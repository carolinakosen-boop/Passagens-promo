"""Scraper for Passagens Imperdíveis promotions (Next.js RSC data extraction)."""

import json
import re
import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://passagensimperdiveis.com.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip",
    "Referer": BASE_URL,
}


def _extract_publicacoes(html: str) -> list[dict]:
    """Extract deal objects from Next.js RSC payload."""
    pushes = re.findall(r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', html, re.DOTALL)
    for push in pushes:
        if "cardsPromo" not in push:
            continue
        push = push.replace('\\"', '"')
        pub_start = push.find('"publicacoes":[')
        if pub_start < 0:
            continue
        depth = 0
        for i, c in enumerate(push[pub_start + 15:]):
            if c == "[":
                depth += 1
            elif c == "]":
                if depth == 0:
                    pub_json = "[" + push[pub_start + 15:pub_start + 15 + i] + "]"
                    try:
                        return json.loads(pub_json)
                    except json.JSONDecodeError:
                        pass
                    break
                depth -= 1
    return []


def fetch_deals() -> list[dict]:
    """Fetch deals from Passagens Imperdíveis via RSC data."""
    deals = []
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        resp = session.get(BASE_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Failed to fetch Passagens Imperdíveis: %s", e)
        return deals

    publicacoes = _extract_publicacoes(resp.text)
    promos = [p for p in publicacoes if p.get("publicacaoTipo") == "PROMOCAO"]
    logger.info("Found %d promos in Passagens Imperdíveis RSC data", len(promos))

    for promo in promos:
        try:
            titulos = promo.get("titulos", {})
            title = titulos.get("tituloLongo") or titulos.get("titulo") or ""
            title = re.sub(r"<[^>]+>", "", title)  # strip HTML tags
            short_title = titulos.get("titulo", "")

            slug = promo.get("slug") or promo.get("slugPublicacao", "")
            link = f"{BASE_URL}/{slug}/" if slug else None

            valor_obj = promo.get("valor", {})
            valor_inner = valor_obj.get("valor", {})
            price_str = valor_inner.get("str", "") if isinstance(valor_inner, dict) else ""
            price = None
            if price_str:
                price = float(price_str.replace(".", "").replace(",", "."))

            if price is not None and price < 100:
                continue

            image_url = promo.get("imagemPrincipal") or promo.get("imagem")

            trip_type = "unknown"
            labels = promo.get("labels", [])
            for label in labels:
                desc = (label.get("descricao") or "").lower()
                if "ida e volta" in desc:
                    trip_type = "round_trip"
                elif "só ida" in desc:
                    trip_type = "one_way"

            pos_valor = valor_obj.get("descricaoPosValor", "")
            if "ida e volta" in pos_valor.lower():
                trip_type = "round_trip"

            destination = short_title if short_title else None

            deals.append({
                "source": "Passagens Imperdíveis",
                "title": title[:200],
                "destination": destination,
                "price_brl": price,
                "currency": "BRL",
                "link": link,
                "image_url": image_url,
                "trip_type": trip_type,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.debug("Error parsing PI promo: %s", e)
            continue

    logger.info("Extracted %d deals from Passagens Imperdíveis", len(deals))
    return deals
