"""Tests för datahämtning."""

import pytest


def test_normalize_ticker():
    """Test ticker-normalisering."""
    from app.data.yfinance_se import _normalize_ticker

    assert _normalize_ticker("EMBRAC-B") == "EMBRAC-B.ST"
    assert _normalize_ticker("EMBRAC-B.ST") == "EMBRAC-B.ST"
    assert _normalize_ticker("^OMXSPI") == "^OMXSPI"


def test_sample_tickers_exist():
    """Verifiera att sample tickers är definierade."""
    from app.data.yfinance_se import SAMPLE_TICKERS

    assert len(SAMPLE_TICKERS) > 0
    assert "EMBRAC-B" in SAMPLE_TICKERS


def test_screening_criteria():
    """Test screening-kriterier."""
    from app.config import ScreeningCriteria

    criteria = ScreeningCriteria()
    assert criteria.market_cap_min == 500_000_000
    assert criteria.market_cap_max == 10_000_000_000
    assert criteria.pe_ratio_max == 30.0


def test_risk_rules():
    """Test riskregler."""
    from app.config import RiskRules

    rules = RiskRules()
    assert rules.stop_loss_pct == -15.0
    assert rules.take_profit_pct == 30.0
    assert rules.max_positions == 15
