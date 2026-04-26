"""Setup scoring and validation.

A setup is scored across four equal components (each 0-25, total 0-100):

- Trend       — alignment with the higher-timeframe trend
- S/R         — quality of the support/resistance level being traded
- Confluence  — number of independent signals agreeing
- Timing      — quality of the trigger / session timing

The total maps to a letter grade. By default only A and A+ setups pass; the
threshold is configurable per RiskProfile. R:R below the profile minimum
forces a fail regardless of grade — a beautiful chart with bad geometry is
still a bad trade.
"""

from __future__ import annotations

from decimal import Decimal

from tradeguard.models import (
    Grade,
    RiskProfile,
    TradePlan,
    TradeSetup,
    ValidationResult,
)
from tradeguard.risk import (
    RiskBudgetReport,
    correlated_exposure,
    position_size,
)


_GRADE_ORDER = [Grade.F, Grade.C, Grade.B, Grade.A, Grade.A_PLUS]


def _grade_for(score: int) -> Grade:
    if score >= 90:
        return Grade.A_PLUS
    if score >= 80:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 60:
        return Grade.C
    return Grade.F


def _grade_at_least(actual: Grade, minimum: Grade) -> bool:
    return _GRADE_ORDER.index(actual) >= _GRADE_ORDER.index(minimum)


def score_setup(setup: TradeSetup) -> tuple[int, Grade, dict[str, int]]:
    """Compute the raw score, letter grade, and per-component breakdown."""
    components = {
        "trend": setup.trend_score,
        "sr": setup.sr_score,
        "confluence": setup.confluence_score,
        "timing": setup.timing_score,
    }
    total = sum(components.values())
    return total, _grade_for(total), components


def validate_setup(
    setup: TradeSetup,
    profile: RiskProfile,
    open_plans: list[TradePlan] | None = None,
) -> ValidationResult:
    """Score the setup, then gate on grade, R:R, and risk-budget checks."""
    open_plans = open_plans or []
    score, grade, components = score_setup(setup)

    reasons: list[str] = []
    warnings: list[str] = []
    passed = True

    if not _grade_at_least(grade, profile.min_passing_grade):
        passed = False
        reasons.append(
            f"Grade {grade.value} below minimum {profile.min_passing_grade.value}."
        )

    rr = setup.rr
    if rr < profile.min_rr:
        passed = False
        reasons.append(
            f"R:R {rr:.2f} below minimum {profile.min_rr:.2f}."
        )

    _, dollar_risk = position_size(setup, profile)
    if dollar_risk == 0:
        passed = False
        reasons.append("Stop distance is zero — cannot size position.")

    budget_report = RiskBudgetReport.build(profile, open_plans)
    projected_used = budget_report.used + dollar_risk
    if projected_used > profile.daily_risk_budget_dollars:
        passed = False
        reasons.append(
            f"Trade would exceed daily risk budget "
            f"(${projected_used:.2f} > ${profile.daily_risk_budget_dollars:.2f})."
        )
    elif projected_used > profile.daily_risk_budget_dollars * Decimal("0.8"):
        warnings.append(
            f"Daily risk usage will reach "
            f"{projected_used / profile.daily_risk_budget_dollars * 100:.0f}% after this trade."
        )

    correlated_total = correlated_exposure(setup, dollar_risk, open_plans)
    if correlated_total > profile.max_correlated_exposure_dollars:
        passed = False
        reasons.append(
            f"Correlated exposure ${correlated_total:.2f} exceeds cap "
            f"${profile.max_correlated_exposure_dollars:.2f}."
        )

    if passed:
        reasons.append(
            f"Grade {grade.value} ({score}/100), R:R {rr:.2f}, risk ${dollar_risk:.2f}."
        )

    return ValidationResult(
        symbol=setup.symbol,
        score=score,
        grade=grade,
        passed=passed,
        reasons=reasons,
        warnings=warnings,
        component_scores=components,
        rr=rr,
    )


def build_plan(
    setup: TradeSetup,
    profile: RiskProfile,
    open_plans: list[TradePlan] | None = None,
) -> tuple[ValidationResult, TradePlan | None]:
    """Validate and, if it passes, build the executable trade plan."""
    open_plans = open_plans or []
    result = validate_setup(setup, profile, open_plans)
    if not result.passed:
        return result, None

    units, dollar_risk = position_size(setup, profile)
    dollar_reward = (units * setup.reward_per_unit).quantize(Decimal("0.01"))

    budget_report = RiskBudgetReport.build(profile, open_plans)
    daily_used_after = (budget_report.used + dollar_risk).quantize(Decimal("0.01"))
    daily_remaining_after = (
        profile.daily_risk_budget_dollars - daily_used_after
    ).quantize(Decimal("0.01"))
    correlated_after = correlated_exposure(setup, dollar_risk, open_plans)

    plan = TradePlan(
        setup=setup,
        profile=profile,
        validation=result,
        position_size=units,
        dollar_risk=dollar_risk,
        dollar_reward=dollar_reward,
        daily_risk_used_after=daily_used_after,
        daily_risk_remaining_after=daily_remaining_after,
        correlated_exposure_after=correlated_after,
    )
    return result, plan
