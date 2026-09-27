# Project FORESIGHT — Demand Forecasting & Inventory Risk Analytics

A data-driven demand forecasting and inventory risk management project developed as part of the Zidio Development Data Science & Analytics internship.

**Live dashboard:** https://foresight-ai-powered-demand-inventory-intelligence-platform-g2.streamlit.app
**Repository:** https://github.com/akashvai8931-stack/FORESIGHT-AI-Powered-Demand-Inventory-Intelligence-Platform

## Project Overview

Project FORESIGHT is built for NorthBay Living, a direct-to-consumer home and lifestyle brand that currently plans inventory on spreadsheets and gut feel.

The project combines historical daily sales, SKU master data, calendar/promotion data, and monthly inventory snapshots to help an operations team:

* Forecast daily demand at SKU level
* Identify SKUs at risk of stockout
* Identify SKUs that are overstocked
* Quantify the financial impact of both, in rupees
* Prioritize which SKUs need action first
* Explore all of the above through an interactive dashboard

## Business Objectives

1. What is the expected demand for each SKU?
2. Which SKUs are at risk of stocking out?
3. Which SKUs have excess inventory tying up capital?
4. What action should the operations team take, and what is it worth in rupees?

## Project Structure

```text
FORESIGHT-AI-Powered-Demand-Inventory-Intelligence-Platform/
│
├── data/
│   └── raw/
│       ├── sales_daily.csv
│       ├── sku_master.csv
│       ├── calendar.csv
│       └── inventory_snapshots.csv
│
├── src/
│   ├── feature_engineering.py     # cleans + merges raw data, builds lag/rolling/calendar features
│   ├── forecast_model.py          # trains XGBoost model, computes WAPE vs seasonal-naive baseline
│   └── risk_scoring.py            # classifies stockout/overstock risk, quantifies rupee impact
│
├── models/
│   └── demand_forecast_model.pkl
│
├── Dashboard/
│   ├── app.py                     # Streamlit dashboard (7 pages)
│   ├── assets/
│   │   └── background.jpg
│   └── data/                      # processed CSVs the dashboard reads
│
├── requirements.txt
└── README.md
```

## Data

Four source datasets, covering 50 core SKUs over 2 years (Jan 2024 – Dec 2025):

* `sales_daily.csv` — 36,550 daily records: units sold, revenue, price, promotion flag
* `sku_master.csv` — 50 records: category, subcategory, launch date, cost/selling price
* `calendar.csv` — 731 records: date parts, season, holiday flag, promotion events
* `inventory_snapshots.csv` — 4,800 records, monthly: stock on hand, on-order, lead time, reorder point

**Data quality note:** `inventory_snapshots.csv` contains 200 unique SKUs, but only 50 have matching sales and product records. The other 150 (SKU051–SKU200) have no sales history anywhere else in the dataset and were excluded from forecasting and risk scoring, kept aside only for reference.

## Data Pipeline

1. Load all four raw datasets
2. Clean and validate (type conversions, duplicate/null checks per file)
3. Split inventory into core (50 SKUs, matched) and extra (150 SKUs, unmatched)
4. Merge sales + calendar + SKU master into one daily table
5. Engineer lag features (1/7/14-day) and rolling averages (7/30-day)
6. One-hot encode categorical columns (category, season, quarter, day of week)
7. Train the forecasting model on a chronological split
8. Build a seasonal-naive baseline for comparison
9. Score every core SKU's stockout/overstock risk
10. Quantify rupee impact per SKU

Run the pipeline with:

```bash
cd src
python feature_engineering.py
python forecast_model.py
python risk_scoring.py
```

## Demand Forecasting

An **XGBoost regressor** (300 trees, max depth 6, learning rate 0.05) is used for daily SKU-level demand forecasting.

Features include:

* Lag features (1-day, 7-day, 14-day prior sales)
* Rolling averages (7-day, 30-day)
* Calendar features (month, week, quarter, day of week, season, holiday flag)
* Promotion flag
* Product attributes (category, price, cost, margin, days since launch)

The model is evaluated against a **seasonal-naive baseline** (same SKU's sales 7 days prior) using WAPE as the primary metric, with MAPE reported as a secondary figure.

### Backtest Results

Evaluated on a chronological hold-out — the final 60 days of the 2-year dataset, never seen during training:

| Metric | XGBoost Model | Seasonal-Naive Baseline |
| ------ | -------------: | -----------------------: |
| WAPE   |        **20.16%** |                   31.46% |
| MAE    |          2.49 |                     3.89 |
| MAPE   |         29.96% |                        — |

The model improved WAPE by approximately **36% relative to the seasonal-naive baseline**.

MAPE (29.96%) is noticeably worse than WAPE (20.16%) because a handful of very low-volume SKUs inflate percentage error disproportionately — a 1–2 unit miss on a SKU that sells ~3 units/day looks like a 50%+ error even though it's a small absolute miss. On high-revenue SKUs specifically, MAPE is 15–17%.

**Note on validation methodology:** this evaluation uses a single chronological train/hold-out split, not full rolling-origin cross-validation. Rolling-origin backtesting (multiple expanding-window folds) would give a more robust accuracy estimate and is a natural next step to strengthen this result further.

## Inventory Risk Analysis

Risk is scored per core SKU using:

* Current stock, on-order quantity
* Average daily demand (trailing 30 days of actual sales)
* Safety stock, reorder point, lead time (from the latest monthly snapshot)
* Days of stock remaining at current demand rate

### Risk Categories

| Risk Level | Count | Logic |
| ---------- | ----: | ----- |
| Healthy | 26 | Stock is above reorder point and within a reasonable supply window |
| Overstock Risk | 8 | More than 60 days of stock on hand at current demand |
| Medium Risk | 8 | Stock has already dropped below the reorder point |
| High Risk | 8 | Stock will run out before a reorder could arrive (days left ≤ lead time) |

### Recommended Actions

* **Reorder now** — High Risk SKUs
* **Markdown / clear** — Overstock Risk SKUs
* **Monitor** — Medium Risk SKUs
* **No action needed** — Healthy SKUs

## Business Impact

Based on the latest inventory snapshot (December 2025) across the 50 core SKUs:

* **Sales at risk (stockouts):** approximately **₹42.1 lakh** — potential lost revenue if the 8 high-risk SKUs are not reordered before running out
* **Capital locked (overstock):** approximately **₹50.8 lakh** — value of excess stock sitting beyond a healthy ~60-day supply across the 8 overstocked SKUs
* **Combined value at stake:** approximately **₹92.9 lakh**

These are model-derived planning indicators based on the dataset's pricing and inventory assumptions, intended to help prioritize action — not exact accounting figures.

## Dashboard

The Streamlit dashboard has 7 pages:

* **Home** — headline metrics, monthly sales trend, risk overview
* **Sales Analytics** — category revenue, promotion/weekend/seasonality effects, top SKUs
* **Demand Forecast** — per-SKU actual vs. predicted chart, forecast accuracy
* **Inventory Dashboard** — stock levels, days-of-stock-left, full inventory table
* **Risk Dashboard** — rupee-value risk breakdown, high-risk and overstock SKU tables
* **Product Details** — per-SKU drill-down with sales history and inventory position
* **Executive Summary** — headline numbers, key findings, and recommended actions, written for a non-technical stakeholder

Run locally with:

```bash
cd Dashboard
streamlit run app.py
```

Live version: https://foresight-ai-powered-demand-inventory-intelligence-platform-g2.streamlit.app

## Reproducibility

```bash
pip install -r requirements.txt
cd src
python feature_engineering.py
python forecast_model.py
python risk_scoring.py
```

Then copy the generated CSVs from `data/processed/` into `Dashboard/data/`, and run the dashboard as above.

## Limitations

* Inventory snapshots are monthly, while sales data is daily — risk scoring uses only the most recent snapshot, since older snapshots would understate current risk.
* Forecast accuracy is weaker for low-volume SKUs, where percentage error naturally inflates.
* Validation is a single chronological hold-out, not full rolling-origin cross-validation — a more robust backtest is a planned next step.
* 150 SKUs in the inventory data have no matching sales history and are excluded from forecasting; worth investigating whether they represent a legacy product line.
* A dedicated scoring API (separate from the dashboard) has not yet been built.
* The model should be retrained periodically as new sales data becomes available.

## Technologies

* Python, pandas, numpy
* XGBoost, scikit-learn
* Streamlit, Plotly

## Project Status

* Data pipeline: Complete
* Data quality and EDA: Complete
* Demand forecasting (beats baseline): Complete
* Inventory risk scoring with rupee impact: Complete
* Dashboard: Complete, deployed live
* Executive readout deck: Complete
* Rolling-origin cross-validation: Not yet implemented (single hold-out used)
* Scoring API: Not yet implemented
* Demo video: In progress

## Project Context

Developed as part of the **Zidio Development Data Science & Analytics internship**, Project FORESIGHT engagement, for the NorthBay Living business case.
