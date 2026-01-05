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
from .claude.analyst import Analyst
from .analysis.technical import TechnicalAnalysis
from .analysis.fundamental import FundamentalAnalysis
from .data.yfinance_se import get_stock_info, get_swedish_stock


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


def weekly_analysis(send_email: bool = False) -> None:
    """Veckovis djupanalys med Claude."""
    console.print("[bold blue]Claude Small-Cap SE - Veckoanalys[/bold blue]\n")

    settings = get_settings()

    # Kontrollera API-nyckel
    if not settings.anthropic_api_key:
        console.print("[red]Fel: ANTHROPIC_API_KEY saknas i .env[/red]")
        return

    # Ladda portfölj
    portfolio = Portfolio()
    portfolio.update_prices()

    # Ladda marknadsdata
    console.print("Laddar marknadsdata...")
    market_data = MarketData()
    market_data.load_benchmark()
    stocks = market_data.load_multiple(SAMPLE_TICKERS)
    console.print(f"Laddade {len(stocks)} aktier")

    # Benchmark-data
    benchmark_week = market_data.get_benchmark_change(5)
    benchmark_ytd = market_data.get_benchmark_change(252)  # ca 1 ar

    # Screena aktier
    console.print("\nScreenar kandidater...")
    screener = Screener()
    candidates = screener.get_candidates(stocks, top_n=5)
    console.print(f"Hittade {len(candidates)} kandidater\n")

    # Formatera portfoljsammanfattning
    portfolio_summary = _format_portfolio_summary(portfolio)

    # Formatera kandidatdata med teknisk/fundamental analys
    console.print("Analyserar kandidater (teknisk + fundamental)...")
    candidate_stocks, technical_signals = _format_candidates_data(candidates)

    # Berakna portfolj YTD (forenklad)
    portfolio_ytd = 0.0
    initial_capital = settings.initial_capital or 100000
    if initial_capital > 0:
        portfolio_ytd = ((portfolio.total_value / initial_capital) - 1) * 100

    # Anropa Claude
    console.print("\n[bold]Skickar till Claude for djupanalys...[/bold]")
    console.print("(Detta kan ta 30-60 sekunder)\n")

    analyst = Analyst()
    try:
        result = analyst.weekly_analysis(
            portfolio_summary=portfolio_summary,
            candidate_stocks=candidate_stocks,
            omxspi_change=benchmark_week,
            benchmark_ytd=benchmark_ytd,
            portfolio_ytd=portfolio_ytd,
            technical_signals=technical_signals,
        )

        # Visa resultat
        _display_weekly_result(result)

        # Spara rapport
        _save_weekly_report(result, portfolio)

        # Skicka e-post om flagga ar satt
        if send_email:
            _send_weekly_email(result, portfolio)

    except Exception as e:
        console.print(f"[red]Fel vid Claude-analys: {e}[/red]")


def _format_portfolio_summary(portfolio: Portfolio) -> str:
    """Formatera portfoljsammanfattning for Claude."""
    lines = [
        f"Totalt varde: {portfolio.total_value:,.0f} SEK",
        f"Kassa: {portfolio.state.cash:,.0f} SEK ({portfolio.state.cash / portfolio.total_value * 100:.1f}%)",
        f"Antal positioner: {len(portfolio.state.positions)}",
        "",
        "Nuvarande positioner:",
    ]

    for ticker, pos in portfolio.state.positions.items():
        weight = pos.market_value / portfolio.total_value * 100
        lines.append(
            f"  - {ticker}: {pos.shares} st @ {pos.avg_cost:.2f} SEK "
            f"(nu: {pos.current_price:.2f} SEK, {pos.unrealized_pnl_pct:+.1f}%, vikt: {weight:.1f}%)"
        )

    return "\n".join(lines)


def _format_candidates_data(candidates) -> tuple[str, str]:
    """Formatera kandidatdata med teknisk och fundamental analys."""
    candidate_lines = []
    signal_lines = []

    for result in candidates:
        stock = result.stock
        ticker = stock.ticker

        try:
            # Hamta mer data
            info = get_stock_info(ticker)
            history = get_swedish_stock(ticker, period="3mo")

            # Teknisk analys
            ta = TechnicalAnalysis(history)
            rsi = ta.rsi() or 0
            sma20 = ta.sma(20)
            sma50 = ta.sma(50)
            trend = ta.get_trend_signal()

            # Fundamental analys
            fa = FundamentalAnalysis(info)
            val_score, val_details = fa.get_valuation_score()

            # Kursforandring
            current = history["Close"].iloc[-1]
            week_ago = history["Close"].iloc[-5] if len(history) >= 5 else current
            month_ago = history["Close"].iloc[-21] if len(history) >= 21 else current

            week_change = ((current - week_ago) / week_ago) * 100
            month_change = ((current - month_ago) / month_ago) * 100

            # Kandidatinfo
            candidate_lines.append(f"""
### {ticker} ({info.get('name', 'N/A')})
- Pris: {stock.current_price:.2f} SEK
- Market Cap: {(stock.market_cap or 0) / 1e9:.2f} MDSEK
- P/E: {stock.pe_ratio or 'N/A'}
- P/B: {info.get('pb_ratio', 'N/A')}
- ROE: {info.get('roe', 'N/A')}
- Vecka: {week_change:+.1f}%, Manad: {month_change:+.1f}%
- Varderingsscore: {val_score}/100
- Screening score: {result.score:.0f}/100
""")

            # Tekniska signaler
            signal_lines.append(
                f"- {ticker}: RSI={rsi:.0f}, Trend={trend}, "
                f"SMA20={sma20:.2f if sma20 else 'N/A'}, SMA50={sma50:.2f if sma50 else 'N/A'}"
            )

        except Exception as e:
            candidate_lines.append(f"\n### {ticker}\n- Fel vid datahamtning: {e}\n")
            signal_lines.append(f"- {ticker}: Data saknas")

    return "\n".join(candidate_lines), "\n".join(signal_lines)


def _display_weekly_result(result: dict) -> None:
    """Visa veckoanalysresultat."""
    console.print("[bold green]KOPREKOMMODATIONER[/bold green]")
    for rec in result.get("buy_recommendations", []):
        console.print(f"  {rec['ticker']}: {rec.get('allocation_pct', 5)}% av portfolj")
        console.print(f"    Risk: {rec.get('risk_level', 'medium')}")
        console.print(f"    Motivering: {rec.get('reasoning', 'N/A')}")
        console.print()

    if result.get("sell_recommendations"):
        console.print("[bold red]SALJREKOMMENDATIONER[/bold red]")
        for rec in result["sell_recommendations"]:
            console.print(f"  {rec['ticker']}: {rec.get('action', 'sell')}")
            console.print(f"    Motivering: {rec.get('reasoning', 'N/A')}")
            console.print()

    if result.get("hold_positions"):
        console.print("[bold yellow]BEHALL[/bold yellow]")
        console.print(f"  {', '.join(result['hold_positions'])}")
        console.print()

    console.print("[bold]MARKNADSUTBLICK[/bold]")
    console.print(f"  {result.get('market_outlook', 'N/A')}")
    console.print(f"\n  Konfidensniva: {result.get('confidence_level', 'medium')}")


def _save_weekly_report(result: dict, portfolio: Portfolio) -> None:
    """Spara veckorapport till fil."""
    from pathlib import Path
    import json

    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    filepath = reports_dir / f"weekly_{timestamp}.json"

    report_data = {
        "date": timestamp,
        "portfolio_value": portfolio.total_value,
        "analysis": result,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[dim]Rapport sparad: {filepath}[/dim]")


def _send_weekly_email(result: dict, portfolio: Portfolio) -> None:
    """Skicka veckorapport via e-post."""
    from .reporting.notifications import send_email_report

    subject = f"Veckoanalys {datetime.now().strftime('%Y-%m-%d')} | {portfolio.total_value:,.0f} SEK"

    body = f"""VECKOVIS DJUPANALYS - Claude Small-Cap SE
{'='*50}

KOPREKOMMODATIONER
"""
    for rec in result.get("buy_recommendations", []):
        body += f"\n{rec['ticker']} ({rec.get('allocation_pct', 5)}% allokering)\n"
        body += f"  Risk: {rec.get('risk_level', 'medium')}\n"
        body += f"  {rec.get('reasoning', '')}\n"

    if result.get("sell_recommendations"):
        body += "\nSALJREKOMMENDATIONER\n"
        for rec in result["sell_recommendations"]:
            body += f"\n{rec['ticker']}: {rec.get('reasoning', '')}\n"

    body += f"\nMARKNADSUTBLICK\n{result.get('market_outlook', '')}\n"
    body += f"\nKonfidensniva: {result.get('confidence_level', 'medium')}\n"

    if send_email_report(subject, body):
        console.print("[green]Veckorapport skickad via e-post![/green]")
    else:
        console.print("[red]Kunde inte skicka e-post[/red]")


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
        weekly_analysis(send_email=args.email)
    elif args.command == "portfolio":
        show_portfolio()
    elif args.command == "performance":
        show_performance()
    elif args.command == "smart":
        smart_daily(send_email=args.email)


if __name__ == "__main__":
    main()
