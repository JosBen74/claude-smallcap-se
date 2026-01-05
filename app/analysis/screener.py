"""Aktiescreener för Small Cap Stockholm."""

from dataclasses import dataclass
from typing import Any

from ..config import ScreeningCriteria, get_settings
from ..data.market_data import StockData


@dataclass
class ScreeningResult:
    """Resultat från screening."""

    stock: StockData
    passed: bool
    reasons: list[str]
    score: float  # 0-100, högre = bättre


class Screener:
    """Screena aktier baserat på kriterier."""

    def __init__(self, criteria: ScreeningCriteria | None = None):
        self.criteria = criteria or get_settings().screening

    def screen(self, stock: StockData) -> ScreeningResult:
        """Screena en aktie mot kriterierna.

        Args:
            stock: StockData att screena

        Returns:
            ScreeningResult med pass/fail och motivering
        """
        passed = True
        reasons: list[str] = []
        score = 100.0

        # Market cap-check
        if stock.market_cap:
            if stock.market_cap < self.criteria.market_cap_min:
                passed = False
                reasons.append(
                    f"Market cap {stock.market_cap / 1e9:.1f} MDSEK < {self.criteria.market_cap_min / 1e9:.1f} MDSEK"
                )
                score -= 20
            elif stock.market_cap > self.criteria.market_cap_max:
                passed = False
                reasons.append(
                    f"Market cap {stock.market_cap / 1e9:.1f} MDSEK > {self.criteria.market_cap_max / 1e9:.1f} MDSEK"
                )
                score -= 20
        else:
            reasons.append("Market cap saknas")
            score -= 10

        # Volym-check
        if stock.avg_volume:
            if stock.avg_volume < self.criteria.avg_volume_min:
                passed = False
                reasons.append(
                    f"Volym {stock.avg_volume:,} < {self.criteria.avg_volume_min:,}"
                )
                score -= 20
        else:
            reasons.append("Volymdata saknas")
            score -= 10

        # P/E-check
        if stock.pe_ratio:
            if stock.pe_ratio > self.criteria.pe_ratio_max:
                passed = False
                reasons.append(f"P/E {stock.pe_ratio:.1f} > {self.criteria.pe_ratio_max}")
                score -= 15
            elif stock.pe_ratio < 0:
                passed = False
                reasons.append(f"Negativt P/E ({stock.pe_ratio:.1f})")
                score -= 25
        # P/E saknas är OK för vissa bolag

        # Pris-check
        if stock.current_price < self.criteria.price_min:
            passed = False
            reasons.append(
                f"Pris {stock.current_price:.2f} SEK < {self.criteria.price_min} SEK"
            )
            score -= 15

        if passed:
            reasons.append("Passerar alla kriterier")

        return ScreeningResult(
            stock=stock,
            passed=passed,
            reasons=reasons,
            score=max(0, score),
        )

    def screen_multiple(self, stocks: list[StockData]) -> list[ScreeningResult]:
        """Screena flera aktier.

        Args:
            stocks: Lista med StockData

        Returns:
            Lista med ScreeningResult, sorterad efter score
        """
        results = [self.screen(stock) for stock in stocks]
        # Sortera: passerade först, sedan efter score
        return sorted(
            results,
            key=lambda r: (not r.passed, -r.score),
        )

    def get_candidates(
        self, stocks: list[StockData], top_n: int = 10
    ) -> list[ScreeningResult]:
        """Hämta topp N kandidater som passerar screening.

        Args:
            stocks: Lista med StockData
            top_n: Max antal att returnera

        Returns:
            Lista med passerade ScreeningResult
        """
        results = self.screen_multiple(stocks)
        passed = [r for r in results if r.passed]
        return passed[:top_n]


def quick_screen(stocks: list[StockData]) -> list[ScreeningResult]:
    """Snabb screening med standardinställningar.

    Args:
        stocks: Lista med StockData

    Returns:
        Sorterad lista med ScreeningResult
    """
    screener = Screener()
    return screener.screen_multiple(stocks)
