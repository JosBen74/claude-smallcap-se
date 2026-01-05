# Claude Small-Cap SE

> AI-driven aktiehandel för Stockholmsbörsen Small Cap med Claude

## Tech Stack

- **Python**: 3.10+
- **AI**: Anthropic Claude API
- **Data**: yFinance, nasdaqnordic_query
- **CLI**: Rich (terminal output)

## Project Structure

```
claude-smallcap-se/
├── app/
│   ├── main.py           # Entry point
│   ├── config.py         # Konfiguration
│   ├── data/             # Datahämtning
│   ├── analysis/         # Screener, teknisk/fundamental analys
│   ├── claude/           # Claude AI-integration
│   ├── trading/          # Portfölj, riskregler
│   └── reporting/        # Rapporter
├── data/                  # Portfolio, transaktioner, rapporter
├── tests/
├── pyproject.toml
└── .env.example
```

## Commands

```bash
# Installera dependencies
pip install -e .

# Daglig körning (uppdatera priser, kontrollera regler)
python -m app.main daily

# Veckoanalys (screena kandidater)
python -m app.main weekly

# Visa portfölj
python -m app.main portfolio

# Visa prestanda
python -m app.main performance
```

## Konfiguration

Skapa `.env` baserat på `.env.example`:

```bash
ANTHROPIC_API_KEY=your-key
INITIAL_CAPITAL=100000
```

## Viktiga moduler

### Data (`app/data/`)
- `yfinance_se.py`: Svenska aktier via yFinance (.ST suffix)
- `market_data.py`: Kombinerad dataklass

### Analys (`app/analysis/`)
- `screener.py`: Filtrera aktier (market cap, P/E, volym)
- `technical.py`: RSI, SMA, MACD, Bollinger
- `fundamental.py`: P/E, ROE, skuldsättning

### Claude (`app/claude/`)
- `analyst.py`: Claude API-integration
- `prompts.py`: Promptmallar för analys
- `decision.py`: Loggning av beslut

### Trading (`app/trading/`)
- `portfolio.py`: Köp/sälj, positioner
- `rules.py`: Stop-loss, take-profit, allokering

### Rapportering (`app/reporting/`)
- `daily_report.py`: Daglig sammanfattning
- `performance.py`: Avkastning vs benchmark

## Handelsregler

```python
# Screening
market_cap_min: 500 MSEK
market_cap_max: 10 MDSEK
avg_volume_min: 100k
pe_ratio_max: 30
price_min: 5 SEK

# Risk
stop_loss_pct: -15%
take_profit_pct: +30%
max_position_pct: 10%
max_positions: 15
cash_reserve_pct: 10%
```

## Flöde

### Dagligt
1. Uppdatera priser (`portfolio.update_prices()`)
2. Kontrollera stop-loss/take-profit (`risk_manager.check_all()`)
3. Generera daglig rapport (`daily_report.generate()`)
4. Spara performance snapshot (`tracker.record_snapshot()`)

### Veckovis
1. Screena nya kandidater (`screener.get_candidates()`)
2. Claude analyserar och rankar (`analyst.weekly_analysis()`)
3. Generera köp/sälj-rekommendationer
4. Logga beslut (`decision_log.log_decision()`)

## Benchmark

OMXSPI (Stockholm PI) används som benchmark för jämförelse.

## Begränsningar

- Paper trading endast (ingen mäklarintegration)
- yFinance-data kan vara fördröjd
- Claude-rekommendationer är vägledande, inte finansiell rådgivning
