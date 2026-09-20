import streamlit as st
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv
from openai import OpenAI

st.set_page_config(
    page_title="AI Business Intelligence Copilot",
    page_icon="📊",
    layout="wide"
)

load_dotenv()

client = OpenAI()

conn = sqlite3.connect(
    "data/superstore.db",
    check_same_thread=False
)
schema = """
Table: sales

Columns:
row_id INTEGER
order_id TEXT
order_date TIMESTAMP
ship_date TIMESTAMP
ship_mode TEXT
customer_id TEXT
customer_name TEXT
segment TEXT
country_region TEXT
city TEXT
state_province TEXT
postal_code TEXT
region TEXT
product_id TEXT
category TEXT
sub_category TEXT
product_name TEXT
sales REAL
quantity INTEGER
discount REAL
profit REAL
"""
system_prompt = f"""
You are a Business Intelligence SQL assistant.

Your job is to convert business questions into SQLite SQL queries.

Use only this database schema:

{schema}

Rules:
1. Use only the sales table.
2. Generate valid SQLite SQL.
3. Do not invent columns.
4. Return only the SQL query.
5. Use SUM(sales) for total sales.
6. Use SUM(profit) for total profit.
7. Use GROUP BY when comparing regions, categories, customers, products, or segments.
8. When calculating profit margin, use (SUM(profit) / SUM(sales)) * 100 and name the result profit_margin_percent.

"""
def generate_sql(question):
    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=system_prompt,
        input=question
    )

    return response.output_text

def execute_sql(sql):
    sql_clean = sql.strip().lower()

    if not sql_clean.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    return pd.read_sql_query(sql, conn)

def explain_result(question, result):
    result_text = result.to_string(index=False)

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=f"""
You are a Business Intelligence analyst.

Business question:
{question}

Query result:
{result_text}

Explain the result in 2-3 clear business sentences.
Use only the numbers shown in the query result.
Format currency values with a dollar sign and commas.
Round business metrics to a sensible number of decimal places.
If the query returns only the top or bottom result, do not mention that other rows are missing or unavailable.
When explaining a profit margin, always include dollar signs literally. For example, write "$7.92 in profit for every $100 in sales." Never write "7.92 in profit for every 100 in sales.
Do not invent any additional facts.
"""
    )

    return response.output_text

def get_executive_summary_data(data, growth_data, year_filter):
    total_sales = data["sales"].sum()
    total_profit = data["profit"].sum()
    profit_margin = (total_profit / total_sales) * 100
    total_orders = data["order_id"].nunique()
    total_customers = data["customer_id"].nunique()

    top_product = (
        data.groupby("product_name")["sales"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )

    top_product_name = top_product.index[0]
    top_product_sales = top_product.iloc[0]

    subcategory_profit = (
        data.groupby("sub_category")["profit"]
        .sum()
        .sort_values()
    )

    weakest_subcategory_name = subcategory_profit.index[0]
    weakest_subcategory_profit = subcategory_profit.iloc[0]

    yearly_data = growth_data.copy()
    yearly_data["order_date"] = pd.to_datetime(yearly_data["order_date"])
    yearly_data["year"] = yearly_data["order_date"].dt.year

    yearly_sales = (
        yearly_data.groupby("year")["sales"]
        .sum()
        .sort_index()
    )

    yearly_profit = (
        yearly_data.groupby("year")["profit"]
        .sum()
        .sort_index()
    )

    if year_filter != "All":
        latest_year = int(year_filter)
        previous_year = latest_year - 1
    else:
        latest_year = yearly_sales.index[-1]
        previous_year = yearly_sales.index[-2]

    if previous_year in yearly_sales.index:
        sales_growth_percent = (
        (yearly_sales.loc[latest_year] - yearly_sales.loc[previous_year])
        / yearly_sales.loc[previous_year]
    ) * 100

        profit_growth_percent = (
        (yearly_profit.loc[latest_year] - yearly_profit.loc[previous_year])
        / yearly_profit.loc[previous_year]
    ) * 100
    else:
     sales_growth_percent = None
     profit_growth_percent = None
    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "profit_margin": profit_margin,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "top_product_name": top_product_name,
        "top_product_sales": top_product_sales,
        "weakest_subcategory_name": weakest_subcategory_name,
        "weakest_subcategory_profit": weakest_subcategory_profit,
        "latest_year": latest_year,
        "previous_year": previous_year,
        "sales_growth_percent": sales_growth_percent,
        "profit_growth_percent": profit_growth_percent
    }


def generate_executive_summary(summary_data, region_filter, category_filter):
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=f"""
You are a senior Business Intelligence analyst writing an executive summary.

Current dashboard filters:
Region: {region_filter}
Category: {category_filter}

Business KPIs:
Total Sales: {summary_data["total_sales"]}
Total Profit: {summary_data["total_profit"]}
Profit Margin: {summary_data["profit_margin"]}
Total Orders: {summary_data["total_orders"]}
Total Customers: {summary_data["total_customers"]}
Top Product by Sales: {summary_data["top_product_name"]}
Top Product Sales: {summary_data["top_product_sales"]}
Latest Year: {summary_data["latest_year"]}
Weakest Subcategory by Profit: {summary_data["weakest_subcategory_name"]}
Weakest Subcategory Profit: {summary_data["weakest_subcategory_profit"]}
Previous Year: {summary_data["previous_year"]}
Sales Growth Percent: {summary_data["sales_growth_percent"]}
Profit Growth Percent: {summary_data["profit_growth_percent"]}

Write a concise professional executive summary in 3-4 sentences.

Requirements:
- Mention the most important KPIs.
- Format sales and profit as currency.
- Format profit margin as a percentage.
- Use clear business language.
- Do not invent facts that are not provided.
- Mention the top product by sales.
- Mention the latest-year sales growth and whether sales increased or decreased.
- End with one practical management recommendation based only on the provided KPIs, trends, top product, and weakest subcategory.
- Do not invent causes that are not supported by the data.
- If Sales Growth Percent or Profit Growth Percent is None, state that prior-year growth comparison is unavailable and do not invent a growth rate.
"""
    )

    return response.output_text

st.title("AI Business Intelligence Copilot")

st.caption(
    "Interactive sales analytics dashboard with AI-powered SQL insights and executive summaries."
)

df = pd.read_csv("data/superstore_cleaned.csv")

df["order_date"] = pd.to_datetime(df["order_date"])
df["year"] = df["order_date"].dt.year

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    region_filter = st.selectbox(
        "Select Region",
        ["All"] + sorted(df["region"].unique().tolist())
    )

with filter_col2:
    category_filter = st.selectbox(
        "Select Category",
        ["All"] + sorted(df["category"].unique().tolist())
    )

with filter_col3:
    year_filter = st.selectbox(
        "Select Year",
        ["All"] + sorted(df["year"].unique().tolist())
    )

filtered_df = df.copy()

if region_filter != "All":
    filtered_df = filtered_df[filtered_df["region"] == region_filter]

if category_filter != "All":
    filtered_df = filtered_df[filtered_df["category"] == category_filter]

if year_filter != "All":
    filtered_df = filtered_df[filtered_df["year"] == year_filter]
growth_df = df.copy()

if region_filter != "All":
    growth_df = growth_df[growth_df["region"] == region_filter]

if category_filter != "All":
    growth_df = growth_df[growth_df["category"] == category_filter]
with st.expander("View Sample Data"):
    st.dataframe(filtered_df.head())

total_sales = filtered_df["sales"].sum()
total_profit = filtered_df["profit"].sum()
profit_margin = (total_profit / total_sales) * 100
total_orders = filtered_df["order_id"].nunique()
total_customers = filtered_df["customer_id"].nunique()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Sales", f"${total_sales:,.0f}")
col2.metric("Total Profit", f"${total_profit:,.0f}")
col3.metric("Profit Margin", f"{profit_margin:.2f}%")
col4.metric("Total Orders", f"{total_orders:,}")
col5.metric("Total Customers", f"{total_customers:,}")
import plotly.express as px

region_sales = (
    filtered_df.groupby("region")["sales"]
    .sum()
    .reset_index()
)

fig = px.bar(
    region_sales,
    x="region",
    y="sales",
    title="Sales by Region"
)

region_profit = (
    filtered_df.groupby("region")["profit"]
    .sum()
    .reset_index()
)

fig_profit = px.bar(
    region_profit,
    x="region",
    y="profit",
    title="Profit by Region"
)
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.plotly_chart(fig, width="stretch")

with chart_col2:
    st.plotly_chart(fig_profit, width="stretch")

category_sales = (
    filtered_df.groupby("category")["sales"]
    .sum()
    .reset_index()
)

fig_category = px.bar(
    category_sales,
    x="category",
    y="sales",
    title="Sales by Category"
)

category_profit = (
    filtered_df.groupby("category")["profit"]
    .sum()
    .reset_index()
)

fig_category_profit = px.bar(
    category_profit,
    x="category",
    y="profit",
    title="Profit by Category"
)

category_col1, category_col2 = st.columns(2)

with category_col1:
    st.plotly_chart(fig_category, width="stretch")

with category_col2:
    st.plotly_chart(fig_category_profit, width="stretch")

    subcategory_profit = (
    filtered_df.groupby("sub_category")["profit"]
    .sum()
    .sort_values()
    .reset_index()
)

fig_subcategory_profit = px.bar(
    subcategory_profit,
    x="profit",
    y="sub_category",
    orientation="h",
    title="Profit by Sub-Category"
)

st.plotly_chart(fig_subcategory_profit, width="stretch")
segment_summary = (
    filtered_df.groupby("segment")[["sales", "profit"]]
    .sum()
    .reset_index()
)

fig_segment_sales = px.bar(
    segment_summary,
    x="segment",
    y="sales",
    title="Sales by Customer Segment"
)

fig_segment_profit = px.bar(
    segment_summary,
    x="segment",
    y="profit",
    title="Profit by Customer Segment"
)

segment_col1, segment_col2 = st.columns(2)

with segment_col1:
    st.plotly_chart(fig_segment_sales, width="stretch")

with segment_col2:
    st.plotly_chart(fig_segment_profit, width="stretch")

top_products = (
    filtered_df.groupby("product_name")["sales"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

fig_top_products = px.bar(
    top_products,
    x="sales",
    y="product_name",
    orientation="h",
    title="Top 10 Products by Sales"
)

fig_top_products.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

top_customers = (
    filtered_df.groupby("customer_name")["sales"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

fig_top_customers = px.bar(
    top_customers,
    x="sales",
    y="customer_name",
    orientation="h",
    title="Top 10 Customers by Sales"
)

fig_top_customers.update_layout(
    yaxis={"categoryorder": "total ascending"}
)
top_col1, top_col2 = st.columns(2)

with top_col1:
    st.plotly_chart(fig_top_products, width="stretch")

with top_col2:
    st.plotly_chart(fig_top_customers, width="stretch")


filtered_df["order_date"] = pd.to_datetime(filtered_df["order_date"])

monthly_sales = (
    filtered_df.groupby(filtered_df["order_date"].dt.to_period("M"))["sales"]
    .sum()
    .reset_index()
)

monthly_sales["order_date"] = monthly_sales["order_date"].astype(str)

monthly_profit = (
    filtered_df.groupby(filtered_df["order_date"].dt.to_period("M"))["profit"]
    .sum()
    .reset_index()
)

monthly_profit["order_date"] = monthly_profit["order_date"].astype(str)

fig_monthly_sales = px.line(
    monthly_sales,
    x="order_date",
    y="sales",
    title="Monthly Sales Trend"
)

fig_monthly_profit = px.line(
    monthly_profit,
    x="order_date",
    y="profit",
    title="Monthly Profit Trend"
)

trend_col1, trend_col2 = st.columns(2)

with trend_col1:
    st.plotly_chart(fig_monthly_sales, width="stretch")

with trend_col2:
    st.plotly_chart(fig_monthly_profit, width="stretch")

st.subheader("Ask the AI Business Intelligence Copilot")

user_question = st.text_input(
    "Ask a business question about the data"
)

ask_button = st.button("Ask Copilot")

if ask_button:
    if user_question.strip():
        with st.spinner("Analyzing your question..."):
            try:
                filter_context = f"""
Current dashboard filters:
Region: {region_filter}
Category: {category_filter}
Year: {year_filter}

Apply these filters to the SQL query when they are not set to All.
For Year, filter using strftime('%Y', order_date).
"""

                sql = generate_sql(user_question + "\n\n" + filter_context)
                result = execute_sql(sql)
                explanation = explain_result(user_question, result)

                st.subheader("Copilot Answer")

                safe_explanation = explanation.replace("$", r"\$")
                st.markdown(safe_explanation)

                st.subheader("Query Result")
                st.dataframe(result)

                with st.expander("View Generated SQL"):
                    st.code(sql, language="sql")

            except Exception as e:
                st.error(f"Could not answer the question: {e}")
    else:
        st.warning("Please enter a business question.")
        st.divider()

st.subheader("Executive Business Summary")

summary_button = st.button("Generate Executive Summary")

if summary_button:
    with st.spinner("Generating executive summary..."):
        try:
            summary_data = get_executive_summary_data(
            filtered_df,
            growth_df,
            year_filter
        )
            executive_summary = generate_executive_summary(
                summary_data,
                region_filter,
                category_filter
            )

            safe_summary = executive_summary.replace("$", r"\$")

            st.markdown(safe_summary)

        except Exception as e:
            st.error(f"Could not generate executive summary: {e}")

