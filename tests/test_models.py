"""Tests for TradeGuard models."""

from decimal import Decimal

import pytest

from tradeguard.models import Direction, Grade, RiskProfile, TradeSetup


def test_trade_setup_geometry_long():
    setup = TradeSetup(
        symbol="AAPL",
        direction=Direction.LONG,
        entry=Decimal("150"),
        stop=Decimal("145"),
        target=Decimal("160"),
        trend_score=20, sr_score=20, confluence_score=20, timing_score=20,
    )
    assert setup.rr == Decimal("2")
    assert setup.risk_per_unit == Decimal("5")
    assert setup.reward_per_unit == Decimal("10")


def test_trade_setup_geometry_short():
    setup = TradeSetup(
        symbol="TSLA",
        direction=Direction.SHORT,
        entry=Decimal("200"),
        stop=Decimal("210"),
        target=Decimal("180"),
        trend_score=20, sr_score=20, confluence_score=20, timing_score=20,
    )
    assert setup.rr == Decimal("2")
    assert setup.risk_per_unit == Decimal("10")


def test_trade_setup_invalid_long_stop():
    with pytest.raises(ValueError):
        TradeSetup(
            symbol="AAPL",
            direction=Direction.LONG,
            entry=Decimal("150"),
            stop=Decimal("155"),
            target=Decimal("160"),
            trend_score=20, sr_score=20, confluence_score=20, timing_score=20,
        )


def test_risk_profile_math():
    profile = RiskProfile(account_size=Decimal("10000"))
    assert profile.risk_per_trade_dollars == Decimal("100")
    assert profile.daily_risk_budget_dollars == Decimal("300")


def test_grade_enum():
    assert Grade.A_PLUS.value == "A+"
    assert Grade.A.value == "A"
