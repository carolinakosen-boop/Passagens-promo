#!/usr/bin/env python3
"""Generate the static HTML dashboard from deals data."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEALS_FILE = DATA_DIR / "deals.json"
DOCS_DIR = ROOT / "docs"
TEMPLATE_DIR = ROOT / "templates"


def _format_price(price: float | None) -> str:
    if price is None:
        return "Consulte"
    formatted = f"{price:,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def generate() -> int:
    """Generate dashboard HTML from deals data."""
    if not DEALS_FILE.exists():
        logger.warning("No deals data found at %s", DEALS_FILE)
        deals = []
    else:
        deals = json.loads(DEALS_FILE.read_text(encoding="utf-8"))

    # Group deals by destination
    destinations: dict[str, list] = {}
    for deal in deals:
        dest = deal.get("destination") or "Outros"
        destinations.setdefault(dest, []).append(deal)

    # Get unique sources
    sources = sorted({d.get("source", "Unknown") for d in deals})

    # Stats
    total_deals = len(deals)
    cheapest = min((d.get("price_brl") or 999999 for d in deals), default=0)
    num_destinations = len(destinations)

    # Load template
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["format_price"] = _format_price
    template = env.get_template("dashboard.html")

    now = datetime.now(timezone.utc)
    html = template.render(
        deals=deals,
        destinations=destinations,
        sources=sources,
        total_deals=total_deals,
        cheapest_price=_format_price(cheapest if cheapest < 999999 else None),
        num_destinations=num_destinations,
        updated_at=now.strftime("%d/%m/%Y às %H:%M UTC"),
        year=now.year,
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output = DOCS_DIR / "index.html"
    output.write_text(html, encoding="utf-8")
    logger.info("Dashboard generated at %s", output)

    # Also copy deals.json to docs for the JS frontend
    deals_output = DOCS_DIR / "deals.json"
    deals_output.write_text(
        json.dumps(deals, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    sys.exit(generate())
