# Claude Small-Cap SE

AI-driven aktiehandel för Stockholmsbörsen Small Cap och First North med Claude.

Inspirerad av [ChatGPT-Micro-Cap-Experiment](https://github.com/LuckyOne7777/ChatGPT-Micro-Cap-Experiment), anpassad för svenska marknaden.

## Funktioner

- **Datahämtning**: Svenska aktier via yFinance (.ST)
- **Screening**: Filtrera på market cap, P/E, volym
- **Teknisk analys**: RSI, SMA, MACD, Bollinger Bands
- **Fundamental analys**: P/E, ROE, skuldsättning
- **Claude-integration**: AI-driven portföljanalys
- **Risk management**: Stop-loss, take-profit, allokeringsregler
- **Rapportering**: Dagliga/veckovisa rapporter med benchmark-jämförelse

## Installation

```bash
# Klona projektet
git clone [repo-url]
cd claude-smallcap-se

# Installera dependencies
pip install -e .

# Konfigurera
cp .env.example .env
# Redigera .env med din ANTHROPIC_API_KEY
```

## Användning

```bash
# Daglig körning
python -m app.main daily

# Veckoanalys
python -m app.main weekly

# Visa portfölj
python -m app.main portfolio

# Visa prestanda
python -m app.main performance
```

## Konfiguration

| Variabel | Beskrivning | Standard |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API-nyckel | - |
| `INITIAL_CAPITAL` | Startkapital | 100000 |
| `CURRENCY` | Valuta | SEK |

## Handelsregler

| Regel | Värde |
|-------|-------|
| Stop-loss | -15% |
| Take-profit | +30% |
| Max per position | 10% |
| Max positioner | 15 |
| Kassareserv | 10% |

## Varning

Detta är ett experimentellt projekt för utbildningssyfte. Inte finansiell rådgivning. Investera på egen risk.

## Licens

MIT
