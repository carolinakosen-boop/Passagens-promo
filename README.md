# ✈️ Passagens em Promoção

Dashboard automático de passagens aéreas em promoção, saindo de **São Paulo (GRU)** e **Rio de Janeiro (GIG/SDU)** para o mundo todo.

## 🔗 [Acessar Dashboard](https://carolinakosen-boop.github.io/passagens-promo/)

## Como funciona

1. **GitHub Actions** roda a cada 6 horas automaticamente
2. **Scrapers** coletam promoções de múltiplas fontes brasileiras
3. **Dashboard** é regenerado com as ofertas atualizadas
4. **Telegram** recebe notificação quando surgem novas promoções

## Fontes de dados

| Fonte | Tipo |
|-------|------|
| Melhores Destinos | Scraping |
| Passagens Imperdíveis | Scraping |
| ViajeDePromo | Scraping |
| Google Flights | Scraping |

## Setup

### Pré-requisitos

- Python 3.12+
- Telegram Bot (via [@BotFather](https://t.me/BotFather))

### Configurar secrets no GitHub

No repositório, vá em **Settings → Secrets and variables → Actions** e adicione:

| Secret | Descrição |
|--------|-----------|
| `TELEGRAM_BOT_TOKEN` | Token do bot do Telegram |
| `TELEGRAM_CHAT_ID` | ID do canal/chat do Telegram (ex: `@seucanalaqui`) |

### Rodar localmente

```bash
pip install -r requirements.txt
cd scripts
python scraper.py
python generate_dashboard.py
```

### Rodar manualmente no GitHub Actions

Vá em **Actions → Update Flight Deals → Run workflow**.

## Estrutura

```
├── .github/workflows/   # GitHub Actions
├── scripts/
│   ├── sources/         # Scrapers por fonte
│   ├── scraper.py       # Orquestrador principal
│   ├── generate_dashboard.py
│   └── telegram_notify.py
├── templates/           # Template HTML (Jinja2)
├── data/                # Dados coletados (JSON)
└── docs/                # Dashboard (GitHub Pages)
```

## Licença

MIT
