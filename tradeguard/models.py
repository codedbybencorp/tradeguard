"""Pydantic models for TradeGuard.

The core domain objects: a trade *setup* (what the trader sees), a *risk profile*
(what they're willing to lose), a *validation result* (what TradeGuard says), and
the resulting *trade plan* (what to actually execute).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class Grade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    F = "F"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TradeSetup(BaseModel):
    """A trade setup before validation.

    Scores are subjective inputs from the trader's analysis. The validator
    combines them into a single grade.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=1, max_length=16)
    direction: Direction
    entry: Decimal = Field(..., gt=0)
    stop: Decimal = Field(..., gt=0)
    target: Decimal = Field(..., gt=0)

    trend_score: int = Field(..., ge=0, le=25, description="Alignment with higher-timeframe trend.")
    sr_score: int = Field(..., ge=0, le=25, description="Quality of support/resistance level.")
    confluence_score: int = Field(..., ge=0, le=25, description="Number of independent signals agreeing.")
    timing_score: int = Field(..., ge=0, le=25, description="Quality of trigger / session timing.")

    notes: Optional[str] = Field(default=None, max_length=2000)
    correlated_symbols: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def _check_geometry(self) -> "TradeSetup":
        if self.direction is Direction.LONG:
            if self.stop >= self.entry:
                raise ValueError("Long stop must be below entry.")
            if self.target <= self.entry:
                raise ValueError("Long target must be above entry.")
        else:
            if self.stop <= self.entry:
                raise ValueError("Short stop must be above entry.")
            if self.target >= self.entry:
                raise ValueError("Short target must be below entry.")
        return self

    @property
    def risk_per_unit(self) -> Decimal:
        return abs(self.entry - self.stop)

    @property
    def reward_per_unit(self) -> Decimal:
        return abs(self.target - self.entry)

    @property
    def rr(self) -> Decimal:
        if self.risk_per_unit == 0:
            return Decimal("0")
        return self.reward_per_unit / self.risk_per_unit


class RiskProfile(BaseModel):
    """The trader's hard limits. These are the numbers the account survives on."""

    model_config = ConfigDict(extra="forbid")

    account_size: Decimal = Field(..., gt=0)
    risk_per_trade_pct: Decimal = Field(default=Decimal("1.0"), gt=0, le=Decimal("5.0"))
    daily_risk_budget_pct: Decimal = Field(default=Decimal("3.0"), gt=0, le=Decimal("10.0"))
    max_correlated_exposure_pct: Decimal = Field(default=Decimal("2.0"), gt=0, le=Decimal("10.0"))
    min_passing_grade: Grade = Field(default=Grade.A)
    min_rr: Decimal = Field(default=Decimal("1.5"), gt=0)

    @property
    def risk_per_trade_dollars(self) -> Decimal:
        return self.account_size * self.risk_per_trade_pct / Decimal("100")

    @property
    def daily_risk_budget_dollars(self) -> Decimal:
        return self.account_size * self.daily_risk_budget_pct / Decimal("100")

    @property
    def max_correlated_exposure_dollars(self) -> Decimal:
        return self.account_size * self.max_correlated_exposure_pct / Decimal("100")


class ValidationResult(BaseModel):
    """The verdict on a setup. `passed` gates whether a TradePlan should be built."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    score: int = Field(..., ge=0, le=100)
    grade: Grade
    passed: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    component_scores: dict[str, int] = Field(default_factory=dict)
    rr: Decimal
    evaluated_at: datetime = Field(default_factory=_utcnow)


class TradePlan(BaseModel):
    """An executable plan derived from a validated setup and risk profile."""

    model_config = ConfigDict(extra="forbid")

    setup: TradeSetup
    profile: RiskProfile
    validation: ValidationResult

    position_size: Decimal = Field(..., ge=0)
    dollar_risk: Decimal = Field(..., ge=0)
    dollar_reward: Decimal = Field(..., ge=0)
    daily_risk_used_after: Decimal = Field(..., ge=0)
    daily_risk_remaining_after: Decimal
    correlated_exposure_after: Decimal = Field(..., ge=0)

    created_at: datetime = Field(default_factory=_utcnow)
