"""Beslutsmotivering och loggning."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR


@dataclass
class Decision:
    """Ett investeringsbeslut."""

    timestamp: str
    decision_type: str  # buy, sell, hold, rebalance
    ticker: str | None
    action: str
    reasoning: str
    confidence: str  # low, medium, high
    amount_sek: float | None = None
    shares: int | None = None
    price: float | None = None
    portfolio_impact_pct: float | None = None


class DecisionLog:
    """Loggar och spårar investeringsbeslut."""

    def __init__(self, log_path: Path | None = None):
        """Initiera med loggfil.

        Args:
            log_path: Sökväg till loggfil
        """
        self.log_path = log_path or DATA_DIR / "decisions.json"
        self.decisions: list[Decision] = []
        self._load()

    def _load(self) -> None:
        """Ladda befintliga beslut från fil."""
        if self.log_path.exists():
            with open(self.log_path) as f:
                data = json.load(f)
                self.decisions = [Decision(**d) for d in data]

    def _save(self) -> None:
        """Spara beslut till fil."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump([asdict(d) for d in self.decisions], f, indent=2, ensure_ascii=False)

    def log_decision(
        self,
        decision_type: str,
        action: str,
        reasoning: str,
        confidence: str = "medium",
        ticker: str | None = None,
        amount_sek: float | None = None,
        shares: int | None = None,
        price: float | None = None,
        portfolio_impact_pct: float | None = None,
    ) -> Decision:
        """Logga ett nytt beslut.

        Args:
            decision_type: Typ av beslut
            action: Åtgärd som tas
            reasoning: Motivering
            confidence: Konfidensnivå
            ticker: Aktiesymbol (om relevant)
            amount_sek: Belopp i SEK
            shares: Antal aktier
            price: Pris per aktie
            portfolio_impact_pct: Påverkan på portfölj i %

        Returns:
            Det loggade beslutet
        """
        decision = Decision(
            timestamp=datetime.now().isoformat(),
            decision_type=decision_type,
            ticker=ticker,
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            amount_sek=amount_sek,
            shares=shares,
            price=price,
            portfolio_impact_pct=portfolio_impact_pct,
        )
        self.decisions.append(decision)
        self._save()
        return decision

    def get_recent(self, days: int = 7) -> list[Decision]:
        """Hämta beslut från senaste dagarna.

        Args:
            days: Antal dagar bakåt

        Returns:
            Lista med beslut
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        return [
            d
            for d in self.decisions
            if datetime.fromisoformat(d.timestamp).timestamp() > cutoff
        ]

    def get_by_ticker(self, ticker: str) -> list[Decision]:
        """Hämta beslut för en specifik aktie.

        Args:
            ticker: Aktiesymbol

        Returns:
            Lista med beslut
        """
        return [d for d in self.decisions if d.ticker == ticker]

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av beslut.

        Returns:
            Dict med statistik
        """
        if not self.decisions:
            return {"total": 0}

        recent = self.get_recent(30)

        return {
            "total": len(self.decisions),
            "last_30_days": len(recent),
            "by_type": self._count_by_field("decision_type"),
            "by_confidence": self._count_by_field("confidence"),
            "latest": asdict(self.decisions[-1]) if self.decisions else None,
        }

    def _count_by_field(self, field: str) -> dict[str, int]:
        """Räkna beslut per fältvärde.

        Args:
            field: Fältnamn att räkna på

        Returns:
            Dict med räkning
        """
        counts: dict[str, int] = {}
        for d in self.decisions:
            value = getattr(d, field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
