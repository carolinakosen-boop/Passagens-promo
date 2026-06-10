"""Scraper for ViajeDePromo (viagedepromo.com.br) deals."""

import re
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.viajedepromo.com.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
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
        r"para\s+(?:o\s+|a\s+)?(.+?)(?:\s+a\s+partir|\s+por\s+apenas|\s+desde|\s+por\s+R\$|\s+saindo|\!)",
        r"(?:passagens?\s+(?:aéreas?\s+)?para\s+)(.+?)(?:\s+a\s+partir|\s+por|\s+desde)",
        r"(?:voos?\s+para\s+)(.+?)(?:\s+a\s+partir|\s+por|\s+desde)",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            dest = match.group(1).strip()
            dest = re.sub(r"\s*(?:ida e volta|i/v).*", "", dest, flags=re.IGNORECASE)
            return dest[:80]
    return None


def fetch_deals() -> list[dict]:
    """Fetch deals from ViajeDePromo."""
    deals = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for path in ["", "/passagens-aereas"]:
        url = f"{BASE_URL}{path}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                continue
        except requests.RequestException as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.select("article, .post, .promo-card, .deal-card")
        if not articles:
            articles = soup.find_all("div", class_=re.compile(r"post|promo|deal|card", re.I))

        for article in articles[:30]:
            try:
                title_el = article.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                link_el = article.find("a", href=True)
                link = None
                if link_el:
                    href = link_el["href"]
                    link = href if href.startswith("http") else f"{BASE_URL}{href}"

                price = _extract_price(article.get_text())
                destination = _extract_destination(title)

                img = article.find("img", src=True)
                image_url = img["src"] if img else None

                deals.append({
                    "source": "ViajeDePromo",
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

    logger.info("Extracted %d deals from ViajeDePromo", len(deals))
    return deals
