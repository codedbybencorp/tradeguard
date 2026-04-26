"""Tests for TradeGuard risk math."""

from decimal import Decimal

from tradeguard.models import Direction, RiskProfile, TradeSetup
from tradeguard.risk import RiskBudgetReport, daily_risk_used, position_size


def test_position_size_long():
    setup = TradeSetup(
        symbol="AAPL", direction=Direction.LONG,
        entry=Decimal("100"), stop=Decimal("95"), target=Decimal("110"),
        trend_score=20, sr_score=20, confluence_score=20, timing_score=20,
    )
    profile = RiskProfile(account_size=Decimal("10000"))
    units, risk = position_size(setup, profile)
    assert risk == Decimal("100.00")
    assert units == Decimal("20")


def test_daily_risk_used_empty():
    assert daily_risk_used([]) == Decimal("0")


def test_risk_budget_report():
    profile = RiskProfile(account_size=Decimal("10000"))
    report = RiskBudgetReport.build(profile, [])
    assert report.budget == Decimal("300.00")
    assert report.used == Decimal("0")
    assert report.remaining == Decimal("300.00")
    assert report.over_budget is False
