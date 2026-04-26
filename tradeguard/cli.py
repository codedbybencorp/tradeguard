"""TradeGuard CLI — beautiful, fast, disciplined."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.prompt import FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from tradeguard.models import Direction, Grade, RiskProfile, TradeSetup
from tradeguard.risk import RiskBudgetReport
from tradeguard.storage import Storage, pass_fail_rate
from tradeguard.validator import build_plan, score_setup, validate_setup

app = typer.Typer(
    name="tradeguard",
    help="Validate trade setups and enforce risk discipline before every trade.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _get_storage() -> Storage:
    return Storage()


def _load_or_create_profile(storage: Storage) -> RiskProfile:
    profile = storage.load_profile()
    if profile is not None:
        return profile
    console.print(Panel(
        "[bold yellow]No risk profile found. Let's create one.[/bold yellow]\n"
        "These are the hard limits that keep your account alive.",
        title="Risk Profile Setup",
        border_style="yellow",
    ))
    account = Decimal(str(FloatPrompt.ask("Account size ($)", default=10000.0)))
    risk_trade = Decimal(str(FloatPrompt.ask("Risk per trade (%)", default=1.0)))
    risk_day = Decimal(str(FloatPrompt.ask("Daily risk budget (%)", default=3.0)))
    corr = Decimal(str(FloatPrompt.ask("Max correlated exposure (%)", default=2.0)))
    min_rr = Decimal(str(FloatPrompt.ask("Minimum R:R", default=1.5)))
    min_grade_str = Prompt.ask("Minimum passing grade", choices=["A+", "A", "B", "C", "F"], default="A")
    min_grade = Grade(min_grade_str)
    profile = RiskProfile(
        account_size=account,
        risk_per_trade_pct=risk_trade,
        daily_risk_budget_pct=risk_day,
        max_correlated_exposure_pct=corr,
        min_rr=min_rr,
        min_passing_grade=min_grade,
    )
    storage.save_profile(profile)
    console.print(Panel(
        f"Account: [green]${profile.account_size:,.2f}[/green]\n"
        f"Per-trade risk: [green]{profile.risk_per_trade_pct}% (${profile.risk_per_trade_dollars:,.2f})[/green]\n"
        f"Daily budget: [green]{profile.daily_risk_budget_pct}% (${profile.daily_risk_budget_dollars:,.2f})[/green]",
        title="Profile Saved",
        border_style="green",
    ))
    return profile


def _prompt_setup() -> TradeSetup:
    symbol = Prompt.ask("Symbol", default="AAPL").upper()
    direction = Direction(Prompt.ask("Direction", choices=["long", "short"], default="long"))
    entry = Decimal(str(FloatPrompt.ask("Entry price", default=150.0)))
    stop = Decimal(str(FloatPrompt.ask("Stop loss", default=145.0)))
    target = Decimal(str(FloatPrompt.ask("Target", default=160.0)))
    console.print("\n[dim]Score each component 0-25 (be honest — your account depends on it):[/dim]")
    trend = IntPrompt.ask("Trend score", default=20)
    sr = IntPrompt.ask("S/R score", default=18)
    confluence = IntPrompt.ask("Confluence score", default=15)
    timing = IntPrompt.ask("Timing score", default=20)
    correlated_raw = Prompt.ask("Correlated symbols (comma-separated, or leave blank)", default="")
    correlated = [s.strip().upper() for s in correlated_raw.split(",") if s.strip()]
    return TradeSetup(
        symbol=symbol,
        direction=direction,
        entry=entry,
        stop=stop,
        target=target,
        trend_score=trend,
        sr_score=sr,
        confluence_score=confluence,
        timing_score=timing,
        correlated_symbols=correlated,
    )


def _show_validation(result, setup: TradeSetup, plan: Optional[object] = None):
    color = "green" if result.passed else "red"
    emoji = "✅" if result.passed else "❌"
    title = f"{emoji}  {setup.symbol} — Grade {result.grade.value} ({result.score}/100)"

    table = Table(box=box.ROUNDED, show_header=False, border_style=color)
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value")
    table.add_row("Direction", setup.direction.value.upper())
    table.add_row("Entry", f"${setup.entry:,.2f}")
    table.add_row("Stop", f"${setup.stop:,.2f}")
    table.add_row("Target", f"${setup.target:,.2f}")
    table.add_row("R:R", f"{result.rr:.2f}")
    if plan:
        table.add_row("Position size", f"{plan.position_size:,.4f}")
        table.add_row("Dollar risk", f"[bold red]${plan.dollar_risk:,.2f}[/bold red]")
        table.add_row("Dollar reward", f"[bold green]${plan.dollar_reward:,.2f}[/bold green]")
        table.add_row("Daily used after", f"${plan.daily_risk_used_after:,.2f}")
        table.add_row("Daily remaining", f"${plan.daily_risk_remaining_after:,.2f}")

    comp_table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
    comp_table.add_column("Component", width=12)
    comp_table.add_column("Score", justify="right", width=6)
    comp_table.add_column("Bar")
    for name, score in result.component_scores.items():
        bar = "█" * (score // 3) + "░" * (8 - score // 3)
        comp_table.add_row(name.capitalize(), str(score), bar)

    reasons = "\n".join(f"• {r}" for r in result.reasons)
    warnings = "\n".join(f"• [yellow]{w}[/yellow]" for w in result.warnings) if result.warnings else "[dim]None[/dim]"

    console.print(Panel(table, title=title, border_style=color))
    console.print(comp_table)
    console.print(Panel(reasons, title="Verdict", border_style=color))
    if result.warnings:
        console.print(Panel(warnings, title="Warnings", border_style="yellow"))


@app.command()
def validate():
    """Validate a trade setup interactively."""
    storage = _get_storage()
    profile = _load_or_create_profile(storage)
    setup = _prompt_setup()
    open_plans = storage.load_plans()
    result, plan = build_plan(setup, profile, open_plans)
    _show_validation(result, setup, plan)
    storage.append_history(result)


@app.command()
def plan():
    """Validate and save a trade plan if it passes."""
    storage = _get_storage()
    profile = _load_or_create_profile(storage)
    setup = _prompt_setup()
    open_plans = storage.load_plans()
    result, trade_plan = build_plan(setup, profile, open_plans)
    _show_validation(result, setup, trade_plan)
    storage.append_history(result)
    if trade_plan:
        storage.append_plan(trade_plan)
        console.print(Panel("[bold green]Trade plan saved.[/bold green]", border_style="green"))
    else:
        console.print(Panel("[bold red]Trade plan REJECTED. No plan saved.[/bold red]", border_style="red"))


@app.command()
def profile(
    show: bool = typer.Option(False, "--show", "-s", help="Show current profile"),
    reset: bool = typer.Option(False, "--reset", "-r", help="Reset profile"),
):
    """View or reset your risk profile."""
    storage = _get_storage()
    if reset:
        storage.save_profile(_load_or_create_profile(storage))
        return
    p = storage.load_profile()
    if p is None or show:
        if p is None:
            console.print("[yellow]No profile found. Run [bold]tradeguard profile --reset[/bold] to create one.[/yellow]")
            return
    table = Table(box=box.ROUNDED, title="Risk Profile", border_style="cyan")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("Account size", f"${p.account_size:,.2f}")
    table.add_row("Risk per trade", f"{p.risk_per_trade_pct}% (${p.risk_per_trade_dollars:,.2f})")
    table.add_row("Daily risk budget", f"{p.daily_risk_budget_pct}% (${p.daily_risk_budget_dollars:,.2f})")
    table.add_row("Max correlated exposure", f"{p.max_correlated_exposure_pct}% (${p.max_correlated_exposure_dollars:,.2f})")
    table.add_row("Minimum grade", p.min_passing_grade.value)
    table.add_row("Minimum R:R", str(p.min_rr))
    console.print(table)


@app.command()
def budget():
    """Show daily risk budget usage."""
    storage = _get_storage()
    profile = _load_or_create_profile(storage)
    plans = storage.load_plans()
    report = RiskBudgetReport.build(profile, plans)
    color = "green" if not report.over_budget else "red"
    rem_color = "green" if report.remaining > 0 else "red"
    console.print(Panel(
        f"Budget: [bold]${report.budget:,.2f}[/bold]\n"
        f"Used:   [bold {color}]${report.used:,.2f}[/bold {color}] ({report.pct_used}%)\n"
        f"Remaining: [bold {rem_color}]${report.remaining:,.2f}[/bold {rem_color}]",
        title="Daily Risk Budget",
        border_style=color,
    ))
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Usage", total=float(report.budget), completed=float(report.used))
        progress.update(task, completed=float(report.used))


@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n", help="Number of records to show")):
    """Show recent validation history."""
    storage = _get_storage()
    hist = storage.load_history()
    if not hist:
        console.print("[dim]No history yet.[/dim]")
        return
    table = Table(box=box.ROUNDED, title=f"Last {min(limit, len(hist))} Validations")
    table.add_column("Time", style="dim")
    table.add_column("Symbol")
    table.add_column("Grade", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("R:R", justify="right")
    table.add_column("Result", justify="center")
    for r in reversed(hist[-limit:]):
        time_str = r.evaluated_at.strftime("%H:%M") if hasattr(r.evaluated_at, "strftime") else str(r.evaluated_at)[:16]
        res = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(time_str, r.symbol, r.grade.value, str(r.score), f"{r.rr:.2f}", res)
    console.print(table)
    passed, total, rate = pass_fail_rate(hist)
    console.print(f"\n[bold]Pass rate:[/bold] {passed}/{total} ([cyan]{rate}%[/cyan])")


@app.command()
def stats():
    """Show overall performance stats."""
    storage = _get_storage()
    hist = storage.load_history()
    plans = storage.load_plans()
    if not hist:
        console.print("[dim]No data yet. Start validating setups.[/dim]")
        return
    passed, total, rate = pass_fail_rate(hist)
    scores = [r.score for r in hist]
    avg_score = sum(scores) / len(scores)
    best = max(hist, key=lambda x: x.score)
    worst = min(hist, key=lambda x: x.score)

    table = Table(box=box.ROUNDED, title="TradeGuard Stats", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total validations", str(total))
    table.add_row("Pass rate", f"[green]{rate}%[/green]" if rate >= 50 else f"[red]{rate}%[/red]")
    table.add_row("Average score", f"{avg_score:.1f}")
    table.add_row("Best setup", f"{best.symbol} ({best.grade.value}, {best.score})")
    table.add_row("Worst setup", f"{worst.symbol} ({worst.grade.value}, {worst.score})")
    table.add_row("Saved plans", str(len(plans)))
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
