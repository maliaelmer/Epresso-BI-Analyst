
"""E-Presso BI Analyst: load and profile all five business tables."""
import io

import pandas as pd
import streamlit as st

import agent
import analytics

MAX_QUESTIONS = 15

st.set_page_config(page_title="E-Presso BI Analyst", layout="wide")
st.title("E-Presso BI Analyst")
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


with st.sidebar:
    st.header("E-Presso Data")
    uploaded_files = st.file_uploader(
        "Upload all five data files",
        type=["csv", "txt", "tsv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

if not uploaded_files:
    st.info("Upload the five E-Presso files in the sidebar to begin.")
    st.stop()

tables = {}
unknown_files = []
duplicate_tables = []

for uploaded in uploaded_files:
    table_type = identify_table(uploaded.name)

    if table_type is None:
        unknown_files.append(uploaded.name)
        continue

    if table_type in tables:
        duplicate_tables.append(TABLE_NAMES[table_type])
        continue

    try:
        tables[table_type] = cached_load(
            uploaded.getvalue(),
            uploaded.name,
            table_type,
        )
    except Exception as exc:
        st.error(f"Could not read {uploaded.name}: {exc}")
        st.stop()

if unknown_files:
    st.warning(
        "I could not identify these files: " + ", ".join(unknown_files)
    )

if duplicate_tables:
    st.warning(
        "You uploaded more than one file for: "
        + ", ".join(duplicate_tables)
    )

missing = [
    TABLE_NAMES[key]
    for key in TABLE_NAMES
    if key not in tables
]

if missing:
    st.warning(
        "Still missing: " + ", ".join(missing)
        + ". Please upload the missing files."
    )
    st.stop()

st.success("All five E-Presso tables have been loaded successfully.")

tab_data, tab_dash, tab_assistant = st.tabs(
    ["Data and profile", "Dashboard", "Assistant"]
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
            st.bar_chart(yearly)

            # Revenue by store type
            st.subheader("Revenue by store type")

            by_store = (
                filtered.groupby("StoreType")["Revenue"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(by_store)

            # Monthly revenue trend
            st.subheader("Monthly revenue trend")

            monthly_data = filtered.copy()
            monthly_data["Year-Month"] = (
                monthly_data["Date"].dt.to_period("M").astype(str)
            )

            monthly = (
                monthly_data.groupby("Year-Month")["Revenue"]
                .sum()
                .sort_index()
            )
            st.line_chart(monthly)

            # Revenue by category
            st.subheader("Revenue by category")

            by_category = (
                filtered.groupby("Category")["Revenue"]
                .sum()
                .sort_values(ascending=False)
            )
            st.bar_chart(by_category)

        # Show evidence that joins did not change revenue
        with st.expander("Data relationship and merge checks"):
            for table_name, report in merge_reports.items():
                st.write(f"**{table_name}**")
                st.json(report)

    except Exception as exc:
        st.error(f"Could not build the dashboard: {exc}")


with tab_assistant:
    st.header("Analytical Assistant")
    st.caption(
        "Rules-based starter. At this stage, questions are checked "
        "against the Sales table."
    )

    st.session_state.setdefault("n_questions", 0)
    st.session_state.setdefault("history", [])

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

            answer = agent.answer_question(
                question,
                tables["sales"],
                mode="rules",
            )

            st.session_state["history"].append({
                "question": question,
                "answer": answer,
            })

            st.rerun()
