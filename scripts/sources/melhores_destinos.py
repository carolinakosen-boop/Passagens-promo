"""Scraper for Melhores Destinos promotions page."""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.melhoresdestinos.com.br"
PROMO_URL = f"{BASE_URL}/promocao"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": BASE_URL,
}

ORIGIN_CODES = {"GRU", "GIG", "SDU", "CGH"}

# Keywords that indicate a deal is about flights (not hotels, currency, parks, etc.)
FLIGHT_KEYWORDS = [
    "passagen", "voo", "aére", "ida e volta", "i/v",
    "saindo de", "saindo do", "voando", "trecho",
    "bagagem", "escala", "direto", "companhia",
    "latam", "gol", "azul", "avianca", "copa", "american",
    "united", "delta", "tap", "iberia", "air france",
    "emirates", "turkish", "qatar", "klm", "lufthansa",
]

# Keywords that indicate the deal is NOT about flights
EXCLUDE_KEYWORDS = [
    "hotel", "hosped", "seguro viagem", "aluguel",
    "ingresso", "dólar", "euro", "câmbio", "nomad",
    "cruzeiro", "rent a car", "cartão", "milha",
    "beto carrero", "disney", "universal", "accor",
    "ibis", "mercure", "novotel", "cupom", "chip",
]


def _extract_price(text: str) -> Optional[float]:
    """Extract price in BRL from text like 'R$ 1.299' or 'R$ 3.042'."""
    match = re.search(r"R\$\s*([\d.,]+)", text)
    if not match:
        return None
    price_str = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(price_str)
    except ValueError:
        return None


def _extract_destination(title: str) -> Optional[str]:
    """Try to extract destination city/country from promo title."""
    patterns = [
        r"para\s+(?:o\s+|a\s+)?(.+?)(?:\s+a\s+partir|\s+por\s+apenas|\s+desde|\s+por\s+R\$|\s+com\s+)",
        r"(?:passagens?\s+(?:aéreas?\s+)?para\s+)(.+?)(?:\s+a\s+partir|\s+por|\s+desde)",
        r"(?:voos?\s+(?:diretos?\s+)?para\s+)(.+?)(?:\s+a\s+partir|\s+por|\s+desde)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            dest = match.group(1).strip()
            dest = re.sub(r"\s*(?:ida e volta|i/v).*", "", dest, flags=re.IGNORECASE)
            return dest[:80]
    return None


def fetch_deals() -> list[dict]:
    """Fetch flight deals from Melhores Destinos promotions page."""
    deals = []
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        resp = session.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        logger.warning("Failed to establish session with Melhores Destinos")

    try:
        resp = session.get(PROMO_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch Melhores Destinos promos: %s", e)
        return deals

    soup = BeautifulSoup(resp.text, "lxml")

    articles = soup.select("article, .post, .promotion-card, .deal-card, .listing-item")
    if not articles:
        articles = soup.find_all("div", class_=re.compile(r"promo|deal|post|card", re.I))
    if not articles:
        articles = soup.find_all("a", href=re.compile(r"/promocao/|passagens", re.I))

    logger.info("Found %d potential deal elements on Melhores Destinos", len(articles))

    for article in articles[:80]:
        try:
            title_el = article.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            title_lower = title.lower()

            # Skip non-flight deals
            if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
                continue

            # Require at least one flight keyword
            if not any(kw in title_lower for kw in FLIGHT_KEYWORDS):
                continue

            link = None
            link_el = article.find("a", href=True)
            if link_el:
                href = link_el["href"]
                link = href if href.startswith("http") else f"{BASE_URL}{href}"

            price = _extract_price(article.get_text())
            # Skip if price is too low to be a real flight (likely currency rate)
            if price is not None and price < 100:
                continue

            destination = _extract_destination(title)

            img = article.find("img", src=True)
            image_url = img["src"] if img else None
            if image_url and not image_url.startswith("http"):
                image_url = f"{BASE_URL}{image_url}"

            deals.append({
                "source": "Melhores Destinos",
                "title": title,
                "destination": destination,
                "price_brl": price,
                "currency": "BRL",
                "link": link,
                "image_url": image_url,
                "trip_type": "round_trip" if "ida e volta" in title.lower() else "unknown",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.debug("Error parsing deal element: %s", e)
            continue

    logger.info("Extracted %d deals from Melhores Destinos", len(deals))
    return deals
