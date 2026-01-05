"""Konfiguration för Claude Small-Cap SE."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Ladda miljövariabler
load_dotenv()

# Projektrot
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"


class ScreeningCriteria(BaseModel):
    """Urvalskriterier för aktiescreening."""

    market_cap_min: int = 500_000_000  # 500 MSEK
    market_cap_max: int = 10_000_000_000  # 10 MDSEK
    avg_volume_min: int = 100_000  # Minst 100k daglig volym
    pe_ratio_max: float = 30.0  # P/E under 30
    price_min: float = 5.0  # Minst 5 SEK


class RiskRules(BaseModel):
    """Riskregler för portföljhantering."""

    stop_loss_pct: float = -15.0  # Sälj vid -15%
    take_profit_pct: float = 30.0  # Sälj del vid +30%
    max_position_pct: float = 10.0  # Max 10% av portfölj per aktie
    max_positions: int = 15  # Max 15 positioner
    cash_reserve_pct: float = 10.0  # Alltid 10% kassa


class Settings(BaseModel):
    """Huvudkonfiguration."""

    # API
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Portfölj
    initial_capital: float = float(os.getenv("INITIAL_CAPITAL", "100000"))
    currency: str = os.getenv("CURRENCY", "SEK")

    # Regler
    screening: ScreeningCriteria = ScreeningCriteria()
    risk: RiskRules = RiskRules()

    # Benchmark
    benchmark_ticker: str = "^OMXSPI"  # OMXS Stockholm PI
    benchmark_name: str = "OMXSPI"

    # Marknader att screena
    markets: list[str] = [
        "Small Cap Stockholm",
        "First North Stockholm",
    ]


# Global settings instans
settings = Settings()


def get_settings() -> Settings:
    """Hämta konfiguration."""
    return settings
