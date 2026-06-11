"""Scraper for GOL Linhas Aéreas fare data (Next.js Apollo state extraction)."""

import json
import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.voegol.com.br"
VOOS_URL = f"{BASE_URL}/br/voos"
PROMO_URL = f"{BASE_URL}/br/voos-promocao-passagens-aereas-comprou-voou"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "identity",
}

# Only include fares originating from these airports
TARGET_ORIGINS = {"GRU", "GIG", "SDU", "CGH", "SAO", "RIO"}


def _extract_fares_from_apollo(html: str) -> list[dict]:
    """Extract fare objects from Next.js Apollo state embedded in the page."""
    soup = BeautifulSoup(html, "lxml")
    fares = []

    for script in soup.find_all("script", id="__NEXT_DATA__"):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue

        apollo = (
            data.get("props", {})
            .get("pageProps", {})
            .get("apolloState", {})
            .get("data", {})
        )

        for key, val in apollo.items():
            if not key.startswith("StandardFareModule") and not key.startswith("DpaHeadline"):
                continue
            if not isinstance(val, dict):
                continue

            module_fares = val.get("fares", [])
            headline = val.get("headline", {})
            if isinstance(headline, dict) and "lowestFare" in headline:
                module_fares.append(headline["lowestFare"])

            for fare in module_fares:
                if not isinstance(fare, dict) or fare.get("__typename") != "Fare":
                    continue
                fares.append(fare)

    return fares


def fetch_deals() -> list[dict]:
    """Fetch GOL fare deals from their website Apollo state."""
    deals = []
    seen: set[str] = set()
    session = requests.Session()
    session.headers.update(HEADERS)

    for url in [VOOS_URL, PROMO_URL]:
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.info("GOL %s returned %d", url, resp.status_code)
                continue
        except requests.RequestException as e:
            logger.warning("Failed to fetch GOL %s: %s", url, e)
            continue

        fares = _extract_fares_from_apollo(resp.text)
        logger.info("Found %d fares on GOL %s", len(fares), url)

        for fare in fares:
            origin_code = fare.get("originAirportCode", "")
            dest_code = fare.get("destinationAirportCode", "")

            if origin_code not in TARGET_ORIGINS:
                continue

            dedup_key = f"{origin_code}-{dest_code}-{fare.get('totalPrice')}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            price = fare.get("totalPrice")
            if price is None or price < 50:
                continue

            origin_city = fare.get("originCity", origin_code)
            dest_city = fare.get("destinationCity", dest_code)
            dep_date = fare.get("formattedDepartureDate", "")
            ret_date = fare.get("formattedReturnDate", "")
            flight_type = fare.get("flightType", "")
            travel_class = fare.get("formattedTravelClass", "")

            title_parts = [f"GOL: {origin_city} ({origin_code}) → {dest_city} ({dest_code})"]
            if dep_date:
                title_parts.append(f"- {dep_date}")
            if ret_date:
                title_parts.append(f"a {ret_date}")
            title = " ".join(title_parts)

            trip_type = "one_way" if flight_type == "ONE_WAY" else "round_trip"

            deals.append({
                "source": "GOL",
                "title": title,
                "destination": dest_city,
                "destination_iata": dest_code,
                "origin": origin_city,
                "origin_iata": origin_code,
                "price_brl": price,
                "currency": "BRL",
                "link": f"{BASE_URL}/br/voos/{origin_code}/{dest_code}",
                "image_url": fare.get("image"),
                "airline": "GOL",
                "trip_type": trip_type,
                "travel_class": travel_class,
                "departure_date": fare.get("departureDate", ""),
                "return_date": fare.get("returnDate", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })

    logger.info("Extracted %d GOL deals (from SP/RJ origins)", len(deals))
    return deals
