"""Prestandamätning och benchmark-jämförelse."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR
from ..data.yfinance_se import get_index_data


@dataclass
class DailySnapshot:
    """Daglig ögonblicksbild av portföljen."""

    date: str
    total_value: float
    cash: float
    positions_value: float
    benchmark_value: float
    daily_return_pct: float
    benchmark_return_pct: float
    cumulative_return_pct: float
    benchmark_cumulative_pct: float


class PerformanceTracker:
    """Spårar portföljprestand a över tid."""

    def __init__(self, data_path: Path | None = None):
        """Initiera tracker.

        Args:
            data_path: Sökväg till datafil
        """
        self.data_path = data_path or DATA_DIR / "performance.json"
        self.snapshots: list[DailySnapshot] = []
        self.initial_value: float = 0.0
        self.initial_benchmark: float = 0.0
        self._load()

    def _load(self) -> None:
        """Ladda historik från fil."""
        if self.data_path.exists():
            with open(self.data_path) as f:
                data = json.load(f)
            self.snapshots = [DailySnapshot(**s) for s in data.get("snapshots", [])]
            self.initial_value = data.get("initial_value", 0.0)
            self.initial_benchmark = data.get("initial_benchmark", 0.0)

    def _save(self) -> None:
        """Spara historik till fil."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "initial_value": self.initial_value,
            "initial_benchmark": self.initial_benchmark,
            "snapshots": [asdict(s) for s in self.snapshots],
        }
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def record_snapshot(
        self,
        total_value: float,
        cash: float,
        benchmark_value: float | None = None,
    ) -> DailySnapshot:
        """Registrera daglig ögonblicksbild.

        Args:
            total_value: Totalt portföljvärde
            cash: Kassa
            benchmark_value: Benchmarkvärde (eller hämta automatiskt)

        Returns:
            Skapad snapshot
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Hämta benchmark om inte angiven
        if benchmark_value is None:
            try:
                benchmark_data = get_index_data("^OMXSPI", period="5d")
                benchmark_value = float(benchmark_data["Close"].iloc[-1])
            except Exception:
                benchmark_value = self.initial_benchmark or 1000.0

        # Sätt initiala värden om första snapshot
        if not self.snapshots:
            self.initial_value = total_value
            self.initial_benchmark = benchmark_value

        # Beräkna returns
        if self.snapshots:
            prev = self.snapshots[-1]
            daily_return = ((total_value - prev.total_value) / prev.total_value) * 100
            benchmark_daily = (
                (benchmark_value - prev.benchmark_value) / prev.benchmark_value
            ) * 100
        else:
            daily_return = 0.0
            benchmark_daily = 0.0

        cumulative = ((total_value - self.initial_value) / self.initial_value) * 100
        benchmark_cumulative = (
            (benchmark_value - self.initial_benchmark) / self.initial_benchmark
        ) * 100

        snapshot = DailySnapshot(
            date=today,
            total_value=total_value,
            cash=cash,
            positions_value=total_value - cash,
            benchmark_value=benchmark_value,
            daily_return_pct=daily_return,
            benchmark_return_pct=benchmark_daily,
            cumulative_return_pct=cumulative,
            benchmark_cumulative_pct=benchmark_cumulative,
        )

        # Ersätt om samma dag finns
        if self.snapshots and self.snapshots[-1].date == today:
            self.snapshots[-1] = snapshot
        else:
            self.snapshots.append(snapshot)

        self._save()
        return snapshot

    def get_returns(self, period_days: int = 30) -> dict[str, Any]:
        """Hämta avkastning för period.

        Args:
            period_days: Antal dagar att beräkna för

        Returns:
            Dict med avkastningsdata
        """
        if not self.snapshots:
            return {
                "period_days": period_days,
                "portfolio_return_pct": 0.0,
                "benchmark_return_pct": 0.0,
                "alpha": 0.0,
            }

        # Hämta relevanta snapshots
        relevant = self.snapshots[-period_days:] if len(self.snapshots) >= period_days else self.snapshots

        if len(relevant) < 2:
            return {
                "period_days": len(relevant),
                "portfolio_return_pct": 0.0,
                "benchmark_return_pct": 0.0,
                "alpha": 0.0,
            }

        start = relevant[0]
        end = relevant[-1]

        portfolio_return = ((end.total_value - start.total_value) / start.total_value) * 100
        benchmark_return = (
            (end.benchmark_value - start.benchmark_value) / start.benchmark_value
        ) * 100

        return {
            "period_days": len(relevant),
            "portfolio_return_pct": portfolio_return,
            "benchmark_return_pct": benchmark_return,
            "alpha": portfolio_return - benchmark_return,
            "start_date": start.date,
            "end_date": end.date,
        }

    def get_statistics(self) -> dict[str, Any]:
        """Beräkna prestandastatistik.

        Returns:
            Dict med statistik
        """
        if len(self.snapshots) < 2:
            return {"message": "Otillräcklig data för statistik"}

        returns = [s.daily_return_pct for s in self.snapshots[1:]]

        import numpy as np

        returns_arr = np.array(returns)

        # Beräkna metrics
        avg_daily = float(np.mean(returns_arr))
        std_daily = float(np.std(returns_arr))
        sharpe = (avg_daily / std_daily * np.sqrt(252)) if std_daily > 0 else 0.0

        # Max drawdown
        cumulative = [s.cumulative_return_pct for s in self.snapshots]
        peak = cumulative[0]
        max_drawdown = 0.0
        for val in cumulative:
            if val > peak:
                peak = val
            drawdown = peak - val
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Winning days
        winning_days = len([r for r in returns if r > 0])
        win_rate = (winning_days / len(returns)) * 100 if returns else 0

        return {
            "days_tracked": len(self.snapshots),
            "avg_daily_return_pct": avg_daily,
            "volatility_daily_pct": std_daily,
            "sharpe_ratio_annualized": sharpe,
            "max_drawdown_pct": max_drawdown,
            "win_rate_pct": win_rate,
            "current_cumulative_pct": self.snapshots[-1].cumulative_return_pct,
            "vs_benchmark_pct": (
                self.snapshots[-1].cumulative_return_pct
                - self.snapshots[-1].benchmark_cumulative_pct
            ),
        }

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av prestanda.

        Returns:
            Dict med sammanfattning
        """
        stats = self.get_statistics()
        returns_30d = self.get_returns(30)
        returns_90d = self.get_returns(90)

        return {
            "statistics": stats,
            "returns_30d": returns_30d,
            "returns_90d": returns_90d,
            "snapshots_count": len(self.snapshots),
            "latest": asdict(self.snapshots[-1]) if self.snapshots else None,
        }
