"""yFinance-integration för svenska aktier."""

from typing import Any
import yfinance as yf
import pandas as pd


def get_swedish_stock(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Hämta historisk kursdata för en svensk aktie.

    Args:
        ticker: Aktiesymbol (med eller utan .ST suffix)
        period: Tidsperiod (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

    Returns:
        DataFrame med OHLCV-data
    """
    symbol = _normalize_ticker(ticker)
    stock = yf.Ticker(symbol)
    return stock.history(period=period)


def get_stock_info(ticker: str) -> dict[str, Any]:
    """Hämta fundamental data för en aktie.

    Args:
        ticker: Aktiesymbol

    Returns:
        Dict med aktieinfo (P/E, market cap, etc.)
    """
    symbol = _normalize_ticker(ticker)
    stock = yf.Ticker(symbol)
    info = stock.info

    return {
        "ticker": ticker,
        "symbol": symbol,
        "name": info.get("longName", info.get("shortName", ticker)),
        "currency": info.get("currency", "SEK"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "pb_ratio": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "avg_volume": info.get("averageVolume"),
        "avg_volume_10d": info.get("averageVolume10days"),
        "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
        "previous_close": info.get("previousClose"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }


def get_multiple_stocks(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Hämta historisk data för flera aktier.

    Args:
        tickers: Lista med aktiesymboler
        period: Tidsperiod

    Returns:
        Dict med ticker -> DataFrame
    """
    result = {}
    for ticker in tickers:
        try:
            result[ticker] = get_swedish_stock(ticker, period)
        except Exception as e:
            print(f"Kunde inte hämta {ticker}: {e}")
    return result


def get_index_data(index: str = "^OMXSPI", period: str = "1y") -> pd.DataFrame:
    """Hämta indexdata för benchmark.

    Args:
        index: Indexsymbol (^OMXSPI för Stockholm PI)
        period: Tidsperiod

    Returns:
        DataFrame med indexdata
    """
    idx = yf.Ticker(index)
    return idx.history(period=period)


def _normalize_ticker(ticker: str) -> str:
    """Normalisera ticker till yFinance-format.

    Args:
        ticker: Aktiesymbol

    Returns:
        Symbol med .ST suffix om det saknas
    """
    if ticker.startswith("^"):
        return ticker  # Index behåller prefix
    if not ticker.endswith(".ST"):
        return f"{ticker}.ST"
    return ticker


# Vanliga svenska aktier för test
SAMPLE_TICKERS = [
    "EMBRAC-B",  # Embracer Group
    "SINCH",  # Sinch
    "BOOZT",  # Boozt
    "BICO",  # BICO Group
    "CINT",  # Cint Group
    "STILLFRONT",  # Stillfront Group
    "VIMIAN",  # Vimian Group
    "NORDNET",  # Nordnet
    "AVANZA",  # Avanza Bank
    "LIFCO-B",  # Lifco
]
