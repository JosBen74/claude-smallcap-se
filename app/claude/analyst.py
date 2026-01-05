"""Claude-baserad aktieanalytiker."""

import json
from typing import Any

from anthropic import Anthropic

from ..config import get_settings
from .prompts import (
    WEEKLY_ANALYSIS_PROMPT,
    DAILY_CHECK_PROMPT,
    STOCK_ANALYSIS_PROMPT,
)


class Analyst:
    """Claude-baserad aktieanalytiker."""

    def __init__(self, api_key: str | None = None):
        """Initiera med Anthropic API-nyckel.

        Args:
            api_key: API-nyckel (eller från miljövariabel)
        """
        settings = get_settings()
        self.client = Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    def _call_claude(self, prompt: str, max_tokens: int = 2000) -> str:
        """Anropa Claude API.

        Args:
            prompt: Prompttext
            max_tokens: Max tokens i svar

        Returns:
            Claude's svar
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parsea JSON från Claude-svar.

        Args:
            response: Claude's textrespons

        Returns:
            Parseat JSON-objekt
        """
        # Försök hitta JSON i svaret
        try:
            # Direkt JSON
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # JSON inuti kodblock
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
            return json.loads(json_str)

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            json_str = response[start:end].strip()
            return json.loads(json_str)

        # Försök hitta { och }
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])

        raise ValueError(f"Kunde inte parsea JSON från svar: {response[:200]}...")

    def weekly_analysis(
        self,
        portfolio_summary: str,
        candidate_stocks: str,
        omxspi_change: float,
        benchmark_ytd: float,
        portfolio_ytd: float,
        technical_signals: str,
    ) -> dict[str, Any]:
        """Veckovis portföljanalys.

        Args:
            portfolio_summary: Sammanfattning av nuvarande portfölj
            candidate_stocks: Kandidataktier med data
            omxspi_change: OMXSPI förändring senaste veckan (%)
            benchmark_ytd: Benchmark YTD (%)
            portfolio_ytd: Portfölj YTD (%)
            technical_signals: Tekniska signaler som text

        Returns:
            Dict med köp/sälj-rekommendationer
        """
        prompt = WEEKLY_ANALYSIS_PROMPT.format(
            portfolio_summary=portfolio_summary,
            candidate_stocks=candidate_stocks,
            omxspi_change=f"{omxspi_change:+.1f}",
            benchmark_ytd=f"{benchmark_ytd:+.1f}",
            portfolio_ytd=f"{portfolio_ytd:+.1f}",
            technical_signals=technical_signals,
        )

        response = self._call_claude(prompt, max_tokens=3000)
        return self._parse_json_response(response)

    def daily_check(
        self,
        portfolio_status: str,
        market_moves: str,
        alerts: str,
    ) -> dict[str, Any]:
        """Daglig portföljkontroll.

        Args:
            portfolio_status: Aktuell portföljstatus
            market_moves: Dagens marknadsrörelser
            alerts: Stop-loss/take-profit alerts

        Returns:
            Dict med daglig kommentar och åtgärder
        """
        prompt = DAILY_CHECK_PROMPT.format(
            portfolio_status=portfolio_status,
            market_moves=market_moves,
            alerts=alerts,
        )

        response = self._call_claude(prompt, max_tokens=1000)
        return self._parse_json_response(response)

    def analyze_stock(
        self,
        ticker: str,
        name: str,
        fundamental_data: str,
        technical_data: str,
        weekly_change: float,
        monthly_change: float,
        quarterly_change: float,
    ) -> dict[str, Any]:
        """Analysera enskild aktie.

        Args:
            ticker: Aktiesymbol
            name: Företagsnamn
            fundamental_data: Fundamental data som text
            technical_data: Teknisk data som text
            weekly_change: Veckoförändring (%)
            monthly_change: Månadsförändring (%)
            quarterly_change: Kvartalsförändring (%)

        Returns:
            Dict med analys och rekommendation
        """
        prompt = STOCK_ANALYSIS_PROMPT.format(
            ticker=ticker,
            name=name,
            fundamental_data=fundamental_data,
            technical_data=technical_data,
            weekly_change=f"{weekly_change:+.1f}",
            monthly_change=f"{monthly_change:+.1f}",
            quarterly_change=f"{quarterly_change:+.1f}",
        )

        response = self._call_claude(prompt, max_tokens=1500)
        return self._parse_json_response(response)

    def get_market_sentiment(self, market_data: str) -> str:
        """Hämta marknadssenti ment.

        Args:
            market_data: Marknadsdata som text

        Returns:
            Sentiment som text (bullish/neutral/bearish)
        """
        prompt = f"""Baserat på följande marknadsdata, bedöm det övergripande sentimentet:

{market_data}

Svara med ETT ord: bullish, neutral, eller bearish"""

        response = self._call_claude(prompt, max_tokens=50)
        return response.strip().lower()
