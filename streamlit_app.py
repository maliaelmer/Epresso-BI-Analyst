
"""E-Presso BI Analyst: load and profile all five business tables."""
import io
from urllib.request import urlopen

import pandas as pd
import altair as alt
import streamlit as st

import agent
import analytics

MAX_QUESTIONS = 15

st.set_page_config(page_title="E-Presso BI Analyst", layout="wide")
st.markdown("""
<style>
    /* Main background and typography */
    .stApp {
        background-color: #F7F4EE;
        color: #30251F;
    }

    h1, h2, h3 {
        color: #38271F !important;
        font-family: Georgia, serif;
    }

    p, label, .stMarkdown {
        color: #51443B;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #30251F;
    }

    [data-testid="stSidebar"] * {
        color: #F7F4EE !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E7DCCB;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #806B5B !important;
    }

    [data-testid="stMetricValue"] {
        color: #38271F !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #8B5E3C;
        color: white;
        border: none;
        border-radius: 8px;
    }

    .stButton > button:hover {
        background-color: #68432D;
        color: white;
        border: none;
    }

    /* Tabs */
    button[data-baseweb="tab"] {
        color: #68432D;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #A66B3F;
        border-bottom-color: #A66B3F;
    }

    /* Data tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #E7DCCB;
        border-radius: 10px;
    }
    /* Filter selection tags */
[data-baseweb="tag"] {
    background-color: #8B5E3C !important;
    color: white !important;
    border-color: #8B5E3C !important;
}

[data-baseweb="tag"] * {
    color: white !important;
}
/* Sidebar upload area */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background-color: #49372D;
    border: 1px solid #806B5B;
    border-radius: 10px;
    padding: 10px;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
    background-color: #49372D;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background-color: #B98255;
    color: white;
    border: none;
}

/* Override Streamlit's default red filter tags */
.stMultiSelect [data-baseweb="tag"] {
    background-color: #8B5E3C !important;
    border: 1px solid #8B5E3C !important;
}

.stMultiSelect [data-baseweb="tag"] span {
    color: #FFFFFF !important;
}

</style>
""", unsafe_allow_html=True)
st.markdown("""
<div style="padding: 24px 0 18px 0;">
    <div style="font-size: 13px; letter-spacing: 4px;
                color: #A66B3F; font-weight: 700;">
        E-PRESSO  /  BUSINESS INTELLIGENCE
    </div>
    <h1 style="font-size: 42px; margin: 8px 0 4px 0;">
        Coffee. Data. Decisions.
    </h1>
    <p style="font-size: 16px; color: #806B5B;">
        Your intelligent workspace for understanding E-Presso's business.
    </p>
</div>
""", unsafe_allow_html=True)
st.caption(
    "Explore E-Presso sales, stores, products, categories, "
    "and customer survey results."
)

TABLE_NAMES = {
    "sales": "Sales",
    "stores": "Stores",
    "products": "Products",
    "categories": "Categories",
    "survey": "Survey Results",
}


def identify_table(filename):
    """Identify the business table from the uploaded filename."""
    name = filename.lower()

    if "survey" in name:
        return "survey"
    if "store" in name:
        return "stores"
    if "product" in name:
        return "products"
    if "categor" in name:
        return "categories"
    if "sales" in name:
        return "sales"

    return None


@st.cache_data(show_spinner=False)
def cached_load(file_bytes, filename, table_type):
    """Load a table. Cache keys include the uploaded file contents."""
    if table_type == "survey":
        # The actual column headings are on row 3 of this worksheet.
        return pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name="Survey Results",
            skiprows=2,
        )

    return analytics.load_table(file_bytes, filename)


DEFAULT_FILES = {
    "sales": "Sales_EPresso.xlsx",
    "stores": "Support_EX_B_Stores.csv",
    "products": "Products.xlsx",
    "categories": "Categories_Epresso.xlsx",
    "survey": "Support_EX_B_Survey.xlsx",
}


@st.cache_data(show_spinner=False)
def load_default_table(filename, table_type):
    url = (
        "https://raw.githubusercontent.com/"
        "maliaelmer/Epresso-BI-Analyst/main/data/"
        + filename
    )
    with urlopen(url) as response:
        file_bytes = response.read()

    return cached_load(file_bytes, filename, table_type)


with st.sidebar:
    st.header("E-Presso Data")
    st.caption(
        "The original data loads automatically. Upload a file only "
        "if you want to replace that table."
    )
    uploaded_files = st.file_uploader(
        "Optional: upload files to replace original data",
        type=["csv", "txt", "tsv", "xlsx", "xls"],
        accept_multiple_files=True,
    )


tables = {}

for table_type, filename in DEFAULT_FILES.items():
    try:
        tables[table_type] = load_default_table(filename, table_type)
    except Exception as exc:
        st.error(f"Could not load the default file {filename}: {exc}")
        st.stop()


unknown_files = []
duplicate_tables = []
uploaded_table_types = set()

for uploaded in uploaded_files or []:
    table_type = identify_table(uploaded.name)

    if table_type is None:
        unknown_files.append(uploaded.name)
        continue

    if table_type in uploaded_table_types:
        duplicate_tables.append(TABLE_NAMES[table_type])
        continue

    try:
        tables[table_type] = cached_load(
            uploaded.getvalue(),
            uploaded.name,
            table_type,
        )
        uploaded_table_types.add(table_type)
    except Exception as exc:
        st.error(f"Could not read {uploaded.name}: {exc}")
        st.stop()


if unknown_files:
    st.warning(
        "I could not identify these files: " + ", ".join(unknown_files)
    )

if duplicate_tables:
    st.warning(
        "You uploaded more than one replacement file for: "
        + ", ".join(duplicate_tables)
    )

st.success("All five E-Presso tables have been loaded successfully.")

tab_data, tab_dash, tab_survey, tab_assistant = st.tabs(
    ["Data and profile", "Dashboard", "Survey Analysis", "Assistant"]
)

with tab_data:
    st.header("Data overview")

    overview = []
    for key, title in TABLE_NAMES.items():
        df = tables[key]
        overview.append({
            "Table": title,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Duplicate rows": int(df.duplicated().sum()),
        })

    st.dataframe(
        pd.DataFrame(overview),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.header("Individual table profiles")

    for key, title in TABLE_NAMES.items():
        df = tables[key]
        profile = analytics.profile_table(df)

        with st.expander(f"{title} — {len(df):,} rows", expanded=(key == "sales")):
            st.subheader("Preview")
            st.dataframe(df.head(10), use_container_width=True)

            left, right = st.columns(2)

            with left:
                st.write("Missing values")
                st.dataframe(profile["missing"], use_container_width=True)

            with right:
                st.write("Data types")
                st.dataframe(profile["dtypes"], use_container_width=True)


with tab_dash:
    st.header("E-Presso Revenue Dashboard")

    try:
        sales_data, merge_reports = analytics.prepare_sales_data(
            tables["sales"],
            tables["stores"],
            tables["products"],
            tables["categories"],
        )

        # Interactive filters
        st.subheader("Filters")

        col1, col2, col3 = st.columns(3)

        years = sorted(sales_data["Year"].dropna().unique())
        categories = sorted(sales_data["Category"].dropna().unique())
        store_types = sorted(sales_data["StoreType"].dropna().unique())

        with col1:
            selected_years = st.multiselect(
                "Year",
                years,
                default=years,
            )

        with col2:
            selected_categories = st.multiselect(
                "Category",
                categories,
                default=categories,
            )

        with col3:
            selected_store_types = st.multiselect(
                "Store type",
                store_types,
                default=store_types,
            )

        filtered = sales_data[
            sales_data["Year"].isin(selected_years)
            & sales_data["Category"].isin(selected_categories)
            & sales_data["StoreType"].isin(selected_store_types)
        ].copy()

        # Key performance indicators
        st.subheader("Key performance indicators")

        total_revenue = filtered["Revenue"].sum()
        sales_records = len(filtered)
        average_revenue = (
            total_revenue / sales_records if sales_records else 0
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Total revenue",
            f"${total_revenue:,.0f}",
        )
        c2.metric(
            "Sales records",
            f"{sales_records:,}",
        )
        c3.metric(
            "Average revenue per record",
            f"${average_revenue:,.2f}",
        )

        if filtered.empty:
            st.warning("No sales records match the selected filters.")
        else:
            # Revenue by year
            st.subheader("Revenue by year")

            yearly = (
                filtered.groupby("Year")["Revenue"]
                .sum()
                .sort_index()
            )

            yearly_chart_data = yearly.rename_axis("Year").reset_index(name="Revenue")

            yearly_chart = alt.Chart(yearly_chart_data).mark_bar(
                cornerRadiusTopLeft=6,
                cornerRadiusTopRight=6
            ).encode(
                x=alt.X("Year:O", title="Year", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Revenue:Q", title="Revenue ($)", scale=alt.Scale(domainMin=0)),
                color=alt.Color(
                    "Year:O",
                    scale=alt.Scale(
                        range=["#789080"]
                    ),
                    legend=None
                ),
                tooltip=[
                    alt.Tooltip("Year:O", title="Year"),
                    alt.Tooltip("Revenue:Q", title="Revenue", format="$,.0f")
                ]
            ).properties(height=350)

            st.altair_chart(yearly_chart, use_container_width=True)
        
            # Revenue by store type
            st.subheader("Revenue by store type")

            by_store = (
                filtered.groupby("StoreType")["Revenue"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(by_store, color="#8B5E3C")

           
                        # Percentage of revenue by month
            st.subheader("Percentage of annual revenue by month")

            monthly_data = filtered.copy()
            monthly_data["Month"] = monthly_data["Date"].dt.month
            monthly_data["Month name"] = monthly_data["Date"].dt.month_name()

            monthly = (
                monthly_data.groupby(["Month", "Month name"])["Revenue"]
                .sum()
                .reset_index()
                .sort_values("Month")
            )

            total_revenue = monthly["Revenue"].sum()
            monthly["Revenue percentage"] = (
                monthly["Revenue"] / total_revenue * 100
            )

            month_order = [
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December"
            ]

            monthly["Month label"] = (
                monthly["Month"].astype(str).str.zfill(2)
                + " - "
                + monthly["Month name"]
            )

            monthly_chart = monthly.set_index("Month label")["Revenue percentage"]

            st.bar_chart(monthly_chart, color="#B98255")

            # Revenue by category
            st.subheader("Revenue by category")

            by_category = (
                filtered.groupby("Category")["Revenue"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(by_category, color="#8B5E3C")

        # Show evidence that joins did not change revenue
        with st.expander("Data relationship and merge checks"):
            for table_name, report in merge_reports.items():
                st.write(f"**{table_name}**")
                st.json(report)

    except Exception as exc:
        st.error(f"Could not build the dashboard: {exc}")

with tab_survey:
    st.header("E-Presso Survey Analysis")

    survey_data = tables["survey"].copy()

    sales_data, merge_reports = analytics.prepare_sales_data(
        tables["sales"],
        tables["stores"],
        tables["products"],
        tables["categories"],
    )

    revenue_by_store_year = (
        sales_data.groupby(["Store ID", "Year"], as_index=False)
        ["Revenue"].sum()
    )

    survey_data["Year"] = pd.to_numeric(
    survey_data["Year"].astype(str).str.replace("Y", "", regex=False),
    errors="coerce"
).astype("Int64")

    revenue_by_store_year["Year"] = pd.to_numeric(
        revenue_by_store_year["Year"], errors="coerce"
    ).astype("Int64")

    survey_data = survey_data.merge(
        tables["stores"],
        left_on="Store ID",
        right_on="ID",
        how="left"
    )

    survey_data = survey_data.merge(
        revenue_by_store_year,
        on=["Store ID", "Year"],
        how="left"
    )

    st.subheader("Customer Satisfaction and Revenue by Location")

    location_analysis = (
        survey_data.groupby("Location", as_index=False)
        .agg(
            Average_Satisfaction=("Satisfaction", "mean"),
            Revenue=("Revenue", "sum")
        )
        .dropna(subset=["Average_Satisfaction"])
    )

    if not location_analysis.empty:
        st.scatter_chart(
            location_analysis,
            x="Average_Satisfaction",
            y="Revenue",
            color="Location"
        )
    else:
        st.info("No customer satisfaction data is available.")

    st.subheader("Survey Results by Location")

    display_columns = [
        "Survey ID",
        "Year",
        "City",
        "Location",
        "Market",
        "StoreType",
        "Revenue",
    ]

    st.dataframe(
        survey_data[display_columns],
        use_container_width=True,
        hide_index=True
    )
with tab_assistant:
    st.subheader("Ask the E-Presso BI Analyst")
    st.caption("Ask questions about revenue, store types, categories, and data quality.")

    st.session_state.setdefault("n_questions", 0)
    st.session_state.setdefault("history", [])
    st.caption(f"Questions used: {st.session_state['n_questions']} / {MAX_QUESTIONS}")

    for item in st.session_state["history"]:
        with st.chat_message("user"):
            st.write(item["question"])

        with st.chat_message("assistant"):
            answer = item["answer"]
            st.markdown(f"**Scope:** {answer['scope']}")
            st.markdown(f"**Findings:** {answer['findings']}")

            if answer["interpretation"]:
                st.markdown(
                    f"**Interpretation:** {answer['interpretation']}"
                )

            if answer["next_steps"]:
                st.markdown(f"**Next steps:** {answer['next_steps']}")

            with st.expander("Tool-call log"):
                st.json(answer["tool_log"])

    question = st.chat_input("Ask a question about E-Presso sales")

    if question:
        if st.session_state["n_questions"] >= MAX_QUESTIONS:
            st.warning(
                "Question limit reached for this session. "
                "Reload the page to start over."
            )
        else:
            st.session_state["n_questions"] += 1

            assistant_sales, _ = analytics.prepare_sales_data(
                tables["sales"],
                tables["stores"],
                tables["products"],
                tables["categories"],
            )

            answer = agent.answer_question(
                question,
                assistant_sales,
                mode="rules",
            )

            st.session_state["history"].append({
                "question": question,
                "answer": answer,
            })

            st.rerun()
