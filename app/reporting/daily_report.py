"""Daglig rapportgenerator."""

from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import REPORTS_DIR, get_settings
from ..trading.portfolio import Portfolio
from ..trading.rules import RiskManager


class DailyReport:
    """Genererar dagliga rapporter."""

    def __init__(self, portfolio: Portfolio):
        """Initiera med portfölj.

        Args:
            portfolio: Portföljen att rapportera om
        """
        self.portfolio = portfolio
        self.risk_manager = RiskManager(portfolio)
        self.console = Console()

    def generate(self, benchmark_change: float = 0.0) -> dict[str, Any]:
        """Generera daglig rapport.

        Args:
            benchmark_change: Benchmarkförändring idag (%)

        Returns:
            Dict med rapportdata
        """
        settings = get_settings()
        summary = self.portfolio.get_summary()
        risk_summary = self.risk_manager.get_summary()

        # Beräkna daglig förändring (approximation)
        # I praktiken skulle man jämföra med gårdagens värde
        daily_change = 0.0  # Placeholder

        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "portfolio": {
                "total_value": summary["total_value"],
                "cash": summary["cash"],
                "positions_value": summary["positions_value"],
                "num_positions": summary["num_positions"],
                "total_return_pct": summary["total_return_pct"],
                "daily_change_pct": daily_change,
            },
            "benchmark": {
                "name": settings.benchmark_name,
                "daily_change_pct": benchmark_change,
            },
            "positions": [],
            "alerts": risk_summary["alerts"],
            "health": risk_summary["portfolio_health"],
        }

        # Lägg till positionsdetaljer
        for ticker, pos in self.portfolio.state.positions.items():
            report["positions"].append(
                {
                    "ticker": ticker,
                    "shares": pos.shares,
                    "avg_cost": pos.avg_cost,
                    "current_price": pos.current_price,
                    "market_value": pos.market_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                    "allocation_pct": summary["allocation"].get(ticker, 0),
                }
            )

        return report

    def print_report(self, report: dict[str, Any] | None = None) -> None:
        """Skriv ut rapport till konsolen.

        Args:
            report: Rapport att skriva ut (eller generera ny)
        """
        if report is None:
            report = self.generate()

        # Header
        self.console.print(
            Panel(
                f"[bold]Daglig Portföljrapport - {report['date']}[/bold]",
                style="blue",
            )
        )

        # Sammanfattning
        portfolio = report["portfolio"]
        self.console.print("\n[bold]Sammanfattning[/bold]")
        self.console.print(f"  Portföljvärde: {portfolio['total_value']:,.0f} SEK")
        self.console.print(f"  Kassa: {portfolio['cash']:,.0f} SEK")
        self.console.print(f"  Total avkastning: {portfolio['total_return_pct']:+.1f}%")
        self.console.print(
            f"  Benchmark ({report['benchmark']['name']}): {report['benchmark']['daily_change_pct']:+.1f}%"
        )

        # Positioner
        if report["positions"]:
            self.console.print("\n[bold]Positioner[/bold]")
            table = Table()
            table.add_column("Aktie", style="cyan")
            table.add_column("Antal", justify="right")
            table.add_column("Värde", justify="right")
            table.add_column("Daglig", justify="right")
            table.add_column("Total", justify="right")
            table.add_column("Allok.", justify="right")

            for pos in report["positions"]:
                pnl_style = "green" if pos["unrealized_pnl_pct"] >= 0 else "red"
                table.add_row(
                    pos["ticker"],
                    str(pos["shares"]),
                    f"{pos['market_value']:,.0f}",
                    "-",  # Daglig förändring inte tillgänglig
                    f"[{pnl_style}]{pos['unrealized_pnl_pct']:+.1f}%[/{pnl_style}]",
                    f"{pos['allocation_pct']:.1f}%",
                )

            self.console.print(table)

        # Alerts
        if report["alerts"]:
            self.console.print("\n[bold]Alerts[/bold]")
            for alert in report["alerts"]:
                style = (
                    "red"
                    if alert["severity"] == "critical"
                    else "yellow"
                    if alert["severity"] == "warning"
                    else "blue"
                )
                icon = "!" if alert["severity"] == "critical" else "⚠" if alert["severity"] == "warning" else "i"
                self.console.print(f"  [{style}]{icon} {alert['message']}[/{style}]")

        # Health
        health_style = (
            "green"
            if report["health"] == "good"
            else "red"
            if report["health"] == "critical"
            else "yellow"
        )
        self.console.print(f"\n[{health_style}]Portföljhälsa: {report['health'].upper()}[/{health_style}]")

    def save_report(self, report: dict[str, Any] | None = None) -> Path:
        """Spara rapport till fil.

        Args:
            report: Rapport att spara (eller generera ny)

        Returns:
            Sökväg till sparad fil
        """
        import json

        if report is None:
            report = self.generate()

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"daily_{report['date']}.json"
        filepath = REPORTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return filepath

    def save_markdown(self, report: dict[str, Any] | None = None) -> Path:
        """Spara rapport som markdown.

        Args:
            report: Rapport att spara (eller generera ny)

        Returns:
            Sökväg till sparad fil
        """
        if report is None:
            report = self.generate()

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"daily_{report['date']}.md"
        filepath = REPORTS_DIR / filename

        portfolio = report["portfolio"]

        md = f"""# Daglig Portföljrapport - {report['date']}

## Sammanfattning
- **Portföljvärde:** {portfolio['total_value']:,.0f} SEK
- **Kassa:** {portfolio['cash']:,.0f} SEK
- **Total avkastning:** {portfolio['total_return_pct']:+.1f}%
- **Benchmark ({report['benchmark']['name']}):** {report['benchmark']['daily_change_pct']:+.1f}%

## Positioner

| Aktie | Antal | Värde | Total |
|-------|-------|-------|-------|
"""

        for pos in report["positions"]:
            md += f"| {pos['ticker']} | {pos['shares']} | {pos['market_value']:,.0f} | {pos['unrealized_pnl_pct']:+.1f}% |\n"

        if report["alerts"]:
            md += "\n## Alerts\n"
            for alert in report["alerts"]:
                icon = "!" if alert["severity"] == "critical" else "?" if alert["severity"] == "warning" else "i"
                md += f"- {icon} {alert['message']}\n"

        md += f"\n---\n*Portföljhälsa: {report['health'].upper()}*\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        return filepath
