"""Portföljhantering."""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import DATA_DIR, get_settings
from ..data.yfinance_se import get_stock_info


@dataclass
class Position:
    """En portföljposition."""

    ticker: str
    shares: int
    avg_cost: float  # Genomsnittlig inköpspris
    current_price: float = 0.0
    last_updated: str = ""

    @property
    def market_value(self) -> float:
        """Marknadsvärde."""
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        """Totalt inköpspris."""
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        """Orealiserad vinst/förlust."""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        """Orealiserad vinst/förlust i procent."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Transaction:
    """En transaktion."""

    timestamp: str
    ticker: str
    action: str  # buy, sell
    shares: int
    price: float
    amount: float  # Totalt belopp
    fees: float = 0.0
    notes: str = ""


@dataclass
class PortfolioState:
    """Portföljens tillstånd."""

    positions: dict[str, Position] = field(default_factory=dict)
    cash: float = 0.0
    transactions: list[Transaction] = field(default_factory=list)
    created_at: str = ""
    last_updated: str = ""


class Portfolio:
    """Hanterar portföljen."""

    def __init__(self, data_path: Path | None = None):
        """Initiera portfölj.

        Args:
            data_path: Sökväg till portföljfil
        """
        self.data_path = data_path or DATA_DIR / "portfolio.json"
        self.state = PortfolioState()
        self._load()

    def _load(self) -> None:
        """Ladda portfölj från fil."""
        if self.data_path.exists():
            with open(self.data_path) as f:
                data = json.load(f)

            self.state = PortfolioState(
                positions={
                    k: Position(**v) for k, v in data.get("positions", {}).items()
                },
                cash=data.get("cash", 0.0),
                transactions=[
                    Transaction(**t) for t in data.get("transactions", [])
                ],
                created_at=data.get("created_at", ""),
                last_updated=data.get("last_updated", ""),
            )
        else:
            # Ny portfölj
            settings = get_settings()
            self.state = PortfolioState(
                cash=settings.initial_capital,
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
            )
            self._save()

    def _save(self) -> None:
        """Spara portfölj till fil."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.state.last_updated = datetime.now().isoformat()

        data = {
            "positions": {k: asdict(v) for k, v in self.state.positions.items()},
            "cash": self.state.cash,
            "transactions": [asdict(t) for t in self.state.transactions],
            "created_at": self.state.created_at,
            "last_updated": self.state.last_updated,
        }

        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def buy(
        self,
        ticker: str,
        shares: int,
        price: float,
        fees: float = 0.0,
        notes: str = "",
    ) -> Transaction:
        """Köp aktier.

        Args:
            ticker: Aktiesymbol
            shares: Antal aktier
            price: Pris per aktie
            fees: Courtage
            notes: Anteckningar

        Returns:
            Transaktionen
        """
        amount = shares * price + fees

        if amount > self.state.cash:
            raise ValueError(
                f"Otillräcklig kassa: behöver {amount:.2f} SEK, har {self.state.cash:.2f} SEK"
            )

        # Uppdatera position
        if ticker in self.state.positions:
            pos = self.state.positions[ticker]
            total_shares = pos.shares + shares
            total_cost = pos.cost_basis + (shares * price)
            pos.shares = total_shares
            pos.avg_cost = total_cost / total_shares
            pos.current_price = price
            pos.last_updated = datetime.now().isoformat()
        else:
            self.state.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                avg_cost=price,
                current_price=price,
                last_updated=datetime.now().isoformat(),
            )

        # Uppdatera kassa
        self.state.cash -= amount

        # Logga transaktion
        tx = Transaction(
            timestamp=datetime.now().isoformat(),
            ticker=ticker,
            action="buy",
            shares=shares,
            price=price,
            amount=amount,
            fees=fees,
            notes=notes,
        )
        self.state.transactions.append(tx)
        self._save()

        return tx

    def sell(
        self,
        ticker: str,
        shares: int,
        price: float,
        fees: float = 0.0,
        notes: str = "",
    ) -> Transaction:
        """Sälj aktier.

        Args:
            ticker: Aktiesymbol
            shares: Antal aktier att sälja
            price: Pris per aktie
            fees: Courtage
            notes: Anteckningar

        Returns:
            Transaktionen
        """
        if ticker not in self.state.positions:
            raise ValueError(f"Ingen position i {ticker}")

        pos = self.state.positions[ticker]
        if shares > pos.shares:
            raise ValueError(
                f"Kan inte sälja {shares} aktier, har bara {pos.shares}"
            )

        amount = shares * price - fees

        # Uppdatera position
        pos.shares -= shares
        pos.current_price = price
        pos.last_updated = datetime.now().isoformat()

        if pos.shares == 0:
            del self.state.positions[ticker]

        # Uppdatera kassa
        self.state.cash += amount

        # Logga transaktion
        tx = Transaction(
            timestamp=datetime.now().isoformat(),
            ticker=ticker,
            action="sell",
            shares=shares,
            price=price,
            amount=amount,
            fees=fees,
            notes=notes,
        )
        self.state.transactions.append(tx)
        self._save()

        return tx

    def update_prices(self) -> None:
        """Uppdatera aktuella priser för alla positioner."""
        for ticker, pos in self.state.positions.items():
            try:
                info = get_stock_info(ticker)
                if info.get("current_price"):
                    pos.current_price = info["current_price"]
                    pos.last_updated = datetime.now().isoformat()
            except Exception as e:
                print(f"Kunde inte uppdatera pris för {ticker}: {e}")

        self._save()

    @property
    def total_value(self) -> float:
        """Totalt portföljvärde."""
        positions_value = sum(p.market_value for p in self.state.positions.values())
        return positions_value + self.state.cash

    @property
    def positions_value(self) -> float:
        """Värde av alla positioner."""
        return sum(p.market_value for p in self.state.positions.values())

    def get_allocation(self) -> dict[str, float]:
        """Hämta allokering per position i procent.

        Returns:
            Dict med ticker -> procent av portfölj
        """
        total = self.total_value
        if total == 0:
            return {}

        alloc = {
            ticker: (pos.market_value / total) * 100
            for ticker, pos in self.state.positions.items()
        }
        alloc["_cash"] = (self.state.cash / total) * 100
        return alloc

    def get_summary(self) -> dict[str, Any]:
        """Sammanfattning av portföljen.

        Returns:
            Dict med portföljdata
        """
        settings = get_settings()
        total = self.total_value
        initial = settings.initial_capital

        return {
            "total_value": total,
            "cash": self.state.cash,
            "positions_value": self.positions_value,
            "num_positions": len(self.state.positions),
            "total_return": total - initial,
            "total_return_pct": ((total - initial) / initial) * 100 if initial > 0 else 0,
            "allocation": self.get_allocation(),
            "last_updated": self.state.last_updated,
        }
