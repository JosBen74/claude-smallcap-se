"""Fundamental analys."""

from dataclasses import dataclass
from typing import Any


@dataclass
class FundamentalMetrics:
    """Fundamentala nyckeltal."""

    pe_ratio: float | None
    forward_pe: float | None
    pb_ratio: float | None
    ps_ratio: float | None
    dividend_yield: float | None
    market_cap: float | None
    enterprise_value: float | None
    debt_to_equity: float | None
    current_ratio: float | None
    roe: float | None  # Return on Equity
    roa: float | None  # Return on Assets
    profit_margin: float | None
    revenue_growth: float | None


class FundamentalAnalysis:
    """Fundamental analys baserad på aktieinfo."""

    def __init__(self, stock_info: dict[str, Any]):
        """Initiera med aktieinfo från yFinance.

        Args:
            stock_info: Dict med fundamental data
        """
        self.info = stock_info

    def get_metrics(self) -> FundamentalMetrics:
        """Extrahera fundamentala nyckeltal.

        Returns:
            FundamentalMetrics med alla tillgängliga värden
        """
        return FundamentalMetrics(
            pe_ratio=self.info.get("pe_ratio"),
            forward_pe=self.info.get("forward_pe"),
            pb_ratio=self.info.get("pb_ratio"),
            ps_ratio=self.info.get("priceToSalesTrailing12Months"),
            dividend_yield=self.info.get("dividend_yield"),
            market_cap=self.info.get("market_cap"),
            enterprise_value=self.info.get("enterpriseValue"),
            debt_to_equity=self.info.get("debtToEquity"),
            current_ratio=self.info.get("currentRatio"),
            roe=self.info.get("returnOnEquity"),
            roa=self.info.get("returnOnAssets"),
            profit_margin=self.info.get("profitMargins"),
            revenue_growth=self.info.get("revenueGrowth"),
        )

    def get_valuation_score(self) -> tuple[float, list[str]]:
        """Beräkna värderingsscore.

        Returns:
            Tuple med (score 0-100, lista med kommentarer)
        """
        score = 50.0  # Startar neutralt
        comments: list[str] = []

        # P/E-analys
        pe = self.info.get("pe_ratio")
        if pe:
            if pe < 0:
                score -= 20
                comments.append(f"Negativt P/E ({pe:.1f})")
            elif pe < 10:
                score += 15
                comments.append(f"Lågt P/E ({pe:.1f})")
            elif pe < 20:
                score += 5
                comments.append(f"Rimligt P/E ({pe:.1f})")
            elif pe > 30:
                score -= 10
                comments.append(f"Högt P/E ({pe:.1f})")

        # P/B-analys
        pb = self.info.get("pb_ratio")
        if pb:
            if pb < 1:
                score += 10
                comments.append(f"Handlas under bokfört värde (P/B {pb:.1f})")
            elif pb > 5:
                score -= 5
                comments.append(f"Högt P/B ({pb:.1f})")

        # Utdelning
        div_yield = self.info.get("dividend_yield")
        if div_yield and div_yield > 0:
            if div_yield > 0.05:
                score += 10
                comments.append(f"Hög direktavkastning ({div_yield * 100:.1f}%)")
            elif div_yield > 0.02:
                score += 5
                comments.append(f"Utdelande ({div_yield * 100:.1f}%)")

        return max(0, min(100, score)), comments

    def get_quality_score(self) -> tuple[float, list[str]]:
        """Beräkna kvalitetsscore baserat på lönsamhet och skuldsättning.

        Returns:
            Tuple med (score 0-100, lista med kommentarer)
        """
        score = 50.0
        comments: list[str] = []

        # ROE
        roe = self.info.get("returnOnEquity")
        if roe:
            if roe > 0.20:
                score += 15
                comments.append(f"Stark ROE ({roe * 100:.1f}%)")
            elif roe > 0.10:
                score += 5
                comments.append(f"God ROE ({roe * 100:.1f}%)")
            elif roe < 0:
                score -= 15
                comments.append(f"Negativ ROE ({roe * 100:.1f}%)")

        # Skuldsättning
        debt_equity = self.info.get("debtToEquity")
        if debt_equity is not None:
            if debt_equity < 0.5:
                score += 10
                comments.append(f"Låg skuldsättning (D/E {debt_equity:.1f})")
            elif debt_equity > 2:
                score -= 15
                comments.append(f"Hög skuldsättning (D/E {debt_equity:.1f})")

        # Vinstmarginal
        profit_margin = self.info.get("profitMargins")
        if profit_margin:
            if profit_margin > 0.15:
                score += 10
                comments.append(f"Stark marginal ({profit_margin * 100:.1f}%)")
            elif profit_margin < 0:
                score -= 10
                comments.append(f"Negativ marginal ({profit_margin * 100:.1f}%)")

        return max(0, min(100, score)), comments

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av fundamental analys.

        Returns:
            Dict med scores och kommentarer
        """
        valuation_score, valuation_comments = self.get_valuation_score()
        quality_score, quality_comments = self.get_quality_score()

        return {
            "valuation_score": valuation_score,
            "valuation_comments": valuation_comments,
            "quality_score": quality_score,
            "quality_comments": quality_comments,
            "overall_score": (valuation_score + quality_score) / 2,
            "metrics": self.get_metrics(),
        }
