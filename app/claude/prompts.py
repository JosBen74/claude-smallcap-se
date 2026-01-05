"""Promptmallar för Claude-analys."""

WEEKLY_ANALYSIS_PROMPT = """Du är en erfaren aktieanalytiker specialiserad på svenska small-cap aktier på Stockholmsbörsen.

## Aktuell portfölj
{portfolio_summary}

## Kandidataktier denna vecka
{candidate_stocks}

## Marknadskontext
- OMXSPI: {omxspi_change}% senaste veckan
- Benchmark YTD: {benchmark_ytd}%
- Portfölj YTD: {portfolio_ytd}%

## Tekniska signaler
{technical_signals}

## Din uppgift
1. Analysera varje kandidataktie baserat på:
   - Fundamental värdering (P/E, P/B, marginal)
   - Tekniska signaler (trend, RSI, momentum)
   - Marknadsposition och konkurrenssituation
   - Risker och triggers

2. Identifiera de 3 bästa köpkandidaterna med motivering

3. Identifiera positioner att avyttra eller minska med motivering

4. Ge en kort marknadsutblick (2-3 meningar)

Svara i JSON-format:
{{
  "buy_recommendations": [
    {{
      "ticker": "TICKER",
      "action": "buy",
      "allocation_pct": 5,
      "reasoning": "Kort motivering...",
      "risk_level": "low|medium|high",
      "target_price": null,
      "stop_loss_pct": -15
    }}
  ],
  "sell_recommendations": [
    {{
      "ticker": "TICKER",
      "action": "sell|reduce",
      "reasoning": "Kort motivering..."
    }}
  ],
  "hold_positions": ["TICKER1", "TICKER2"],
  "market_outlook": "Marknadsutblick...",
  "confidence_level": "low|medium|high"
}}
"""

DAILY_CHECK_PROMPT = """Du är en aktieanalytiker som gör en daglig genomgång av portföljen.

## Portföljstatus
{portfolio_status}

## Dagens marknadsrörelser
{market_moves}

## Stop-loss/Take-profit alerts
{alerts}

## Din uppgift
1. Kommentera dagen kort (1-2 meningar)
2. Flagga om någon position kräver omedelbar åtgärd
3. Notera eventuella nyheter/händelser att bevaka

Svara i JSON-format:
{{
  "daily_comment": "Dagens kommentar...",
  "immediate_actions": [
    {{
      "ticker": "TICKER",
      "action": "sell|hold|investigate",
      "reasoning": "Motivering..."
    }}
  ],
  "watchlist_notes": ["Not om aktie 1...", "Not om aktie 2..."]
}}
"""

STOCK_ANALYSIS_PROMPT = """Analysera följande aktie för potentiellt köp:

## Aktie: {ticker} ({name})

## Fundamental data
{fundamental_data}

## Teknisk analys
{technical_data}

## Historisk kursutveckling
- 1 vecka: {weekly_change}%
- 1 månad: {monthly_change}%
- 3 månader: {quarterly_change}%

## Din analys
Ge en strukturerad analys med:
1. **Styrkor**: 2-3 punkter
2. **Svagheter/Risker**: 2-3 punkter
3. **Katalysatorer**: Potentiella triggers för kursrörelse
4. **Rekommendation**: Köp/Avvakta/Undvik
5. **Lämplig portföljallokering**: X% av portfölj

Svara i JSON-format:
{{
  "ticker": "{ticker}",
  "recommendation": "buy|wait|avoid",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "catalysts": ["...", "..."],
  "suggested_allocation_pct": X,
  "risk_level": "low|medium|high",
  "summary": "1-2 meningar sammanfattning"
}}
"""

REBALANCE_PROMPT = """Det är dags för månadsvis ombalansering av portföljen.

## Aktuell portföljsammansättning
{current_portfolio}

## Målallokering
- Max per position: {max_position_pct}%
- Kassareserv: {cash_reserve_pct}%
- Max antal positioner: {max_positions}

## Positioner utanför målallokering
{out_of_balance}

## Din uppgift
Föreslå ombalanseringsåtgärder för att återställa målallokering, med hänsyn till:
- Transaktionskostnader (undvik små justeringar)
- Skatteeffekter (undvik onödiga realisationer)
- Marknadstiming (stark/svag aktie)

Svara i JSON-format:
{{
  "rebalancing_actions": [
    {{
      "ticker": "TICKER",
      "current_pct": X,
      "target_pct": Y,
      "action": "buy|sell|hold",
      "amount_sek": Z,
      "reasoning": "..."
    }}
  ],
  "total_transactions": X,
  "estimated_impact": "..."
}}
"""
