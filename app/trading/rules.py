"""Risk management och handelsregler."""

from dataclasses import dataclass
from typing import Any

from ..config import RiskRules, get_settings
from .portfolio import Portfolio, Position


@dataclass
class Alert:
    """En riskalert."""

    alert_type: str  # stop_loss, take_profit, over_allocation, low_cash
    ticker: str | None
    message: str
    severity: str  # info, warning, critical
    suggested_action: str


class RiskManager:
    """Hanterar riskregler och alerts."""

    def __init__(self, portfolio: Portfolio, rules: RiskRules | None = None):
        """Initiera med portfölj och regler.

        Args:
            portfolio: Portföljen att övervaka
            rules: Riskregler (eller standardvärden)
        """
        self.portfolio = portfolio
        self.rules = rules or get_settings().risk

    def check_all(self) -> list[Alert]:
        """Kontrollera alla riskregler.

        Returns:
            Lista med alerts
        """
        alerts: list[Alert] = []

        # Kontrollera varje position
        for ticker, pos in self.portfolio.state.positions.items():
            alerts.extend(self.check_position(pos))

        # Kontrollera portföljnivå
        alerts.extend(self.check_portfolio_rules())

        return alerts

    def check_position(self, position: Position) -> list[Alert]:
        """Kontrollera regler för en position.

        Args:
            position: Position att kontrollera

        Returns:
            Lista med alerts för positionen
        """
        alerts: list[Alert] = []

        pnl_pct = position.unrealized_pnl_pct

        # Stop-loss
        if pnl_pct <= self.rules.stop_loss_pct:
            alerts.append(
                Alert(
                    alert_type="stop_loss",
                    ticker=position.ticker,
                    message=f"{position.ticker}: {pnl_pct:+.1f}% - under stop-loss ({self.rules.stop_loss_pct}%)",
                    severity="critical",
                    suggested_action="sell",
                )
            )
        elif pnl_pct <= self.rules.stop_loss_pct + 5:
            # Varning när man närmar sig stop-loss
            alerts.append(
                Alert(
                    alert_type="stop_loss_warning",
                    ticker=position.ticker,
                    message=f"{position.ticker}: {pnl_pct:+.1f}% - närmar sig stop-loss",
                    severity="warning",
                    suggested_action="monitor",
                )
            )

        # Take-profit
        if pnl_pct >= self.rules.take_profit_pct:
            alerts.append(
                Alert(
                    alert_type="take_profit",
                    ticker=position.ticker,
                    message=f"{position.ticker}: {pnl_pct:+.1f}% - passerat take-profit ({self.rules.take_profit_pct}%)",
                    severity="info",
                    suggested_action="consider_partial_sale",
                )
            )

        return alerts

    def check_portfolio_rules(self) -> list[Alert]:
        """Kontrollera portföljnivåregler.

        Returns:
            Lista med alerts
        """
        alerts: list[Alert] = []
        allocation = self.portfolio.get_allocation()
        total = self.portfolio.total_value

        # Kontrollera max allokering per position
        for ticker, pct in allocation.items():
            if ticker == "_cash":
                continue
            if pct > self.rules.max_position_pct:
                alerts.append(
                    Alert(
                        alert_type="over_allocation",
                        ticker=ticker,
                        message=f"{ticker}: {pct:.1f}% > max {self.rules.max_position_pct}%",
                        severity="warning",
                        suggested_action="reduce_position",
                    )
                )

        # Kontrollera kassareserv
        cash_pct = allocation.get("_cash", 0)
        if cash_pct < self.rules.cash_reserve_pct:
            alerts.append(
                Alert(
                    alert_type="low_cash",
                    ticker=None,
                    message=f"Kassa {cash_pct:.1f}% < minimum {self.rules.cash_reserve_pct}%",
                    severity="warning",
                    suggested_action="increase_cash",
                )
            )

        # Kontrollera antal positioner
        num_positions = len(self.portfolio.state.positions)
        if num_positions > self.rules.max_positions:
            alerts.append(
                Alert(
                    alert_type="too_many_positions",
                    ticker=None,
                    message=f"{num_positions} positioner > max {self.rules.max_positions}",
                    severity="warning",
                    suggested_action="consolidate",
                )
            )

        return alerts

    def can_buy(self, amount: float) -> tuple[bool, str]:
        """Kontrollera om köp är tillåtet.

        Args:
            amount: Köpbelopp

        Returns:
            Tuple med (tillåtet, anledning)
        """
        # Kontrollera kassa
        if amount > self.portfolio.state.cash:
            return False, f"Otillräcklig kassa: {self.portfolio.state.cash:.0f} SEK"

        # Kontrollera att kassareserv behålls
        new_cash = self.portfolio.state.cash - amount
        total = self.portfolio.total_value
        new_cash_pct = (new_cash / total) * 100 if total > 0 else 0

        if new_cash_pct < self.rules.cash_reserve_pct:
            max_buy = (
                self.portfolio.state.cash
                - (self.rules.cash_reserve_pct / 100) * total
            )
            return (
                False,
                f"Skulle bryta kassareserv. Max köp: {max(0, max_buy):.0f} SEK",
            )

        # Kontrollera antal positioner
        if len(self.portfolio.state.positions) >= self.rules.max_positions:
            return False, f"Max antal positioner ({self.rules.max_positions}) nått"

        return True, "OK"

    def suggested_position_size(self, ticker: str) -> float:
        """Föreslå positionsstorlek för en aktie.

        Args:
            ticker: Aktiesymbol

        Returns:
            Föreslaget belopp i SEK
        """
        total = self.portfolio.total_value

        # Basera på max allokering
        max_amount = (self.rules.max_position_pct / 100) * total

        # Men behåll kassareserv
        available_cash = (
            self.portfolio.state.cash
            - (self.rules.cash_reserve_pct / 100) * total
        )

        return min(max_amount, max(0, available_cash))

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av riskstatus.

        Returns:
            Dict med riskdata
        """
        alerts = self.check_all()

        return {
            "num_alerts": len(alerts),
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "warnings": len([a for a in alerts if a.severity == "warning"]),
            "alerts": [
                {
                    "type": a.alert_type,
                    "ticker": a.ticker,
                    "message": a.message,
                    "severity": a.severity,
                    "action": a.suggested_action,
                }
                for a in alerts
            ],
            "portfolio_health": "good" if not alerts else (
                "critical" if any(a.severity == "critical" for a in alerts) else "warning"
            ),
        }
