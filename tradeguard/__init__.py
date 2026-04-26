"""TradeGuard — pre-trade risk validation and setup scoring."""

from tradeguard.models import (
    Direction,
    Grade,
    RiskProfile,
    TradePlan,
    TradeSetup,
    ValidationResult,
)
from tradeguard.risk import (
    RiskBudgetReport,
    correlated_exposure,
    daily_risk_used,
    position_size,
)
from tradeguard.validator import score_setup, validate_setup

__version__ = "0.1.0"

__all__ = [
    "Direction",
    "Grade",
    "RiskBudgetReport",
    "RiskProfile",
    "TradePlan",
    "TradeSetup",
    "ValidationResult",
    "correlated_exposure",
    "daily_risk_used",
    "position_size",
    "score_setup",
    "validate_setup",
    "__version__",
]
