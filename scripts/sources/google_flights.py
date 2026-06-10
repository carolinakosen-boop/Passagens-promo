"""Google Flights scraper using direct requests.

Uses the publicly accessible Google Flights explore endpoint to find
cheap flights from specified origins.
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

EXPLORE_URL = "https://www.google.com/travel/flights"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

ORIGINS = [
    {"code": "GRU", "city": "São Paulo", "name": "Guarulhos"},
    {"code": "GIG", "city": "Rio de Janeiro", "name": "Galeão"},
    {"code": "SDU", "city": "Rio de Janeiro", "name": "Santos Dumont"},
]


def _build_explore_url(origin_code: str) -> str:
    """Build Google Flights explore URL for an origin."""
    today = datetime.now(timezone.utc)
    date_from = (today + timedelta(days=14)).strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    return (
        f"https://www.google.com/travel/flights/explore"
        f"?q=Flights+from+{origin_code}"
        f"&curr=BRL&gl=br&hl=pt-BR"
    )


def fetch_deals() -> list[dict]:
    """Fetch cheap flight deals from Google Flights explore.

    Note: Google Flights explore page is JS-rendered, so direct HTTP
    requests have limited success. This is a best-effort approach.
    For better results, the Playwright-based scraper should be used.
    """
    deals = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for origin in ORIGINS:
        url = _build_explore_url(origin["code"])
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.warning(
                    "Google Flights returned %d for %s",
                    resp.status_code,
                    origin["code"],
                )
                continue

            # Try to extract flight data from page content
            # Google Flights embeds data in script tags
            text = resp.text

            # Look for price patterns in the HTML
            price_matches = re.findall(
                r'R\$\s*([\d.]+)',
                text,
            )
            # Look for destination city names
            # This is a best-effort extraction from the rendered HTML
            dest_matches = re.findall(
                r'"([A-Z]{3})","([^"]+?)","[^"]*?","R\$\s*([\d.,]+)"',
                text,
            )

            for match in dest_matches:
                iata, city, price_str = match
                price_str = price_str.replace(".", "").replace(",", ".")
                try:
                    price = float(price_str)
                except ValueError:
                    continue

                deals.append({
                    "source": "Google Flights",
                    "title": f"{origin['city']} ({origin['code']}) → {city} ({iata})",
                    "destination": city,
                    "destination_iata": iata,
                    "origin": origin["city"],
                    "origin_iata": origin["code"],
                    "price_brl": price,
                    "currency": "BRL",
                    "link": url,
                    "image_url": None,
                    "trip_type": "round_trip",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })

        except requests.RequestException as e:
            logger.error("Failed to fetch Google Flights for %s: %s", origin["code"], e)
            continue

    logger.info("Extracted %d deals from Google Flights", len(deals))
    return deals
