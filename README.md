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
├── 6.2.ipynb                      # full pipeline: cleaning, EDA, features, model, risk scoring
│
├── sales_daily.csv                # raw data
├── sku_master.csv                 # raw data
├── calendar.csv                   # raw data
├── inventory_snapshots.csv        # raw data
│
├── sales_clean.csv                # cleaned data
├── sku_clean.csv
├── calendar_clean.csv
├── inventory_core_clean.csv       # inventory for the 50 matched SKUs
├── inventory_extra_clean.csv      # inventory for the 150 unmatched SKUs (not used)
├── master_daily_clean.csv         # merged daily table (36,550 rows)
├── master_features.csv            # modelling table with lag/rolling features (35,100 rows)
│
├── demand_forecast_model.pkl      # trained XGBoost model
├── forecast_results.csv           # actual vs predicted on the hold-out period
├── sku_accuracy.csv               # per-SKU forecast accuracy
├── risk_scoring_output.csv        # risk level and rupee impact per SKU
│
├── Dashboard/
│   ├── app.py                     # Streamlit dashboard (7 pages)
│   ├── assets/
│   │   └── background.jpg
│   └── data/                      # CSVs the dashboard reads
│
├── requirements.txt
└── README.md
```

## Data

Four source datasets, covering 50 core SKUs over 2 years (1 Jan 2024 – 31 Dec 2025):

* `sales_daily.csv` — 36,550 daily records: units sold, revenue, price, promotion flag
* `sku_master.csv` — 50 records: category, subcategory, launch date, cost/selling price
* `calendar.csv` — 731 records: date parts, season, holiday flag, promotion events
* `inventory_snapshots.csv` — 4,800 records, monthly: stock on hand, on-order, lead time, reorder point

**Data quality note:** `inventory_snapshots.csv` contains 200 unique SKUs, but only 50 have matching sales and product records. The other 150 (SKU051–SKU200) have no sales history anywhere else in the dataset and were excluded from forecasting and risk scoring, kept aside only for reference.

## Data Pipeline

All steps are in the notebook `6.2.ipynb`:

1. Load all four raw datasets
2. Clean and validate (type conversions, duplicate/null checks per file)
3. Split inventory into core (50 SKUs, matched) and extra (150 SKUs, unmatched)
4. Merge sales + calendar + SKU master into one daily table
5. Exploratory data analysis (trend, category, promotion, weekend, season, holiday, top/bottom SKUs)
6. Engineer lag features (1/7/14-day) and rolling averages (7/30-day)
7. One-hot encode categorical columns (category, season, quarter, day of week)
8. Train the forecasting model on a chronological split
9. Score every core SKU's stockout/overstock risk
10. Quantify rupee impact per SKU

## Demand Forecasting

An **XGBoost regressor** (300 trees, max depth 6, learning rate 0.05) is used for daily SKU-level demand forecasting.

The model uses 33 input features:

* Lag features (1-day, 7-day, 14-day prior sales)
* Rolling averages (7-day, 30-day)
* Calendar features (year, month, week, quarter, day of week, season, weekend flag, holiday flag)
* Promotion flag
* Product attributes (category, price, cost price, selling price, margin, days since launch)

The model is evaluated against a **seasonal-naive baseline** (the same SKU's sales 7 days earlier) using WAPE as the primary metric, with MAPE reported as a secondary figure.

### Backtest Results

Evaluated on a chronological hold-out — the final 60 days of the dataset (2 Nov – 31 Dec 2025, 3,000 SKU-day rows), never seen during training. Training uses 30 Jan 2024 – 1 Nov 2025 (32,100 rows).

| Metric | XGBoost Model | Seasonal-Naive Baseline |
| ------ | -------------: | -----------------------: |
| WAPE   |        **20.22%** |                   31.46% |
| MAE    |          2.50 |                     3.89 |
| MAPE   |         30.01% |                        — |

The model reduced WAPE by approximately **36% relative to the seasonal-naive baseline**.

MAPE (30.01%) is noticeably worse than WAPE (20.22%) because a handful of very low-volume SKUs inflate percentage error disproportionately — a 1–2 unit miss on a SKU that sells ~3 units/day looks like a 50%+ error even though it is a small absolute miss. The five best-predicted SKUs (SKU037, SKU027, SKU042, SKU018, SKU043) have MAPE of 14.8–17.5%; the five worst (SKU039, SKU015, SKU003, SKU011, SKU028) sell only ~2.5–5 units per day.

**Note on validation methodology:** this evaluation uses a single chronological train/hold-out split, not full rolling-origin cross-validation. Rolling-origin backtesting (multiple expanding-window folds) would give a more robust accuracy estimate and is a natural next step.

## Inventory Risk Analysis

Risk is scored per core SKU using:

* Current stock, on-order quantity
* Average daily demand (trailing 30 days of actual sales)
* Safety stock, reorder point, lead time (from the latest monthly snapshot, 1 Dec 2025)
* Days of stock remaining at current demand rate

### Risk Categories

Rules are applied in this order:

| Risk Level | Count | Logic |
| ---------- | ----: | ----- |
| High Risk | 8 | Stock will run out before a reorder could arrive (days of stock left ≤ lead time) |
| Medium Risk | 8 | Stock has already dropped below the reorder point |
| Overstock Risk | 8 | More than 60 days of stock on hand at current demand |
| Healthy | 26 | None of the above |

### Recommended Actions

* **Reorder now** — High Risk SKUs
* **Markdown / clear** — Overstock Risk SKUs
* **Monitor** — Medium Risk SKUs
* **No action needed** — Healthy SKUs

## Business Impact

Based on the latest inventory snapshot (December 2025) across the 50 core SKUs:

* **Sales at risk (stockouts):** approximately **₹42.1 lakh** — for each High Risk SKU: (lead time − days of stock left) × average daily demand × selling price
* **Capital locked (overstock):** approximately **₹50.8 lakh** — for each Overstock Risk SKU: units above 60 days of demand × cost price
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
pip install -r requirements.txt
cd Dashboard
streamlit run app.py
```

Live version: https://foresight-ai-powered-demand-inventory-intelligence-platform-g2.streamlit.app

## Reproducibility

1. Install the requirements: `pip install -r requirements.txt`
2. Open `6.2.ipynb` in Jupyter and run the cells from top to bottom. It reads the four raw CSV files in the repository root and regenerates the cleaned data, features, model, forecast results and risk scoring output.
3. The CSVs used by the dashboard are already provided in `Dashboard/data/`.

## Limitations

* Inventory snapshots are monthly, while sales data is daily — risk scoring uses only the most recent snapshot, since older snapshots would understate current risk.
* Forecast accuracy is weaker for low-volume SKUs, where percentage error naturally inflates.
* Validation is a single chronological hold-out, not full rolling-origin cross-validation — a more robust backtest is a planned next step.
* 150 SKUs in the inventory data have no matching sales history and are excluded from forecasting; worth investigating whether they represent a legacy product line.
* A dedicated scoring API (separate from the dashboard) has not yet been built.
* The model should be retrained periodically as new sales data becomes available.

## Technologies

* Python, pandas, numpy
* XGBoost, scikit-learn, joblib
* Matplotlib (EDA), Plotly (dashboard)
* Streamlit

## Project Status

* Data pipeline: Complete
* Data quality and EDA: Complete
* Demand forecasting (beats baseline): Complete
* Inventory risk scoring with rupee impact: Complete
* Dashboard: Complete, deployed live
* Executive readout deck: Complete
* Rolling-origin cross-validation: Not yet implemented (single hold-out used)
* Scoring API: Not yet implemented

## Project Context

Developed as part of the **Zidio Development Data Science & Analytics internship**, Project FORESIGHT engagement, for the NorthBay Living business case.
