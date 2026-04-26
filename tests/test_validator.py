"""Tests for TradeGuard validator."""

from decimal import Decimal

from tradeguard.models import Direction, Grade, RiskProfile, TradeSetup
from tradeguard.validator import build_plan, score_setup, validate_setup


def test_score_setup():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("95"), target=Decimal("110"),
        trend_score=25, sr_score=25, confluence_score=25, timing_score=25,
    )
    score, grade, comps = score_setup(setup)
    assert score == 100
    assert grade == Grade.A_PLUS
    assert comps["trend"] == 25


def test_validate_setup_passes():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("95"), target=Decimal("115"),
        trend_score=25, sr_score=25, confluence_score=25, timing_score=25,
    )
    profile = RiskProfile(account_size=Decimal("10000"))
    result = validate_setup(setup, profile)
    assert result.passed is True
    assert result.grade == Grade.A_PLUS


def test_validate_setup_fails_low_grade():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("95"), target=Decimal("115"),
        trend_score=5, sr_score=5, confluence_score=5, timing_score=5,
    )
    profile = RiskProfile(account_size=Decimal("10000"))
    result = validate_setup(setup, profile)
    assert result.passed is False
    assert "Grade F" in result.reasons[0]


def test_validate_setup_fails_low_rr():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("99"), target=Decimal("100.5"),
        trend_score=25, sr_score=25, confluence_score=25, timing_score=25,
    )
    profile = RiskProfile(account_size=Decimal("10000"), min_rr=Decimal("2.0"))
    result = validate_setup(setup, profile)
    assert result.passed is False


def test_build_plan_returns_none_on_fail():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("99"), target=Decimal("100.5"),
        trend_score=25, sr_score=25, confluence_score=25, timing_score=25,
    )
    profile = RiskProfile(account_size=Decimal("10000"), min_rr=Decimal("2.0"))
    result, plan = build_plan(setup, profile)
    assert plan is None
    assert result.passed is False


def test_build_plan_returns_plan_on_pass():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("95"), target=Decimal("115"),
        trend_score=25, sr_score=25, confluence_score=25, timing_score=25,
    )
    profile = RiskProfile(account_size=Decimal("10000"))
    result, plan = build_plan(setup, profile)
    assert plan is not None
    assert plan.dollar_risk == Decimal("100.00")
    assert plan.position_size == Decimal("20")
