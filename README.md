# Growth Funnel & Support-Deflection Metrics Dashboard

A multi-view Streamlit dashboard that tells a **build-measure-iterate** growth story
for an AI customer-support SaaS — acquisition funnel, cohort retention, and AI
support-deflection economics in one place.

Built as a business-operations / growth-analytics portfolio piece. It demonstrates a
metrics mindset: define the funnel, measure each stage, find the leakiest step, and
quantify the operating leverage of AI support deflection.

> **All data in this project is synthetic.** It is generated from a fixed random seed
> by [`data_gen.py`](data_gen.py) so the dashboard is fully reproducible. No real
> company, customer, or proprietary data is used anywhere.

## Views

1. **Growth Overview** — headline KPI tiles (monthly signups, activation rate,
   visitor→paid conversion, MRR) plus the 12-month MRR trend.
2. **Funnel** — Visitor → Signup → Activated → Paid, with stage-by-stage conversion
   rates and automatic highlighting of the leakiest step.
3. **Cohort Retention** — monthly signup cohorts as a retention heatmap, surfacing the
   Month-0→Month-1 cliff and improvement in newer cohorts.
4. **AI Support Deflection** — auto-resolution (deflection) rate, CSAT, tickets
   deflected, and cumulative cost saved vs. a human-handled baseline.

Each view ends with a short **"So what → recommendation"** callout, so the dashboard
reads as an argument, not just a chart dump.

## Design

Charts follow Cole Nussbaumer Knaflic's *Storytelling with Data*:

- **Takeaway titles** — every chart title states the insight, not the metric name.
- **Decluttered** — gridlines and chart junk removed; axes muted.
- **Direct labels** — values annotated on the chart instead of hunting a legend.
- **Restrained color** — one teal accent carries the signal; grey is context.

## Run it

```bash
pip install -r requirements.txt

# optional — writes the synthetic CSVs to ./data and prints a sanity summary
python data_gen.py

streamlit run app.py
```

The app generates its data in-memory on launch (via `data_gen.generate_all()`), so
running `data_gen.py` first is optional — it is useful for inspecting the raw CSVs.

## Files

| File               | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `app.py`           | Multi-view Streamlit dashboard                                 |
| `data_gen.py`      | Synthetic funnel / cohort / support / revenue data generator   |
| `requirements.txt` | Python dependencies                                            |
| `README.md`        | This file                                                      |
| `.gitignore`       | Ignores `__pycache__`, virtualenvs, and generated `data/`      |

## Data model (synthetic)

- **Funnel** — 12 monthly cohorts; visitors grow ~6%/mo, stage conversion rates drift
  up gently to model product improvement, with noise.
- **Cohorts** — retention decays toward a loyal-core floor; later cohorts retain
  slightly better.
- **Support** — ticket volume scales with the paying base; AI deflection climbs from
  ~52% to ~74% as the agent is tuned; CSAT stays high; cost saved uses a $6.00
  human-handled per-ticket baseline.
- **Revenue** — MRR proxy from the paid base at ~$48 ARPA with ~98.5% net monthly
  retention.

---

**Author:** Leo Chan — [github.com/GoldenCrate](https://github.com/GoldenCrate)
