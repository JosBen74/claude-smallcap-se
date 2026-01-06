"""Smart daglig rapport med Claude-rekommendationer."""

import os
from datetime import datetime
from typing import Any

from ..config import get_settings
from ..data.market_data import MarketData
from ..data.yfinance_se import get_stock_info, get_swedish_stock, SAMPLE_TICKERS
from ..analysis.screener import Screener
from ..analysis.technical import TechnicalAnalysis
from ..analysis.fundamental import FundamentalAnalysis
from ..trading.portfolio import Portfolio
from ..trading.rules import RiskManager
from ..claude.analyst import Analyst


# Utökad lista med svenska aktier att screena
SCREENING_UNIVERSE = [
    # Small Cap
    "EMBRAC-B", "SINCH", "BOOZT", "BICO", "CINT",
    "VIMIAN", "LIFCO-B", "LAGERCRANTZ-B", "ADDTECH-B",
    # First North
    "VISC", "COFFEE-B", "MILDEF", "SEYE",
    # Mid Cap
    "SAAB-B", "SSAB-A", "SSAB-B", "BOLIDEN", "LUNDIN-MINING",
    "ELECTROLUX-B", "HUSQVARNA-B", "SKF-B",
    # Tillväxt
    "EVO", "NIBE-B", "HEXAGON-B", "ASSA-ABLOY-B",
]


def generate_smart_daily_report(portfolio: Portfolio) -> dict[str, Any]:
    """Generera smart daglig rapport med Claude-analys.

    Args:
        portfolio: Portföljen att analysera

    Returns:
        Dict med komplett rapport inkl. rekommendationer
    """
    settings = get_settings()
    market_data = MarketData()

    # Ladda benchmark
    try:
        market_data.load_benchmark()
        benchmark_change = market_data.get_benchmark_change(1)
        benchmark_week = market_data.get_benchmark_change(5)
    except:
        benchmark_change = 0.0
        benchmark_week = 0.0

    # Uppdatera portföljpriser
    portfolio.update_prices()

    # Kontrollera riskregler
    risk_manager = RiskManager(portfolio)
    alerts = risk_manager.check_all()

    # Grundläggande portföljdata
    report = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "portfolio": {
            "total_value": portfolio.total_value,
            "cash": portfolio.state.cash,
            "positions_value": portfolio.positions_value,
            "num_positions": len(portfolio.state.positions),
        },
        "benchmark": {
            "name": "OMXSPI",
            "daily_change": benchmark_change,
            "weekly_change": benchmark_week,
        },
        "positions": [],
        "alerts": [{"type": a.alert_type, "message": a.message, "severity": a.severity} for a in alerts],
        "recommendations": {
            "buy": [],
            "sell": [],
            "hold": [],
        },
    }

    # Analysera varje position
    for ticker, pos in portfolio.state.positions.items():
        # Hämta dagens förändring
        daily_change_pct = 0.0
        daily_change_sek = 0.0
        try:
            history = get_swedish_stock(ticker, period="5d")
            if len(history) >= 2:
                prev_close = history["Close"].iloc[-2]
                current = history["Close"].iloc[-1]
                daily_change_pct = ((current - prev_close) / prev_close) * 100
                daily_change_sek = (current - prev_close) * pos.shares
        except:
            pass

        position_data = {
            "ticker": ticker,
            "shares": pos.shares,
            "avg_cost": pos.avg_cost,
            "current_price": pos.current_price,
            "market_value": pos.market_value,
            "unrealized_pnl": pos.unrealized_pnl,
            "unrealized_pnl_pct": pos.unrealized_pnl_pct,
            "daily_change_pct": daily_change_pct,
            "daily_change_sek": daily_change_sek,
        }
        report["positions"].append(position_data)

    # Claude-analys om API-nyckel finns
    if settings.anthropic_api_key:
        try:
            analyst = Analyst()

            # Analysera säljkandidater (nuvarande positioner)
            for pos_data in report["positions"]:
                ticker = pos_data["ticker"]
                pnl = pos_data["unrealized_pnl_pct"]

                # Rekommendera försäljning vid stora förluster eller vinster
                if pnl <= -15:
                    report["recommendations"]["sell"].append({
                        "ticker": ticker,
                        "reason": f"Stop-loss: {pnl:.1f}% förlust",
                        "action": "SÄLJ",
                    })
                elif pnl >= 30:
                    report["recommendations"]["sell"].append({
                        "ticker": ticker,
                        "reason": f"Take-profit: {pnl:.1f}% vinst",
                        "action": "ÖVERVÄG DELSÄLJNING",
                    })
                else:
                    report["recommendations"]["hold"].append({
                        "ticker": ticker,
                        "pnl_pct": pnl,
                    })

            # Hitta 3 köpkandidater
            buy_picks = _find_buy_candidates(analyst, market_data, portfolio)
            report["recommendations"]["buy"] = buy_picks[:3]

        except Exception as e:
            report["claude_error"] = str(e)

    return report


def _find_buy_candidates(analyst: Analyst, market_data: MarketData, portfolio: Portfolio) -> list[dict]:
    """Hitta köpkandidater från screening-universumet.

    Returns:
        Lista med topp köpkandidater
    """
    candidates = []
    current_holdings = set(portfolio.state.positions.keys())

    for ticker in SCREENING_UNIVERSE:
        # Skippa aktier vi redan äger
        if ticker in current_holdings:
            continue

        try:
            info = get_stock_info(ticker)
            if not info.get("current_price"):
                continue

            history = get_swedish_stock(ticker, period="3mo")
            if len(history) < 20:
                continue

            # Teknisk analys
            ta = TechnicalAnalysis(history)
            rsi = ta.rsi()
            trend = ta.get_trend_signal()

            # Fundamental
            fa = FundamentalAnalysis(info)
            val_score, _ = fa.get_valuation_score()

            # Beräkna kursförändring
            current = history["Close"].iloc[-1]
            week_ago = history["Close"].iloc[-5] if len(history) >= 5 else current
            month_ago = history["Close"].iloc[-21] if len(history) >= 21 else current

            week_change = ((current - week_ago) / week_ago) * 100
            month_change = ((current - month_ago) / month_ago) * 100

            # Poängsätt kandidaten
            score = 50

            # RSI-bonus (köp vid översålt)
            if rsi and rsi < 30:
                score += 20
            elif rsi and rsi < 40:
                score += 10
            elif rsi and rsi > 70:
                score -= 15  # Överköpt = minus

            # Trend-bonus
            if trend == "bullish":
                score += 10
            elif trend == "bearish":
                score -= 10

            # Värdering
            score += (val_score - 50) * 0.3

            # Momentum (måttligt positivt är bra)
            if 5 < month_change < 20:
                score += 10
            elif month_change > 30:
                score -= 10  # För het

            candidates.append({
                "ticker": ticker,
                "name": info.get("name", ticker),
                "price": info["current_price"],
                "rsi": rsi,
                "trend": trend,
                "week_change": week_change,
                "month_change": month_change,
                "score": score,
                "market_cap": info.get("market_cap", 0),
            })

        except Exception as e:
            continue

    # Sortera efter score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Formatera topp 3
    result = []
    for c in candidates[:3]:
        result.append({
            "ticker": c["ticker"],
            "name": c["name"],
            "price": c["price"],
            "reason": _generate_buy_reason(c),
            "score": c["score"],
        })

    return result


def _generate_buy_reason(candidate: dict) -> str:
    """Generera köpmotivering."""
    reasons = []

    if candidate.get("rsi") and candidate["rsi"] < 35:
        reasons.append(f"Översåld (RSI {candidate['rsi']:.0f})")

    if candidate.get("trend") == "bullish":
        reasons.append("Positiv trend")

    if 5 < candidate.get("month_change", 0) < 20:
        reasons.append(f"Stabilt momentum (+{candidate['month_change']:.0f}% månad)")

    if not reasons:
        reasons.append("Attraktiv värdering")

    return ", ".join(reasons)


def format_smart_email(report: dict) -> tuple[str, str]:
    """Formatera rapport för e-post.

    Returns:
        Tuple med (subject, body)
    """
    p = report["portfolio"]

    subject = f"Börsrapport {report['date']} | {p['total_value']:,.0f} SEK"

    body = f"""DAGLIG BÖRSRAPPORT - {report['date']}
{'='*50}

PORTFÖLJÖVERSIKT
Totalt värde: {p['total_value']:,.0f} SEK
Kassa: {p['cash']:,.0f} SEK
Positioner: {p['positions_value']:,.0f} SEK

Benchmark (OMXSPI): {report['benchmark']['daily_change']:+.1f}% idag

DINA POSITIONER
{'-'*50}
"""

    for pos in report["positions"]:
        daily_pct = pos.get('daily_change_pct', 0)
        daily_sek = pos.get('daily_change_sek', 0)
        body += f"""
{pos['ticker']}
  {pos['shares']} st @ {pos['avg_cost']:.2f} SEK -> {pos['current_price']:.2f} SEK
  Idag:  {daily_pct:+.1f}% ({daily_sek:+,.0f} SEK)
  Totalt: {pos['unrealized_pnl_pct']:+.1f}% ({pos['unrealized_pnl']:+,.0f} SEK)
  Värde: {pos['market_value']:,.0f} SEK
"""

    # Alerts
    if report["alerts"]:
        body += f"\n{'='*50}\nALERTS\n"
        for alert in report["alerts"]:
            body += f"  ! {alert['message']}\n"

    # Rekommendationer
    body += f"\n{'='*50}\nREKOMMENDATIONER\n"

    # Säljrekommendationer
    if report["recommendations"]["sell"]:
        body += "\nSÄLJ:\n"
        for rec in report["recommendations"]["sell"]:
            body += f"  {rec['ticker']}: {rec['reason']}\n"

    # Köprekommendationer
    if report["recommendations"]["buy"]:
        body += "\nKÖP (3 smarta val):\n"
        for i, rec in enumerate(report["recommendations"]["buy"], 1):
            body += f"""
  {i}. {rec['ticker']} ({rec['name']})
     Pris: {rec['price']:.2f} SEK
     Anledning: {rec['reason']}
"""

    body += f"""
{'='*50}
Genererad av Claude Small-Cap SE
"""

    return subject, body
