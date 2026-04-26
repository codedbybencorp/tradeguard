"""JSON-backed persistence for trade plans, validation history, and risk profile."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional

from pydantic import TypeAdapter

from tradeguard.models import RiskProfile, TradePlan, ValidationResult


DEFAULT_DATA_DIR = Path(
    os.environ.get("TRADEGUARD_HOME", str(Path.home() / ".tradeguard"))
)

_PLAN_LIST_ADAPTER = TypeAdapter(list[TradePlan])
_VALIDATION_LIST_ADAPTER = TypeAdapter(list[ValidationResult])


class Storage:
    """Append-mostly JSON storage. One file per kind, atomic writes."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.plans_path = self.data_dir / "plans.json"
        self.history_path = self.data_dir / "history.json"
        self.profile_path = self.data_dir / "profile.json"

    # --- profile -----------------------------------------------------------

    def load_profile(self) -> Optional[RiskProfile]:
        if not self.profile_path.exists():
            return None
        with self.profile_path.open("r", encoding="utf-8") as f:
            return RiskProfile.model_validate_json(f.read())

    def save_profile(self, profile: RiskProfile) -> None:
        self._atomic_write(self.profile_path, profile.model_dump_json(indent=2))

    # --- plans -------------------------------------------------------------

    def load_plans(self) -> list[TradePlan]:
        return self._read_list(self.plans_path, _PLAN_LIST_ADAPTER)

    def append_plan(self, plan: TradePlan) -> None:
        plans = self.load_plans()
        plans.append(plan)
        self._write_list(self.plans_path, _PLAN_LIST_ADAPTER, plans)

    def replace_plans(self, plans: Iterable[TradePlan]) -> None:
        self._write_list(self.plans_path, _PLAN_LIST_ADAPTER, list(plans))

    # --- validation history ------------------------------------------------

    def load_history(self) -> list[ValidationResult]:
        return self._read_list(self.history_path, _VALIDATION_LIST_ADAPTER)

    def append_history(self, result: ValidationResult) -> None:
        history = self.load_history()
        history.append(result)
        self._write_list(self.history_path, _VALIDATION_LIST_ADAPTER, history)

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _read_list(path: Path, adapter: TypeAdapter) -> list:
        if not path.exists():
            return []
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        return adapter.validate_json(raw)

    def _write_list(self, path: Path, adapter: TypeAdapter, items: list) -> None:
        payload = adapter.dump_json(items, indent=2).decode("utf-8")
        self._atomic_write(path, payload)

    def _atomic_write(self, path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def pass_fail_rate(history: list[ValidationResult]) -> tuple[int, int, float]:
    """Return (passed, total, pass_rate_pct)."""
    total = len(history)
    if total == 0:
        return 0, 0, 0.0
    passed = sum(1 for r in history if r.passed)
    return passed, total, round(passed / total * 100, 1)
