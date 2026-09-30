import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import base64

st.set_page_config(
    page_title="Project FORESIGHT",
    page_icon="📦",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# OPTIONAL: if the baseline WAPE calculated below does NOT match the value in
# your notebook (31.46), type the notebook value here (e.g. 31.46).
# Leave as None to use the value calculated from the data.
# ---------------------------------------------------------------------------
BASELINE_WAPE_OVERRIDE = None


def set_background(image_path):
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(10, 20, 50, 0.85);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background(os.path.join(BASE_DIR, "assets", "background.jpg"))
import plotly.io as pio

pio.templates["foresight_dark"] = pio.templates["plotly_dark"]
pio.templates["foresight_dark"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(20,30,60,0.4)",
    font=dict(color="#E8EEF7"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
)
pio.templates.default = "foresight_dark"

@st.cache_data
def load_data():
    master = pd.read_csv(os.path.join(BASE_DIR, "data", "master_daily_clean.csv"), parse_dates=["Date"])
    risk = pd.read_csv(os.path.join(BASE_DIR, "data", "risk_scoring_output.csv"), parse_dates=["Snapshot_Date"])
    forecast_results = pd.read_csv(os.path.join(BASE_DIR, "data", "forecast_results.csv"), parse_dates=["Date"])
    return master, risk, forecast_results


def wape(actual, predicted):
    """Weighted Absolute Percentage Error, in %."""
    return float(np.abs(actual - predicted).sum() / actual.sum() * 100)


@st.cache_data
def compute_performance(fr, master):
    """Model WAPE vs seasonal-naive baseline WAPE across all SKUs.

    - Model WAPE uses the Actual / Predicted columns of forecast_results.csv.
    - Baseline: if forecast_results.csv already has a baseline column it is used;
      otherwise a weekly seasonal-naive forecast (same weekday last week) is
      built from the sales history.
    """
    model_wape = wape(fr["Actual"], fr["Predicted"])

    baseline_col = next(
        (c for c in fr.columns
         if c.lower() in ("baseline", "baseline_pred", "baseline_predicted",
                          "seasonal_naive", "naive_pred", "naive")),
        None,
    )

    if baseline_col is not None:
        baseline_wape = wape(fr["Actual"], fr[baseline_col])
        baseline_source = f"column '{baseline_col}' in forecast_results.csv"
    else:
        m = master[["SKU", "Date", "Units_Sold"]].sort_values(["SKU", "Date"]).copy()
        m["Baseline"] = m.groupby("SKU")["Units_Sold"].shift(7)
        merged = fr.merge(m[["SKU", "Date", "Baseline"]], on=["SKU", "Date"], how="left")
        merged = merged.dropna(subset=["Baseline"])
        baseline_wape = wape(merged["Actual"], merged["Baseline"])
        baseline_source = "calculated: same weekday last week"

    if BASELINE_WAPE_OVERRIDE is not None:
        baseline_wape = float(BASELINE_WAPE_OVERRIDE)
        baseline_source = "value from modelling notebook"

    improvement = (baseline_wape - model_wape) / baseline_wape * 100
    return {
        "model_wape": model_wape,
        "baseline_wape": baseline_wape,
        "improvement": improvement,
        "baseline_source": baseline_source,
    }


master_df, risk_df, forecast_results = load_data()

st.sidebar.title("📦 Project FORESIGHT")
page = st.sidebar.radio(
    "Navigate",
    ["Home", "Sales Analytics", "Demand Forecast", "Inventory Dashboard",
     "Risk Dashboard", "Product Details", "Executive Summary"]
)

if page == "Home":
    st.title("📦 Project FORESIGHT")
    st.markdown("### AI-Powered Demand Forecasting & Inventory Intelligence")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    total_skus = master_df['SKU'].nunique()
    total_revenue = master_df['Revenue'].sum()
    high_risk_count = (risk_df['Risk_Level'] == 'High Risk - Stockout Likely').sum()
    avg_daily_units = master_df['Units_Sold'].mean()

    col1.metric("Total SKUs", total_skus)
    col2.metric("Total Revenue", f"₹{total_revenue/1e7:.1f} Cr")
    col3.metric("High Risk SKUs", high_risk_count, delta=f"{high_risk_count} need action", delta_color="inverse")
    col4.metric("Avg Daily Units/SKU", f"{avg_daily_units:.1f}")

    st.markdown("---")

    st.subheader("Monthly Sales Trend")
    monthly = master_df.groupby(master_df['Date'].dt.to_period('M'))['Units_Sold'].sum().reset_index()
    monthly['Date'] = monthly['Date'].astype(str)
    fig = px.line(monthly, x='Date', y='Units_Sold', markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Inventory Risk Overview")
    risk_counts = risk_df['Risk_Level'].value_counts().reset_index()
    risk_counts.columns = ['Risk_Level', 'Count']
    fig2 = px.bar(risk_counts, x='Risk_Level', y='Count', color='Risk_Level')
    st.plotly_chart(fig2, use_container_width=True)

elif page == "Sales Analytics":
    st.title("📈 Sales Analytics")
    st.markdown("---")

    st.info(
        "**Data scope:** 4 datasets (daily sales, product master, calendar, inventory snapshots), "
        "50 core SKUs, Jan 2024 – Dec 2025. The inventory file listed 200 SKUs, but only 50 matched "
        "the sales and product records; the other 150 were split out and excluded from forecasting."
    )

    st.subheader("Revenue by Category")
    cat_perf = master_df.groupby('Category')['Revenue'].sum().sort_values(ascending=False).reset_index()
    fig1 = px.bar(cat_perf, x='Category', y='Revenue', color='Category')
    st.plotly_chart(fig1, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Promotion Impact")
        promo = master_df.groupby('Promotion')['Units_Sold'].mean().reset_index()
        promo['Promotion'] = promo['Promotion'].map({0: 'No Promotion', 1: 'Promotion'})
        fig2 = px.bar(promo, x='Promotion', y='Units_Sold', color='Promotion')
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Weekend vs Weekday")
        weekend = master_df.groupby('is_weekend')['Units_Sold'].mean().reset_index()
        weekend['is_weekend'] = weekend['is_weekend'].map({0: 'Weekday', 1: 'Weekend'})
        fig3 = px.bar(weekend, x='is_weekend', y='Units_Sold', color='is_weekend')
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Top 10 SKUs by Revenue")
    top_skus = master_df.groupby(['SKU', 'Product_Name'])['Revenue'].sum().sort_values(ascending=False).head(10).reset_index()
    st.dataframe(top_skus, use_container_width=True)

elif page == "Demand Forecast":
    st.title("🔮 Demand Forecast")
    st.markdown("---")

    sku_list = sorted(master_df['SKU'].unique())
    selected_sku = st.selectbox("Select a SKU to view forecast", sku_list)

    sku_forecast = forecast_results[forecast_results['SKU'] == selected_sku].sort_values('Date')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sku_forecast['Date'], y=sku_forecast['Actual'], name='Actual', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=sku_forecast['Date'], y=sku_forecast['Predicted'], name='Predicted', mode='lines+markers'))
    fig.update_layout(title=f"Actual vs Predicted — {selected_sku}", xaxis_title="Date", yaxis_title="Units Sold")
    st.plotly_chart(fig, use_container_width=True)

    sku_mape = sku_forecast['APE'].mean()
    st.metric("Selected SKU — MAPE (lower is better)", f"{sku_mape:.1f}%")

    # ------------------------- NEW: model vs baseline -------------------------
    st.markdown("---")
    st.subheader("Model Performance vs Baseline (all SKUs)")

    perf = compute_performance(forecast_results, master_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Model WAPE (XGBoost)", f"{perf['model_wape']:.2f}%")
    c2.metric("Seasonal-Naive Baseline WAPE", f"{perf['baseline_wape']:.2f}%")
    c3.metric("Relative Improvement", f"{perf['improvement']:.0f}%")

    perf_df = pd.DataFrame({
        "Model": ["Seasonal-Naive Baseline", "XGBoost Model"],
        "WAPE (%)": [perf["baseline_wape"], perf["model_wape"]],
    })
    fig_perf = px.bar(perf_df, x="Model", y="WAPE (%)", color="Model", text_auto=".2f")
    fig_perf.update_layout(showlegend=False)
    st.plotly_chart(fig_perf, use_container_width=True)

    st.caption(
        "WAPE (Weighted Absolute Percentage Error) = total absolute error ÷ total actual sales, so it weights "
        "errors by volume. The per-SKU MAPE above treats every day equally, so low-volume days inflate it. "
        "Lower is better for both. "
        f"Baseline source: {perf['baseline_source']}."
    )

    with st.expander("Model details"):
        st.markdown("""
        - **Algorithm:** XGBoost (300 trees, depth 6, learning rate 0.05)
        - **Features:** lag features (1, 7, 14 days) and rolling averages (7, 30 days); promotion and
          weekend effects are included
        - **Validation:** chronological train/test split (not random), so the model never sees the future
        - **Benchmark:** seasonal-naive baseline, as required by the project brief
        """)

elif page == "Inventory Dashboard":
    st.title("📋 Inventory Dashboard")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total SKUs Tracked", len(risk_df))
    col2.metric("Total Inventory Value", f"₹{risk_df['Inventory_Value'].sum()/1e7:.2f} Cr")
    col3.metric("Avg Lead Time", f"{risk_df['Lead_Time_Days'].mean():.1f} days")
    col4.metric("Below Reorder Point", int((risk_df['Stock_vs_Reorder'] < 0).sum()))

    st.markdown("---")
    st.subheader("Days of Stock Left by SKU")
    stock_view = risk_df[['SKU', 'Days_of_Stock_Left', 'Risk_Level']].sort_values('Days_of_Stock_Left')
    fig = px.bar(stock_view, x='SKU', y='Days_of_Stock_Left', color='Risk_Level')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full Inventory Table")
    st.dataframe(
        risk_df[['SKU', 'Current_Stock', 'On_Order', 'Reorder_Point', 'Safety_Stock',
                 'Lead_Time_Days', 'Avg_Daily_Demand', 'Days_of_Stock_Left', 'Risk_Level']],
        use_container_width=True
    )

elif page == "Risk Dashboard":
    st.title("⚠️ Risk Dashboard")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Sales at Risk (Stockouts)", f"₹{risk_df['Sales_At_Risk_INR'].sum()/1e5:.1f} L")
    col2.metric("Capital Locked (Overstock)", f"₹{risk_df['Capital_Locked_INR'].sum()/1e5:.1f} L")
    col3.metric("SKUs Needing Action", int((risk_df['Risk_Level'] != 'Healthy').sum()))

    st.markdown("---")
    st.subheader("Risk Level Distribution")
    risk_counts = risk_df['Risk_Level'].value_counts().reset_index()
    risk_counts.columns = ['Risk_Level', 'Count']
    fig = px.pie(risk_counts, names='Risk_Level', values='Count', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("High Risk SKUs — Stockout Likely")
    high_risk = risk_df[risk_df['Risk_Level'] == 'High Risk - Stockout Likely'].sort_values(
        'Sales_At_Risk_INR', ascending=False)
    st.dataframe(
        high_risk[['SKU', 'Current_Stock', 'Days_of_Stock_Left', 'Lead_Time_Days', 'Sales_At_Risk_INR']],
        use_container_width=True
    )

    st.subheader("Overstock SKUs — Markdown / Clear Candidates")
    overstock = risk_df[risk_df['Risk_Level'] == 'Overstock Risk'].sort_values(
        'Capital_Locked_INR', ascending=False)
    st.dataframe(
        overstock[['SKU', 'Current_Stock', 'Days_of_Stock_Left', 'Capital_Locked_INR']],
        use_container_width=True
    )

elif page == "Product Details":
    st.title("🔍 Product Details")
    st.markdown("---")

    sku_list = sorted(master_df['SKU'].unique())
    selected_sku = st.selectbox("Select a SKU", sku_list)

    sku_data = master_df[master_df['SKU'] == selected_sku]
    sku_risk = risk_df[risk_df['SKU'] == selected_sku]

    info = sku_data.iloc[0]
    st.subheader(f"{info['Product_Name']} ({selected_sku})")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Category", info['Category'])
    col2.metric("Total Units Sold", int(sku_data['Units_Sold'].sum()))
    col3.metric("Total Revenue", f"₹{sku_data['Revenue'].sum()/1e5:.1f} L")
    if not sku_risk.empty:
        col4.metric("Risk Level", sku_risk.iloc[0]['Risk_Level'])

    st.markdown("---")
    st.subheader("Daily Sales History")
    fig = px.line(sku_data.sort_values('Date'), x='Date', y='Units_Sold')
    st.plotly_chart(fig, use_container_width=True)

    if not sku_risk.empty:
        st.subheader("Current Inventory Position")
        r = sku_risk.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Stock", int(r['Current_Stock']))
        col2.metric("Reorder Point", int(r['Reorder_Point']))
        col3.metric("Days of Stock Left", f"{r['Days_of_Stock_Left']:.1f}")

elif page == "Executive Summary":
    st.title("📊 Executive Summary")
    st.caption("Prepared for: Head of Operations & Finance — NorthBay Living")
    st.markdown("---")

    st.markdown("### Headline Numbers")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue (2yr)", f"₹{master_df['Revenue'].sum()/1e7:.1f} Cr")
    col2.metric("Sales at Risk", f"₹{risk_df['Sales_At_Risk_INR'].sum()/1e5:.1f} L")
    col3.metric("Capital Locked", f"₹{risk_df['Capital_Locked_INR'].sum()/1e5:.1f} L")
    col4.metric("High Risk SKUs", int((risk_df['Risk_Level'] == 'High Risk - Stockout Likely').sum()))

    st.markdown("---")
    st.markdown("### Key Findings")
    st.markdown(f"""
    - **{int((risk_df['Risk_Level'] == 'High Risk - Stockout Likely').sum())} SKUs** are at immediate
      stockout risk, representing **₹{risk_df['Sales_At_Risk_INR'].sum()/1e5:.1f} lakh** in sales that
      could be lost if not reordered promptly.
    - **{int((risk_df['Risk_Level'] == 'Overstock Risk').sum())} SKUs** are overstocked, tying up
      **₹{risk_df['Capital_Locked_INR'].sum()/1e5:.1f} lakh** in working capital that could be freed
      through markdowns or promotions.
    - Sales show strong, repeatable **yearly seasonality** — March is the consistent peak month,
      October the consistent trough, in both years of data.
    - **Promotions lift sales by ~38%** and **weekends outsell weekdays by ~25%** — both effects are
      incorporated into the forecasting model.
    - A long tail exists in the product catalog: the top 5 SKUs generate dramatically more revenue
      than the bottom 5, suggesting inventory priority should concentrate on top performers.
    """)

    st.markdown("---")
    st.markdown("### Recommended Actions")
    st.markdown("""
    1. **Reorder now** — the high-risk SKUs listed in the Risk Dashboard, prioritized by sales-at-risk value.
    2. **Markdown / clear** — the overstocked SKUs to free up locked capital.
    3. **Monitor** — SKUs already below reorder point before they escalate to high risk.
    4. **Re-run this pipeline monthly** as new sales and inventory data comes in, to keep forecasts current.
    """)

    st.markdown("---")
    st.caption(
        "Limitations: Forecast accuracy is weaker for low-volume SKUs, since percentage error naturally "
        "inflates when actual sales are small. Risk scoring is based on the most recent monthly inventory "
        "snapshot; a live daily feed would improve precision further."
    )