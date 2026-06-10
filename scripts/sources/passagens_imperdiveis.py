"""Scraper for Passagens Imperdíveis promotions."""

import re
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.passagensimperdiveis.com.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": BASE_URL,
}


def _extract_price(text: str) -> Optional[float]:
    match = re.search(r"R\$\s*([\d.,]+)", text)
    if not match:
        return None
    price_str = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(price_str)
    except ValueError:
        return None


def _extract_destination(title: str) -> Optional[str]:
    patterns = [
        r"para\s+(?:o\s+|a\s+)?(.+?)(?:\s+a\s+partir|\s+por\s+apenas|\s+desde|\s+por\s+R\$|\!)",
        r"(?:passagens?\s+(?:aéreas?\s+)?para\s+)(.+?)(?:\s+a\s+partir|\s+por|\s+desde)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            dest = match.group(1).strip()
            dest = re.sub(r"\s*(?:ida e volta|i/v).*", "", dest, flags=re.IGNORECASE)
            return dest[:80]
    return None


def fetch_deals() -> list[dict]:
    """Fetch deals from Passagens Imperdíveis."""
    deals = []
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        resp = session.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch Passagens Imperdíveis: %s", e)
        return deals

    soup = BeautifulSoup(resp.text, "lxml")

    articles = soup.select("article, .post-card, .promo-card, .deal")
    if not articles:
        articles = soup.find_all("div", class_=re.compile(r"post|promo|deal|card", re.I))
    if not articles:
        articles = soup.find_all("a", href=re.compile(r"passagen|promo|voo", re.I))

    logger.info("Found %d potential elements on Passagens Imperdíveis", len(articles))

    for article in articles[:50]:
        try:
            title_el = article.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            link = None
            link_el = article.find("a", href=True)
            if link_el:
                href = link_el["href"]
                link = href if href.startswith("http") else f"{BASE_URL}{href}"

            price = _extract_price(article.get_text())
            destination = _extract_destination(title)

            img = article.find("img", src=True)
            image_url = img["src"] if img else None

            deals.append({
                "source": "Passagens Imperdíveis",
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
            logger.debug("Error parsing element: %s", e)
            continue

    logger.info("Extracted %d deals from Passagens Imperdíveis", len(deals))
    return deals
