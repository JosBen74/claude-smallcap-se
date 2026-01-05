"""Huvudentry för Claude Small-Cap SE."""

import argparse
from datetime import datetime

from rich.console import Console

from .config import get_settings
from .data.market_data import MarketData
from .data.yfinance_se import SAMPLE_TICKERS
from .analysis.screener import Screener
from .trading.portfolio import Portfolio
from .trading.rules import RiskManager
from .reporting.daily_report import DailyReport
from .reporting.performance import PerformanceTracker
from .reporting.notifications import send_daily_report_email, send_smart_report_email
from .reporting.smart_report import generate_smart_daily_report, format_smart_email


console = Console()


def daily_run(send_email: bool = False) -> None:
    """Daglig körning - uppdatera priser och kontrollera regler."""
    console.print("[bold blue]Claude Small-Cap SE - Daglig körning[/bold blue]\n")

    # Ladda portfölj
    portfolio = Portfolio()
    console.print(f"Portföljvärde: {portfolio.total_value:,.0f} SEK")

    # Uppdatera priser
    console.print("\nUppdaterar priser...")
    portfolio.update_prices()

    # Kontrollera riskregler
    risk_manager = RiskManager(portfolio)
    alerts = risk_manager.check_all()

    if alerts:
        console.print(f"\n[yellow]! {len(alerts)} alerts[/yellow]")
        for alert in alerts:
            style = "red" if alert.severity == "critical" else "yellow"
            console.print(f"  [{style}]{alert.message}[/{style}]")
    else:
        console.print("\n[green]Inga alerts[/green]")

    # Generera daglig rapport
    reporter = DailyReport(portfolio)
    market_data = MarketData()
    market_data.load_benchmark()
    benchmark_change = market_data.get_benchmark_change(1)

    report = reporter.generate(benchmark_change)
    reporter.print_report(report)

    # Spara rapport
    filepath = reporter.save_markdown(report)
    console.print(f"\n[dim]Rapport sparad: {filepath}[/dim]")

    # Skicka e-post om flagga är satt
    if send_email:
        console.print("\nSkickar e-postrapport...")
        if send_daily_report_email(report):
            console.print("[green]E-post skickad![/green]")
        else:
            console.print("[red]Kunde inte skicka e-post[/red]")

    # Spara performance snapshot
    tracker = PerformanceTracker()
    tracker.record_snapshot(
        total_value=portfolio.total_value,
        cash=portfolio.state.cash,
    )


def weekly_analysis() -> None:
    """Veckovis analys med Claude."""
    console.print("[bold blue]Claude Small-Cap SE - Veckoanalys[/bold blue]\n")

    settings = get_settings()

    # Kontrollera API-nyckel
    if not settings.anthropic_api_key:
        console.print("[red]Fel: ANTHROPIC_API_KEY saknas i .env[/red]")
        return

    # Ladda marknadsdata
    console.print("Laddar marknadsdata...")
    market_data = MarketData()
    market_data.load_benchmark()
    stocks = market_data.load_multiple(SAMPLE_TICKERS)
    console.print(f"Laddade {len(stocks)} aktier")

    # Screena aktier
    console.print("\nScreenar kandidater...")
    screener = Screener()
    candidates = screener.get_candidates(stocks, top_n=5)
    console.print(f"Hittade {len(candidates)} kandidater")

    for result in candidates:
        console.print(f"  {result.stock.ticker}: score {result.score:.0f}")

    # Här skulle Claude-analys anropas
    console.print("\n[yellow]Claude-analys är inte implementerad i detta läge.[/yellow]")
    console.print("Kör med --with-claude för full analys.")


def show_portfolio() -> None:
    """Visa portföljstatus."""
    portfolio = Portfolio()
    summary = portfolio.get_summary()

    console.print("[bold]Portföljöversikt[/bold]\n")
    console.print(f"Totalt värde: {summary['total_value']:,.0f} SEK")
    console.print(f"Kassa: {summary['cash']:,.0f} SEK")
    console.print(f"Antal positioner: {summary['num_positions']}")
    console.print(f"Total avkastning: {summary['total_return_pct']:+.1f}%")

    if portfolio.state.positions:
        console.print("\n[bold]Positioner[/bold]")
        for ticker, pos in portfolio.state.positions.items():
            pnl_style = "green" if pos.unrealized_pnl_pct >= 0 else "red"
            console.print(
                f"  {ticker}: {pos.shares} st @ {pos.avg_cost:.2f} SEK "
                f"([{pnl_style}]{pos.unrealized_pnl_pct:+.1f}%[/{pnl_style}])"
            )


def show_performance() -> None:
    """Visa prestandahistorik."""
    tracker = PerformanceTracker()
    summary = tracker.get_summary()

    console.print("[bold]Prestandaöversikt[/bold]\n")

    if summary.get("statistics", {}).get("message"):
        console.print(f"[dim]{summary['statistics']['message']}[/dim]")
        return

    stats = summary["statistics"]
    console.print(f"Dagar spårade: {stats['days_tracked']}")
    console.print(f"Kumulativ avkastning: {stats['current_cumulative_pct']:+.1f}%")
    console.print(f"vs Benchmark: {stats['vs_benchmark_pct']:+.1f}%")
    console.print(f"Sharpe ratio (årlig): {stats['sharpe_ratio_annualized']:.2f}")
    console.print(f"Max drawdown: {stats['max_drawdown_pct']:.1f}%")
    console.print(f"Win rate: {stats['win_rate_pct']:.0f}%")


def smart_daily(send_email: bool = False) -> None:
    """Smart daglig rapport med Claude-rekommendationer."""
    console.print("[bold blue]Claude Small-Cap SE - Smart Daglig Rapport[/bold blue]\n")

    settings = get_settings()

    if not settings.anthropic_api_key:
        console.print("[red]Varning: ANTHROPIC_API_KEY saknas - begränsade rekommendationer[/red]\n")

    # Ladda portfölj
    portfolio = Portfolio()
    console.print(f"Laddar portfölj... {len(portfolio.state.positions)} positioner\n")

    # Generera smart rapport
    console.print("Analyserar marknaden och genererar rekommendationer...")
    console.print("(Detta kan ta 1-2 minuter)\n")

    report = generate_smart_daily_report(portfolio)

    # Visa rapport
    console.print("[bold]PORTFÖLJÖVERSIKT[/bold]")
    p = report["portfolio"]
    console.print(f"Totalt värde: {p['total_value']:,.0f} SEK")
    console.print(f"Kassa: {p['cash']:,.0f} SEK")
    console.print(f"Positioner: {p['positions_value']:,.0f} SEK\n")

    console.print(f"Benchmark (OMXSPI): {report['benchmark']['daily_change']:+.1f}% idag\n")

    console.print("[bold]DINA POSITIONER[/bold]")
    for pos in report["positions"]:
        pnl_style = "green" if pos["unrealized_pnl_pct"] >= 0 else "red"
        console.print(
            f"  {pos['ticker']}: {pos['shares']} st @ {pos['avg_cost']:.2f} "
            f"-> {pos['current_price']:.2f} SEK "
            f"[{pnl_style}]({pos['unrealized_pnl_pct']:+.1f}%)[/{pnl_style}]"
        )

    # Rekommendationer
    recs = report["recommendations"]

    if recs["sell"]:
        console.print("\n[bold red]SÄLJREKOMMENDATIONER[/bold red]")
        for rec in recs["sell"]:
            console.print(f"  ! {rec['ticker']}: {rec['reason']}")

    if recs["buy"]:
        console.print("\n[bold green]KÖPREKOMMENDATIONER (3 smarta val)[/bold green]")
        for i, rec in enumerate(recs["buy"], 1):
            console.print(f"  {i}. {rec['ticker']} - {rec.get('name', '')}")
            console.print(f"     Pris: {rec['price']:.2f} SEK")
            console.print(f"     Anledning: {rec['reason']}")

    # Alerts
    if report["alerts"]:
        console.print("\n[bold yellow]ALERTS[/bold yellow]")
        for alert in report["alerts"]:
            console.print(f"  ! {alert['message']}")

    # Skicka e-post
    if send_email:
        console.print("\nSkickar e-postrapport...")
        if send_smart_report_email(report):
            console.print("[green]E-post skickad![/green]")
        else:
            console.print("[red]Kunde inte skicka e-post[/red]")


def main() -> None:
    """Huvudentry."""
    parser = argparse.ArgumentParser(
        description="Claude Small-Cap SE - AI-driven aktiehandel"
    )
    parser.add_argument(
        "command",
        choices=["daily", "weekly", "portfolio", "performance", "smart"],
        nargs="?",
        default="daily",
        help="Kommando att köra",
    )
    parser.add_argument(
        "--with-claude",
        action="store_true",
        help="Inkludera Claude-analys",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Skicka rapport via e-post",
    )

    args = parser.parse_args()

    if args.command == "daily":
        daily_run(send_email=args.email)
    elif args.command == "weekly":
        weekly_analysis()
    elif args.command == "portfolio":
        show_portfolio()
    elif args.command == "performance":
        show_performance()
    elif args.command == "smart":
        smart_daily(send_email=args.email)


if __name__ == "__main__":
    main()
