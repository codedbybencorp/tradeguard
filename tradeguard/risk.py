"""Risk math.

Position sizing, daily-budget accounting, and correlated-exposure checks.
All money values flow through Decimal to avoid floating-point drift on
financial math.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import ROUND_DOWN, Decimal
from typing import Iterable

from tradeguard.models import RiskProfile, TradePlan, TradeSetup


_QUANTUM = Decimal("0.0001")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_DOWN)


def position_size(setup: TradeSetup, profile: RiskProfile) -> tuple[Decimal, Decimal]:
    """Return (units, dollar_risk) sized to the per-trade risk cap.

    Sized on stop distance, not target — risk is what you actually lose if
    you're wrong, not what you hope to make.
    """
    risk_per_unit = setup.risk_per_unit
    if risk_per_unit <= 0:
        return Decimal("0"), Decimal("0")

    max_dollar_risk = profile.risk_per_trade_dollars
    units = _quantize(max_dollar_risk / risk_per_unit)
    dollar_risk = (units * risk_per_unit).quantize(Decimal("0.01"))
    return units, dollar_risk


def daily_risk_used(plans: Iterable[TradePlan], on_day: date | None = None) -> Decimal:
    """Sum dollar_risk across plans created on `on_day` (UTC). Default: today."""
    target = on_day or datetime.now(timezone.utc).date()
    total = Decimal("0")
    for plan in plans:
        created = plan.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created.astimezone(timezone.utc).date() == target:
            total += plan.dollar_risk
    return total.quantize(Decimal("0.01"))


def correlated_exposure(
    setup: TradeSetup,
    candidate_dollar_risk: Decimal,
    open_plans: Iterable[TradePlan],
) -> Decimal:
    """Sum dollar risk of open plans whose symbol is in `setup.correlated_symbols`,
    plus the candidate trade itself."""
    correlated = {s.upper() for s in setup.correlated_symbols} | {setup.symbol.upper()}
    total = candidate_dollar_risk
    for plan in open_plans:
        if plan.setup.symbol.upper() in correlated:
            total += plan.dollar_risk
    return total.quantize(Decimal("0.01"))


@dataclass
class RiskBudgetReport:
    """Snapshot of where the trader stands against their daily risk budget."""

    budget: Decimal
    used: Decimal
    remaining: Decimal
    pct_used: Decimal
    over_budget: bool

    @classmethod
    def build(cls, profile: RiskProfile, plans: Iterable[TradePlan]) -> "RiskBudgetReport":
        used = daily_risk_used(plans)
        budget = profile.daily_risk_budget_dollars
        remaining = (budget - used).quantize(Decimal("0.01"))
        pct = (used / budget * Decimal("100")).quantize(Decimal("0.1")) if budget > 0 else Decimal("0")
        return cls(
            budget=budget.quantize(Decimal("0.01")),
            used=used,
            remaining=remaining,
            pct_used=pct,
            over_budget=used >= budget,
        )
