"""TradeGuard Web Dashboard — FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from tradeguard.models import Direction, RiskProfile, TradeSetup
from tradeguard.risk import RiskBudgetReport
from tradeguard.storage import Storage, pass_fail_rate
from tradeguard.validator import build_plan

app = FastAPI(title="TradeGuard", version="0.1.0")

# Template / static setup
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR.parent.parent / "static"

if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _render(name: str, context: dict) -> str:
    template = jinja_env.get_template(name)
    return template.render(**context)


def _storage() -> Storage:
    return Storage()


def _dashboard_context(request: Request, extra: dict | None = None) -> dict:
    storage = _storage()
    profile = storage.load_profile()
    plans = storage.load_plans()
    history = storage.load_history()
    passed, total, rate = pass_fail_rate(history)
    budget_report = RiskBudgetReport.build(profile, plans) if profile else None
    recent = list(reversed(history[-10:]))
    ctx = {
        "request": request,
        "profile": profile,
        "budget_report": budget_report,
        "recent": recent,
        "plans_count": len(plans),
        "history_count": total,
        "pass_rate": rate,
        "passed_count": passed,
    }
    if extra:
        ctx.update(extra)
    return ctx


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    ctx = _dashboard_context(request)
    return HTMLResponse(content=_render("index.html", ctx))


@app.post("/validate", response_class=HTMLResponse)
def validate_setup_web(
    request: Request,
    symbol: str = Form(...),
    direction: str = Form(...),
    entry: float = Form(...),
    stop: float = Form(...),
    target: float = Form(...),
    trend_score: int = Form(...),
    sr_score: int = Form(...),
    confluence_score: int = Form(...),
    timing_score: int = Form(...),
    correlated_symbols: str = Form(default=""),
):
    storage = _storage()
    profile = storage.load_profile()
    if profile is None:
        ctx = _dashboard_context(request, {"error": "No risk profile configured. Set one up via the CLI first: tradeguard profile --reset"})
        return HTMLResponse(content=_render("index.html", ctx))

    setup = TradeSetup(
        symbol=symbol.upper(),
        direction=Direction(direction),
        entry=entry,
        stop=stop,
        target=target,
        trend_score=trend_score,
        sr_score=sr_score,
        confluence_score=confluence_score,
        timing_score=timing_score,
        correlated_symbols=[s.strip().upper() for s in correlated_symbols.split(",") if s.strip()],
    )
    open_plans = storage.load_plans()
    result, plan = build_plan(setup, profile, open_plans)
    storage.append_history(result)
    if plan:
        storage.append_plan(plan)

    ctx = _dashboard_context(request, {
        "result": result,
        "plan": plan,
        "setup": setup,
    })
    return HTMLResponse(content=_render("index.html", ctx))
