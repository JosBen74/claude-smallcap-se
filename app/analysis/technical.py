"""Teknisk analys."""

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class TechnicalIndicators:
    """Samling av tekniska indikatorer."""

    rsi_14: float | None  # RSI 14 dagar
    sma_20: float | None  # Simple Moving Average 20 dagar
    sma_50: float | None  # Simple Moving Average 50 dagar
    sma_200: float | None  # Simple Moving Average 200 dagar
    macd: float | None  # MACD line
    macd_signal: float | None  # MACD signal line
    macd_histogram: float | None  # MACD histogram
    bollinger_upper: float | None  # Bollinger band övre
    bollinger_lower: float | None  # Bollinger band undre
    atr_14: float | None  # Average True Range 14 dagar


class TechnicalAnalysis:
    """Beräkna tekniska indikatorer."""

    def __init__(self, prices: pd.DataFrame):
        """Initiera med prisdata.

        Args:
            prices: DataFrame med OHLCV-data (Open, High, Low, Close, Volume)
        """
        self.prices = prices
        self._close = prices["Close"]
        self._high = prices["High"]
        self._low = prices["Low"]

    def calculate_all(self) -> TechnicalIndicators:
        """Beräkna alla indikatorer.

        Returns:
            TechnicalIndicators med alla värden
        """
        return TechnicalIndicators(
            rsi_14=self.rsi(14),
            sma_20=self.sma(20),
            sma_50=self.sma(50),
            sma_200=self.sma(200),
            macd=self.macd()[0],
            macd_signal=self.macd()[1],
            macd_histogram=self.macd()[2],
            bollinger_upper=self.bollinger_bands()[0],
            bollinger_lower=self.bollinger_bands()[1],
            atr_14=self.atr(14),
        )

    def sma(self, period: int) -> float | None:
        """Simple Moving Average.

        Args:
            period: Antal perioder

        Returns:
            Senaste SMA-värde
        """
        if len(self._close) < period:
            return None
        return float(self._close.rolling(window=period).mean().iloc[-1])

    def ema(self, period: int) -> float | None:
        """Exponential Moving Average.

        Args:
            period: Antal perioder

        Returns:
            Senaste EMA-värde
        """
        if len(self._close) < period:
            return None
        return float(self._close.ewm(span=period, adjust=False).mean().iloc[-1])

    def rsi(self, period: int = 14) -> float | None:
        """Relative Strength Index.

        Args:
            period: Antal perioder (standard 14)

        Returns:
            RSI-värde (0-100)
        """
        if len(self._close) < period + 1:
            return None

        delta = self._close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def macd(
        self, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[float | None, float | None, float | None]:
        """Moving Average Convergence Divergence.

        Args:
            fast: Snabb EMA-period
            slow: Långsam EMA-period
            signal: Signal-period

        Returns:
            Tuple med (MACD line, Signal line, Histogram)
        """
        if len(self._close) < slow + signal:
            return None, None, None

        ema_fast = self._close.ewm(span=fast, adjust=False).mean()
        ema_slow = self._close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return (
            float(macd_line.iloc[-1]),
            float(signal_line.iloc[-1]),
            float(histogram.iloc[-1]),
        )

    def bollinger_bands(
        self, period: int = 20, std_dev: float = 2.0
    ) -> tuple[float | None, float | None]:
        """Bollinger Bands.

        Args:
            period: Antal perioder för SMA
            std_dev: Antal standardavvikelser

        Returns:
            Tuple med (Upper band, Lower band)
        """
        if len(self._close) < period:
            return None, None

        sma = self._close.rolling(window=period).mean()
        std = self._close.rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return float(upper.iloc[-1]), float(lower.iloc[-1])

    def atr(self, period: int = 14) -> float | None:
        """Average True Range.

        Args:
            period: Antal perioder

        Returns:
            ATR-värde
        """
        if len(self._close) < period + 1:
            return None

        high_low = self._high - self._low
        high_close = np.abs(self._high - self._close.shift())
        low_close = np.abs(self._low - self._close.shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return float(atr.iloc[-1])

    def get_trend_signal(self) -> str:
        """Bedöm trendsignal baserat på moving averages.

        Returns:
            "bullish", "bearish" eller "neutral"
        """
        sma20 = self.sma(20)
        sma50 = self.sma(50)
        current = float(self._close.iloc[-1])

        if sma20 is None or sma50 is None:
            return "neutral"

        if current > sma20 > sma50:
            return "bullish"
        elif current < sma20 < sma50:
            return "bearish"
        else:
            return "neutral"

    def get_rsi_signal(self) -> str:
        """Bedöm RSI-signal.

        Returns:
            "overbought", "oversold" eller "neutral"
        """
        rsi = self.rsi()
        if rsi is None:
            return "neutral"

        if rsi > 70:
            return "overbought"
        elif rsi < 30:
            return "oversold"
        else:
            return "neutral"
