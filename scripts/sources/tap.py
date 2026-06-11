"""Scraper for TAP Air Portugal last-minute flight deals."""

import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

OFFERS_URL = "https://www.flytap.com/pt_br/ofertas-de-voos-de-ultima-hora"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

TARGET_ORIGINS = {"GRU", "GIG", "SDU", "CGH", "SAO", "RIO"}

# Route pattern: "City Name (IATA)paraDest City (IATA)"
_ROUTE_RE = re.compile(
    r"([A-Za-zÀ-ú\s.'-]+?)\s*\(([A-Z]{3})\)\s*para\s*([A-Za-zÀ-ú\s.'-]+?)\s*\(([A-Z]{3})\)"
)
_DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})")
_PRICE_RE = re.compile(r"([\d.]+)\s*BRL")


def fetch_deals() -> list[dict]:
    """Fetch TAP Air Portugal last-minute deals (economy only)."""
    try:
        resp = requests.get(OFFERS_URL, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning("TAP returned %d", resp.status_code)
            return []
    except requests.RequestException as e:
        logger.warning("Failed to fetch TAP: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    deals: list[dict] = []
    seen: set[str] = set()

    # Find fare cards: flex containers with route + BRL price
    for card in soup.find_all("div", class_="flex-wrap"):
        text = card.get_text(strip=True)

        if "BRL" not in text:
            continue
        if not any(code in text for code in TARGET_ORIGINS):
            continue
        # Skip business class fares
        if "Business" in text or "Executiva" in text:
            continue

        route = _ROUTE_RE.search(text)
        if not route:
            continue

        origin_city = route.group(1).strip()
        origin_iata = route.group(2)
        dest_city = route.group(3).strip()
        dest_iata = route.group(4)

        if origin_iata not in TARGET_ORIGINS:
            continue

        price_match = _PRICE_RE.search(text)
        if not price_match:
            continue
        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        if price < 100:
            continue

        date_match = _DATE_RE.search(text)
        dep_date = date_match.group(1) if date_match else ""
        ret_date = date_match.group(2) if date_match else ""

        dedup_key = f"{origin_iata}-{dest_iata}-{price}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Clean up city names (remove stray prefixes from HTML parsing)
        origin_city = re.sub(r"^.*?(?=[A-ZÀ-Ú])", "", origin_city, count=1).strip()
        if not origin_city:
            origin_city = origin_iata

        title_parts = [f"TAP: {origin_city} ({origin_iata}) → {dest_city} ({dest_iata})"]
        if dep_date:
            title_parts.append(f"- {dep_date}")
        if ret_date:
            title_parts.append(f"a {ret_date}")
        title = " ".join(title_parts)

        # Build image URL from airTRFX CDN (TAP tenant)
        dest_slug = dest_city.lower().replace(" ", "-").replace("ã", "a").replace("é", "e")
        image_url = f"https://assets.airtrfx.com/media-em/tp/{dest_slug}-1-1500px.jpg"

        deals.append({
            "source": "TAP",
            "title": title,
            "destination": dest_city,
            "destination_iata": dest_iata,
            "origin": origin_city,
            "origin_iata": origin_iata,
            "price_brl": price,
            "currency": "BRL",
            "link": f"https://www.flytap.com/pt_br/ofertas-de-voos-de-ultima-hora",
            "image_url": image_url,
            "airline": "TAP",
            "trip_type": "round_trip",
            "departure_date": dep_date,
            "return_date": ret_date,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info("Extracted %d TAP deals (economy, from SP/RJ)", len(deals))
    return deals
