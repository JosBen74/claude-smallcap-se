"""Kombinerad marknadsdataklass."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from .yfinance_se import get_swedish_stock, get_stock_info, get_index_data


@dataclass
class StockData:
    """Data för en enskild aktie."""

    ticker: str
    name: str
    current_price: float
    previous_close: float
    market_cap: float | None
    pe_ratio: float | None
    avg_volume: int | None
    history: pd.DataFrame
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def daily_change(self) -> float:
        """Daglig förändring i procent."""
        if self.previous_close and self.previous_close > 0:
            return ((self.current_price - self.previous_close) / self.previous_close) * 100
        return 0.0

    @property
    def weekly_change(self) -> float:
        """Veckoförändring i procent."""
        if len(self.history) < 5:
            return 0.0
        week_ago = self.history["Close"].iloc[-5]
        return ((self.current_price - week_ago) / week_ago) * 100

    @property
    def monthly_change(self) -> float:
        """Månadsförändring i procent."""
        if len(self.history) < 21:
            return 0.0
        month_ago = self.history["Close"].iloc[-21]
        return ((self.current_price - month_ago) / month_ago) * 100


class MarketData:
    """Samlar marknaddata för analys."""

    def __init__(self) -> None:
        self.stocks: dict[str, StockData] = {}
        self.benchmark: pd.DataFrame | None = None
        self.last_updated: datetime | None = None

    def load_stock(self, ticker: str, period: str = "1y") -> StockData:
        """Ladda data för en aktie.

        Args:
            ticker: Aktiesymbol
            period: Tidsperiod

        Returns:
            StockData-objekt
        """
        history = get_swedish_stock(ticker, period)
        info = get_stock_info(ticker)

        stock_data = StockData(
            ticker=ticker,
            name=info.get("name", ticker),
            current_price=info.get("current_price", 0.0) or 0.0,
            previous_close=info.get("previous_close", 0.0) or 0.0,
            market_cap=info.get("market_cap"),
            pe_ratio=info.get("pe_ratio"),
            avg_volume=info.get("avg_volume"),
            history=history,
            info=info,
        )

        self.stocks[ticker] = stock_data
        self.last_updated = datetime.now()
        return stock_data

    def load_multiple(self, tickers: list[str], period: str = "1y") -> list[StockData]:
        """Ladda data för flera aktier.

        Args:
            tickers: Lista med aktiesymboler
            period: Tidsperiod

        Returns:
            Lista med StockData-objekt
        """
        result = []
        for ticker in tickers:
            try:
                stock = self.load_stock(ticker, period)
                result.append(stock)
            except Exception as e:
                print(f"Kunde inte ladda {ticker}: {e}")
        return result

    def load_benchmark(self, index: str = "^OMXSPI", period: str = "1y") -> pd.DataFrame:
        """Ladda benchmarkdata.

        Args:
            index: Indexsymbol
            period: Tidsperiod

        Returns:
            DataFrame med indexdata
        """
        self.benchmark = get_index_data(index, period)
        return self.benchmark

    def get_benchmark_change(self, days: int = 5) -> float:
        """Hämta benchmarkförändring över antal dagar.

        Args:
            days: Antal dagar

        Returns:
            Förändring i procent
        """
        if self.benchmark is None or len(self.benchmark) < days:
            return 0.0
        start = self.benchmark["Close"].iloc[-days]
        end = self.benchmark["Close"].iloc[-1]
        return ((end - start) / start) * 100

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av laddad data.

        Returns:
            Dict med sammanfattning
        """
        return {
            "num_stocks": len(self.stocks),
            "stocks": list(self.stocks.keys()),
            "benchmark_loaded": self.benchmark is not None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
