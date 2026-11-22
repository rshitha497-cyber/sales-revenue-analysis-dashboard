import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Sales & Revenue Dashboard", page_icon="📊", layout="wide")

st.title("📊 Sales & Revenue Analysis Dashboard")
st.caption("Explore sales, revenue, profit, products and regional performance.")

# ---------- Data loading ----------
@st.cache_data
def load_sample_data():
    data = pd.read_csv("sample_sales.csv")
    data["Order_Date"] = pd.to_datetime(data["Order_Date"], errors="coerce")
    return data

def prepare_data(data):
    data = data.copy()
    required = ["Product", "Region", "Quantity", "Unit_Price"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    if "Order_Date" not in data.columns:
        raise ValueError("Your file must contain an Order_Date column.")

    data["Order_Date"] = pd.to_datetime(data["Order_Date"], errors="coerce", dayfirst=False)
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["Unit_Price"] = pd.to_numeric(data["Unit_Price"], errors="coerce")

    if "Unit_Cost" in data.columns:
        data["Unit_Cost"] = pd.to_numeric(data["Unit_Cost"], errors="coerce")
    else:
        data["Unit_Cost"] = 0

    if "Category" not in data.columns:
        data["Category"] = "Uncategorized"

    data = data.dropna(subset=["Order_Date", "Product", "Region", "Quantity", "Unit_Price"])
    data = data[data["Quantity"] >= 0]
    data["Sales"] = data["Quantity"] * data["Unit_Price"]
    data["Profit"] = data["Quantity"] * (data["Unit_Price"] - data["Unit_Cost"])
    return data

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
    st.info(
        "Required columns: Order_Date, Product, Region, Quantity, Unit_Price. "
        "Optional columns: Category, Unit_Cost."
    )

try:
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".csv"):
            raw = pd.read_csv(uploaded_file)
        else:
            raw = pd.read_excel(uploaded_file)
        sales_data = prepare_data(raw)
    else:
        sales_data = prepare_data(load_sample_data())

    if sales_data.empty:
        st.warning("No valid records found. Please check your uploaded file.")
        st.stop()

except Exception as error:
    st.error(f"Could not load the data: {error}")
    st.stop()

# ---------- Filters ----------
st.sidebar.header("Dashboard filters")
min_date = sales_data["Order_Date"].min().date()
max_date = sales_data["Order_Date"].max().date()
date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date),
                                   min_value=min_date, max_value=max_date)

products = sorted(sales_data["Product"].dropna().unique().tolist())
regions = sorted(sales_data["Region"].dropna().unique().tolist())
categories = sorted(sales_data["Category"].dropna().unique().tolist())

selected_products = st.sidebar.multiselect("Product", products, default=products)
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)

filtered = sales_data[
    sales_data["Product"].isin(selected_products)
    & sales_data["Region"].isin(selected_regions)
    & sales_data["Category"].isin(selected_categories)
].copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Order_Date"].dt.date.between(start_date, end_date)
    ]

if filtered.empty:
    st.warning("No records match the selected filters. Change the filters in the sidebar.")
    st.stop()

# ---------- KPI cards ----------
total_revenue = filtered["Sales"].sum()
total_profit = filtered["Profit"].sum()
total_units = filtered["Quantity"].sum()
total_orders = len(filtered)
average_order_value = total_revenue / total_orders if total_orders else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue", f"₹{total_revenue:,.0f}")
k2.metric("Total Profit", f"₹{total_profit:,.0f}")
k3.metric("Orders / Records", f"{total_orders:,}")
k4.metric("Units Sold", f"{total_units:,.0f}")
k5.metric("Average Revenue / Record", f"₹{average_order_value:,.0f}")

st.divider()

# ---------- Charts ----------
left, right = st.columns(2)

with left:
    monthly = (filtered.assign(Month=filtered["Order_Date"].dt.to_period("M").astype(str))
               .groupby("Month", as_index=False)["Sales"].sum())
    fig_month = px.line(monthly, x="Month", y="Sales", markers=True,
                        title="Monthly Revenue Trend",
                        labels={"Sales": "Revenue (₹)", "Month": "Month"})
    st.plotly_chart(fig_month, use_container_width=True)

with right:
    product_sales = (filtered.groupby("Product", as_index=False)["Sales"].sum()
                     .sort_values("Sales", ascending=False))
    fig_product = px.bar(product_sales, x="Product", y="Sales", color="Product",
                         title="Revenue by Product",
                         labels={"Sales": "Revenue (₹)"})
    st.plotly_chart(fig_product, use_container_width=True)

left2, right2 = st.columns(2)

with left2:
    region_sales = filtered.groupby("Region", as_index=False)["Sales"].sum()
    fig_region = px.pie(region_sales, names="Region", values="Sales",
                        title="Revenue Share by Region", hole=0.35)
    st.plotly_chart(fig_region, use_container_width=True)

with right2:
    category_sales = filtered.groupby("Category", as_index=False)["Sales"].sum()
    fig_category = px.bar(category_sales, x="Category", y="Sales", color="Category",
                          title="Revenue by Category",
                          labels={"Sales": "Revenue (₹)"})
    st.plotly_chart(fig_category, use_container_width=True)

# ---------- Top products and data table ----------
st.subheader("Top-performing products")
top_products = (filtered.groupby("Product", as_index=False)
                .agg(Units_Sold=("Quantity", "sum"),
                     Revenue=("Sales", "sum"),
                     Profit=("Profit", "sum"))
                .sort_values("Revenue", ascending=False))
st.dataframe(top_products, use_container_width=True, hide_index=True)

st.subheader("Filtered sales records")
display_data = filtered.sort_values("Order_Date", ascending=False)
st.dataframe(display_data, use_container_width=True, hide_index=True)

csv_data = display_data.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download filtered data as CSV", data=csv_data,
                   file_name="filtered_sales_data.csv", mime="text/csv")

st.caption("Note: The included sample dataset is for learning and demonstration. Replace it with verified business data for real analysis.")
