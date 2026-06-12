#!/usr/bin/env python3
"""Send new flight deal notifications to a Telegram channel/chat."""

import json
import logging
import os
import sys
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEW_DEALS_FILE = DATA_DIR / "new_deals.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_API = "https://api.telegram.org/bot{token}"

MAX_NOTIFICATIONS = 15  # avoid spamming on first run


def _format_deal(deal: dict) -> str:
    """Format a single deal as a Telegram message with HTML."""
    parts = []

    price = deal.get("price_brl")
    destination = deal.get("destination") or "Destino"
    source = deal.get("source", "")
    title = deal.get("title", "")
    link = deal.get("link", "")
    trip_type = deal.get("trip_type", "")

    # Header with emoji
    if price and price < 2000:
        emoji = "🔥"
    elif price and price < 3000:
        emoji = "✈️"
    else:
        emoji = "💺"

    parts.append(f"{emoji} <b>{destination}</b>")

    if price:
        parts.append(f"💰 <b>R$ {price:,.2f}</b>".replace(",", "X").replace(".", ",").replace("X", "."))

    if trip_type == "round_trip":
        parts.append("🔄 Ida e volta")

    if title and title != destination:
        parts.append(f"\n📝 {title[:200]}")

    if link:
        parts.append(f'\n🔗 <a href="{link}">Ver oferta</a>')

    if source:
        parts.append(f"\n📡 Fonte: {source}")

    return "\n".join(parts)


def send_notifications() -> int:
    """Read new deals and send Telegram notifications."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping notifications."
        )
        return 0

    if not NEW_DEALS_FILE.exists():
        logger.info("No new deals file found. Nothing to notify.")
        return 0

    try:
        new_deals = json.loads(NEW_DEALS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read new deals: %s", e)
        return 1

    if not new_deals:
        logger.info("No new deals to notify about.")
        return 0

    # Sort by price, cheapest first
    new_deals.sort(key=lambda d: d.get("price_brl") or 999999)

    # Limit notifications
    to_send = new_deals[:MAX_NOTIFICATIONS]
    logger.info("Sending %d notifications (of %d new deals)", len(to_send), len(new_deals))

    api_url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    errors = 0

    # Send header message
    header = (
        "🛫 <b>Novas promoções de passagens!</b>\n"
        f"Encontramos {len(new_deals)} nova(s) oferta(s).\n"
        "─────────────────────"
    )
    try:
        resp = requests.post(
            f"{api_url}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": header,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to send header: %s", e)
        errors += 1

    # Send individual deal messages
    for deal in to_send:
        msg = _format_deal(deal)
        try:
            resp = requests.post(
                f"{api_url}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to send deal notification: %s", e)
            errors += 1

    if errors:
        logger.warning("%d notification(s) failed", errors)
    else:
        logger.info("All notifications sent successfully!")

    return 0  # never fail the job due to notification issues


if __name__ == "__main__":
    sys.exit(send_notifications())
