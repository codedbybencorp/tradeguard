# 🛡️ TradeGuard

> **The pre-trade validation system that stops bad trades before they cost you money.**

Most traders don't blow up from one bad trade — they bleed out from dozens of mediocre ones taken on impulse. TradeGuard forces a pause. It validates every setup against your risk rules, scores confluence objectively, and gives you a clear **PASS** or **FAIL** before you click buy.

---

## Why Traders Need This

- **Emotional trading kills accounts.** TradeGuard enforces a mechanical checklist.
- **Position sizing errors are silent killers.** It calculates exact share size based on your stop and account risk.
- **Correlated exposure stacks risk.** It warns when you're over-exposed to related symbols.
- **Daily loss limits prevent spirals.** It tracks your risk budget and rejects trades that would push you over.
- **Only A+ setups get capital.** By default, only Grade A or A+ setups pass. No more B- trades "just to be in the market."

---

## Features

| Feature | What It Does |
|---------|-------------|
| **Setup Scoring** | Scores every trade across 4 dimensions (trend, S/R, confluence, timing). 0-100 scale. |
| **Risk Validation** | Enforces max risk per trade, daily budget, correlated exposure caps, and minimum R:R. |
| **Auto Position Sizing** | Calculates exact position size based on stop distance and your dollar risk limit. |
| **Grade Gating** | Rejects setups below your minimum grade (default: A). |
| **Daily Budget Tracker** | Tracks cumulative risk used today with a visual progress bar. |
| **Beautiful CLI** | Rich terminal UI with colored tables, progress bars, and interactive prompts. |
| **Web Dashboard** | FastAPI dashboard for quick validation without the terminal. |
| **Persistent History** | JSON storage for all validations and saved plans. Review stats anytime. |

---

## Quick Start

```bash
# Install
pip install -e .

# Set up your risk profile
tradeguard profile --reset

# Validate a setup interactively
tradeguard validate

# Validate and save a plan
tradeguard plan

# Check daily risk budget
tradeguard budget

# View stats
tradeguard stats

# Launch web dashboard
tradeguard-web  # or: python -m uvicorn tradeguard.web:app --reload
```

## Docker Deployment

```bash
# Build & run web dashboard
docker compose up -d web

# Dashboard at http://localhost:8000
# Health check at http://localhost:8000/health

# Run CLI inside container
docker compose run --rm cli validate
docker compose run --rm cli stats

# Run tests inside container
docker compose run --rm cli test

# View logs
docker compose logs -f web

# Stop everything
docker compose down
```

**One-liner deploy (any server with Docker):**
```bash
git clone <repo> tradeguard && cd tradeguard
docker compose up -d web
```

---

## The Scoring System

Every setup is scored 0-100 across four equal components:

| Component | Max | What to Score |
|-----------|-----|---------------|
| **Trend** | 25 | Alignment with HTF trend (daily/weekly) |
| **S/R** | 25 | Quality of the key level being tested |
| **Confluence** | 25 | Number of independent signals agreeing |
| **Timing** | 25 | Session quality, trigger precision, orderflow |

**Grades:**
- **A+ (90+)** — Exceptional. High conviction.
- **A (80-89)** — Solid. Good risk/reward and confluence.
- **B (70-79)** — Marginal. Below TradeGuard default threshold.
- **C (60-69)** — Poor. Likely to fail validation.
- **F (<60)** — No trade. Rejected.

---

## Risk Profile Settings

```
Account size:           $10,000
Risk per trade:         1%  ($100)
Daily risk budget:      3%  ($300)
Max correlated exposure: 2%  ($200)
Minimum grade:          A
Minimum R:R:            1.5
```

---

## Web Dashboard

Launch the dashboard and validate setups from your browser:

```bash
uvicorn tradeguard.web:app --reload --port 8000
```

Then open `http://localhost:8000`.

---

## Marketing Copy

**Taglines:**
- *"Don't trade your P&L. Trade your plan."*
- *"Every blown account starts with a skipped checklist."*
- *"A+ setups only. Everything else is noise."*
- *"Risk management isn't a feeling. It's a system."*

**For social:**
> Tired of revenge trading? TradeGuard forces you to validate every setup against your risk rules BEFORE you enter. It calculates position size, checks daily limits, and only lets A+ setups through. Your account will thank you.

---

## Tech Stack

- **Python 3.10+**
- **Pydantic v2** — type-safe models
- **Rich** — beautiful terminal UI
- **Typer** — CLI framework
- **FastAPI + Jinja2** — web dashboard
- **Decimal** — exact financial math (no float drift)

---

## License

MIT — built for traders who want to survive.

---

**Ready to stop gambling and start trading?** `pip install tradeguard` and validate your next setup.
