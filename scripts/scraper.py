#!/usr/bin/env python3
"""Main scraper orchestrator — fetches deals from all sources, deduplicates,
and merges with existing data."""

import json
import hashlib
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sources import melhores_destinos, passagens_imperdiveis, gol, viaje_de_promo, tap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scraper")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEALS_FILE = DATA_DIR / "deals.json"
MAX_DEALS = 200  # keep the last N deals
MAX_AGE_DAYS = 1  # drop deals older than 24h (stale promos removed quickly)


def _deal_id(deal: dict) -> str:
    """Generate a unique ID for a deal based on title + source."""
    key = f"{deal.get('source', '')}-{deal.get('title', '')}-{deal.get('price_brl', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _load_existing() -> list[dict]:
    if DEALS_FILE.exists():
        try:
            return json.loads(DEALS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read existing deals file, starting fresh")
    return []


def _save(deals: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DEALS_FILE.write_text(
        json.dumps(deals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d deals to %s", len(deals), DEALS_FILE)


def fetch_all() -> list[dict]:
    """Fetch deals from all sources, merge with existing data, deduplicate."""
    all_new: list[dict] = []

    sources = [
        ("Melhores Destinos", melhores_destinos.fetch_deals),
        ("Passagens Imperdíveis", passagens_imperdiveis.fetch_deals),
        ("GOL", gol.fetch_deals),
        ("TAP", tap.fetch_deals),
        ("ViajeDePromo", viaje_de_promo.fetch_deals),
    ]

    for name, fetch_fn in sources:
        try:
            logger.info("Fetching from %s...", name)
            deals = fetch_fn()
            logger.info("  → %d deals from %s", len(deals), name)
            all_new.extend(deals)
        except Exception as e:
            logger.error("Failed to fetch from %s: %s", name, e)

    # Assign IDs
    for deal in all_new:
        deal["id"] = _deal_id(deal)

    # Merge with existing (drop stale deals)
    existing = _load_existing()
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    fresh_existing = []
    stale_count = 0
    for d in existing:
        fetched = d.get("fetched_at", "")
        if fetched:
            try:
                ts = datetime.fromisoformat(fetched)
                if ts < cutoff:
                    stale_count += 1
                    continue
            except (ValueError, TypeError):
                pass
        fresh_existing.append(d)
    if stale_count:
        logger.info("Dropped %d stale deals (older than %d days)", stale_count, MAX_AGE_DAYS)

    existing_ids = {d.get("id") for d in fresh_existing}
    fresh = [d for d in all_new if d["id"] not in existing_ids]
    logger.info("Found %d new deals (out of %d total fetched)", len(fresh), len(all_new))

    # Combine: new first, then existing (already filtered)
    combined = fresh + fresh_existing

    # Sort by price (cheapest first), deals without price go last
    combined.sort(key=lambda d: d.get("price_brl") or 999999)

    # Trim to max
    combined = combined[:MAX_DEALS]

    _save(combined)
    return fresh  # return only new deals (for notifications)


def main() -> int:
    logger.info("Starting deal scraper at %s", datetime.now(timezone.utc).isoformat())
    new_deals = fetch_all()
    logger.info("Done. %d new deals found.", len(new_deals))

    # Write new deals to a temp file for the notification step
    new_deals_file = DATA_DIR / "new_deals.json"
    new_deals_file.write_text(
        json.dumps(new_deals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
