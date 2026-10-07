"""
data_gen.py — Synthetic data generator for the Growth Funnel & Support-Deflection dashboard.

ALL DATA PRODUCED HERE IS SYNTHETIC. It is generated from a fixed random seed so the
dashboard is fully reproducible. No real company, customer, or Decagon data is used.

The generator models a plausible B2B SaaS growth story over a 12-month window:
  - A marketing/acquisition funnel: Visitor -> Signup -> Activated -> Paid
  - Monthly signup cohorts with retention decay
  - An AI support operation (ticket volume, auto-resolution/deflection, CSAT, cost)

Run directly to write CSVs into ./data and print a quick sanity summary:
    python data_gen.py
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 12 month window ending at a fixed month so output is deterministic.
MONTHS = pd.period_range(end="2025-09", periods=12, freq="M")


def _rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


def generate_funnel() -> pd.DataFrame:
    """Monthly acquisition funnel with a gentle growth trend + noise."""
    rng = _rng()
    n = len(MONTHS)

    # Visitors grow ~6% / month off a base, with multiplicative noise.
    base_visitors = 18000
    growth = np.cumprod(np.r_[1.0, rng.normal(1.06, 0.03, n - 1)])
    visitors = (base_visitors * growth * rng.normal(1.0, 0.04, n)).round().astype(int)

    # Stage conversion rates drift up slightly over time (product gets better),
    # with small month-to-month noise. Rates kept in realistic SaaS ranges.
    signup_rate = np.clip(np.linspace(0.085, 0.11, n) + rng.normal(0, 0.004, n), 0.05, 0.2)
    activation_rate = np.clip(np.linspace(0.46, 0.58, n) + rng.normal(0, 0.02, n), 0.3, 0.75)
    paid_rate = np.clip(np.linspace(0.20, 0.27, n) + rng.normal(0, 0.012, n), 0.1, 0.4)

    signups = (visitors * signup_rate).round().astype(int)
    activated = (signups * activation_rate).round().astype(int)
    paid = (activated * paid_rate).round().astype(int)

    df = pd.DataFrame(
        {
            "month": MONTHS.astype(str),
            "visitors": visitors,
            "signups": signups,
            "activated": activated,
            "paid": paid,
        }
    )
    return df


def generate_cohorts(funnel: pd.DataFrame) -> pd.DataFrame:
    """Monthly signup cohorts with retention by months-since-signup.

    Returns a long-format frame: cohort_month, period_index, retention (0-1), active_users.
    Retention follows a decay curve; later cohorts retain slightly better (product improves).
    """
    rng = _rng()
    rows = []
    n = len(MONTHS)

    for i, cohort in enumerate(MONTHS):
        cohort_size = int(funnel.loc[i, "signups"])
        # Max observable periods: later cohorts have fewer trailing months.
        max_period = n - 1 - i

        # Base decay: strong month-0 (100%), drop, then flatten.
        # Later cohorts (higher i) get a small retention lift.
        lift = 0.02 * i
        for p in range(0, max_period + 1):
            if p == 0:
                ret = 1.0
            else:
                # Smooth decay toward a floor, plus cohort lift and small noise.
                floor = 0.28 + 0.015 * i
                ret = floor + (0.72 - lift * 0.3) * np.exp(-0.45 * p)
                ret = float(np.clip(ret + rng.normal(0, 0.012), 0.05, 1.0))
            rows.append(
                {
                    "cohort_month": str(cohort),
                    "period_index": p,
                    "retention": round(ret, 4),
                    "active_users": int(round(cohort_size * ret)),
                }
            )
    return pd.DataFrame(rows)


def generate_support(funnel: pd.DataFrame) -> pd.DataFrame:
    """Monthly AI support operation metrics.

    Ticket volume scales with the active paying base. Auto-resolution (deflection)
    rate improves over the year as the AI agent is tuned. CSAT stays high and stable.
    Cost-saved is modeled vs. a human-handled baseline cost per ticket.
    """
    rng = _rng()
    n = len(MONTHS)

    # Support tickets scale with cumulative paid customers (support load grows).
    cumulative_paid = funnel["paid"].cumsum().to_numpy()
    tickets = (cumulative_paid * rng.normal(0.9, 0.05, n) + 1200).round().astype(int)

    # AI auto-resolution (deflection) rate climbs from ~52% to ~74% as the agent is tuned.
    deflection_rate = np.clip(np.linspace(0.52, 0.74, n) + rng.normal(0, 0.015, n), 0.4, 0.85)
    deflected = (tickets * deflection_rate).round().astype(int)
    escalated = tickets - deflected

    # CSAT (1-5) for AI-handled interactions, stable and high with small noise.
    csat = np.clip(np.linspace(4.25, 4.5, n) + rng.normal(0, 0.05, n), 3.5, 5.0).round(2)

    # Median first-response time (seconds). AI responds fast; improves slightly.
    first_response_sec = np.clip(np.linspace(14, 7, n) + rng.normal(0, 1.0, n), 3, 30).round(1)

    # Cost model: a human-handled ticket costs ~$6.00; each deflected ticket saves that.
    cost_per_ticket_human = 6.00
    cost_saved = (deflected * cost_per_ticket_human).round(2)

    df = pd.DataFrame(
        {
            "month": MONTHS.astype(str),
            "tickets": tickets,
            "deflected": deflected,
            "escalated": escalated,
            "deflection_rate": deflection_rate.round(4),
            "csat": csat,
            "first_response_sec": first_response_sec,
            "cost_saved_usd": cost_saved,
        }
    )
    return df


def generate_revenue(funnel: pd.DataFrame) -> pd.DataFrame:
    """Monthly revenue proxy (MRR) from the paid base.

    New paid customers each month add MRR at an average ARPA; we apply monthly
    net retention (expansion minus churn) to the prior base. This gives a smooth,
    growing MRR series consistent with the funnel.
    """
    rng = _rng()
    arpa = 48.0  # average revenue per paid account / month (USD)
    net_monthly_retention = 0.985  # 98.5% of prior MRR carries over (slight churn)
    initial_mrr = 220_000.0  # existing book of business at the start of the window

    mrr = []
    running = initial_mrr
    for i, _ in enumerate(MONTHS):
        new_paid = int(funnel.loc[i, "paid"])
        added = new_paid * arpa * rng.normal(1.0, 0.03)
        running = running * net_monthly_retention + added
        mrr.append(round(running, 2))

    return pd.DataFrame({"month": MONTHS.astype(str), "mrr_usd": mrr})


def generate_all() -> dict[str, pd.DataFrame]:
    funnel = generate_funnel()
    cohorts = generate_cohorts(funnel)
    support = generate_support(funnel)
    revenue = generate_revenue(funnel)
    return {
        "funnel": funnel,
        "cohorts": cohorts,
        "support": support,
        "revenue": revenue,
    }


def write_csvs(out_dir: str = DATA_DIR) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    data = generate_all()
    paths = {}
    for name, df in data.items():
        path = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        paths[name] = path
    return paths


if __name__ == "__main__":
    data = generate_all()
    paths = write_csvs()

    print("Synthetic data generated (SEED = %d). Files written:" % SEED)
    for name, path in paths.items():
        print(f"  - {name:8s} -> {path}  ({len(data[name])} rows)")

    f = data["funnel"]
    s = data["support"]
    r = data["revenue"]
    print("\nSanity summary:")
    print(f"  Visitors (latest month):   {f['visitors'].iloc[-1]:,}")
    print(f"  Signups  (latest month):   {f['signups'].iloc[-1]:,}")
    print(f"  Paid     (latest month):   {f['paid'].iloc[-1]:,}")
    v2p = f["paid"].iloc[-1] / f["visitors"].iloc[-1]
    print(f"  Visitor->Paid conversion:  {v2p:.2%}")
    print(f"  Deflection rate (latest):  {s['deflection_rate'].iloc[-1]:.1%}")
    print(f"  CSAT (latest):             {s['csat'].iloc[-1]}")
    print(f"  Cost saved (12mo total):   ${s['cost_saved_usd'].sum():,.0f}")
    print(f"  MRR (latest month):        ${r['mrr_usd'].iloc[-1]:,.0f}")
