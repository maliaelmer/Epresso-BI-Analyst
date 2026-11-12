
"""Business logic for the E-Presso BI Analyst.
Keep Streamlit code out of this file.
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass, field

import pandas as pd

EXCEL_EXT = (".xlsx", ".xlsm", ".xls")
TEXT_EXT = (".csv", ".txt", ".tsv")


# ------------------------------------------------------------ loading

def excel_sheet_names(file_bytes: bytes) -> list[str]:
    return pd.ExcelFile(io.BytesIO(file_bytes)).sheet_names


def load_table(file_bytes: bytes, filename: str, sheet_name=0) -> pd.DataFrame:
    """Read a CSV, TXT, TSV or Excel file."""
    name = filename.lower()
    buffer = io.BytesIO(file_bytes)

    if name.endswith(EXCEL_EXT):
        return pd.read_excel(buffer, sheet_name=sheet_name)

    if name.endswith(TEXT_EXT):
        return pd.read_csv(buffer, sep=None, engine="python")

    raise ValueError(f"Unsupported file type: {filename}")


def profile_table(df: pd.DataFrame) -> dict:
    """Return row count, duplicates, missing values and data types."""
    missing = df.isna().sum()

    return {
        "rows": len(df),
        "columns": df.shape[1],
        "duplicate_rows": int(df.duplicated().sum()),
        "missing": pd.DataFrame({
            "column": missing.index,
            "missing": missing.values,
            "pct_missing": (
                missing.values / max(len(df), 1) * 100
            ).round(2),
        }),
        "dtypes": pd.DataFrame({
            "column": df.columns,
            "dtype": df.dtypes.astype(str).values,
        }),
    }


# ------------------------------------------------------- tool contract

@dataclass
class ToolResult:
    """Standard result returned by analytical assistant tools."""
    tool: str
    value: object
    definition: str
    scope: dict
    rows_used: int
    caveats: list = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _error(tool: str, message: str, scope: dict | None = None) -> ToolResult:
    return ToolResult(
        tool=tool,
        value=None,
        definition="",
        scope=scope or {},
        rows_used=0,
        caveats=[],
        error=message,
    )


def _apply_filters(df: pd.DataFrame, filters: dict | None):
    """Validate requested filters against the loaded data."""
    for col, wanted in (filters or {}).items():
        if col not in df.columns:
            return df, f"Unknown column: {col}"

        wanted_list = (
            list(wanted)
            if isinstance(wanted, (list, tuple, set))
            else [wanted]
        )

        valid = set(df[col].dropna().unique())
        bad = [value for value in wanted_list if value not in valid]

        if bad:
            examples = sorted(map(str, valid))[:20]
            return df, (
                f"{bad} not found in column {col}. "
                f"Valid values include: {examples}"
            )

        df = df[df[col].isin(wanted_list)]

    return df, None


# ------------------------------------------------------ analytical tools

def get_total(
    df: pd.DataFrame,
    value_col: str,
    filters: dict | None = None,
) -> ToolResult:
    """Calculate the sum of a numeric column."""
    name = "get_total"

    if value_col not in df.columns:
        return _error(name, f"Unknown column: {value_col}")

    subset, err = _apply_filters(df, filters)
    if err:
        return _error(name, err, {"filters": filters})

    values = pd.to_numeric(subset[value_col], errors="coerce")
    n_bad = int(values.isna().sum())

    caveats = ["Revenue is not profit."]

    if n_bad:
        caveats.append(
            f"{n_bad} row(s) had missing or non-numeric values "
            f"in {value_col} and were excluded."
        )

    return ToolResult(
        tool=name,
        value=float(values.sum()),
        definition=f"Sum of {value_col}",
        scope={"filters": filters or "none (all rows)"},
        rows_used=int(values.notna().sum()),
        caveats=caveats,
    )


def group_total(
    df: pd.DataFrame,
    value_col: str,
    group_col: str,
    filters: dict | None = None,
) -> ToolResult:
    """Calculate a sum grouped by another column."""
    name = "group_total"

    for col in (value_col, group_col):
        if col not in df.columns:
            return _error(name, f"Unknown column: {col}")

    subset, err = _apply_filters(df, filters)
    if err:
        return _error(name, err, {"filters": filters})

    work = subset.copy()
    work[value_col] = pd.to_numeric(
        work[value_col], errors="coerce"
    )

    n_bad = int(work[value_col].isna().sum())
    n_nogroup = int(work[group_col].isna().sum())

    grouped = (
        work.dropna(subset=[value_col, group_col])
        .groupby(group_col)[value_col]
        .sum()
    )

    caveats = ["Revenue is not profit."]

    if n_bad:
        caveats.append(
            f"{n_bad} row(s) with invalid {value_col} were excluded."
        )

    if n_nogroup:
        caveats.append(
            f"{n_nogroup} row(s) with missing {group_col} were excluded."
        )

    return ToolResult(
        tool=name,
        value={str(k): float(v) for k, v in grouped.items()},
        definition=f"Sum of {value_col} by {group_col}",
        scope={"filters": filters or "none (all rows)"},
        rows_used=int(len(work) - n_bad - n_nogroup),
        caveats=caveats,
    )
    
def revenue_growth_by_channel(
    df: pd.DataFrame,
) -> ToolResult:
    """Compare revenue growth across sales channels."""
    name = "revenue_growth_by_channel"

    required = ["Year", "StoreType", "Revenue"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        return _error(name, f"Missing required columns: {missing}")

    work = df[required].copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Revenue"] = pd.to_numeric(
        work["Revenue"], errors="coerce"
    )

    work = work.dropna(
        subset=["Year", "StoreType", "Revenue"]
    )

    years = sorted(work["Year"].unique())

    if len(years) < 2:
        return _error(
            name,
            "At least two different years are needed to calculate growth."
        )

    first_year = years[0]
    last_year = years[-1]

    grouped = work.groupby(
        ["StoreType", "Year"]
    )["Revenue"].sum().unstack(fill_value=0)

    results = {}
    caveats = []

    for channel in grouped.index:
        start = float(grouped.loc[channel, first_year])
        end = float(grouped.loc[channel, last_year])

        if start == 0:
            growth = None
            caveats.append(
                f"{channel}: growth cannot be calculated because "
                "starting revenue is zero."
            )
        else:
            growth = round((end - start) / start * 100, 2)

        results[str(channel)] = {
            "starting_revenue": start,
            "ending_revenue": end,
            "growth_percentage": growth,
        }

    return ToolResult(
        tool=name,
        value={
            "first_year": int(first_year),
            "last_year": int(last_year),
            "channels": results,
        },
        definition=(
            f"Revenue growth by sales channel from "
            f"{int(first_year)} to {int(last_year)}"
        ),
        scope={"years": [int(first_year), int(last_year)]},
        rows_used=len(work),
        caveats=caveats,
    )





def data_quality_report(df: pd.DataFrame) -> ToolResult:
    """Report row count, duplicate rows and missing values."""
    missing = {
        col: int(count)
        for col, count in df.isna().sum().items()
        if count > 0
    }

    caveats = []
    if missing:
        caveats.append(
            "Missing values may limit conclusions drawn from those columns."
        )

    return ToolResult(
        tool="data_quality_report",
        value={
            "rows": len(df),
            "duplicate_rows": int(df.duplicated().sum()),
            "columns_with_missing": missing,
        },
        definition="Counts of duplicate rows and missing values",
        scope={"filters": "none (full table)"},
        rows_used=len(df),
        caveats=caveats,
    )

def get_average_satisfaction(
    df: pd.DataFrame,
    filters: dict | None = None
) -> ToolResult:
    """Calculate average customer satisfaction overall or by region."""

    filters = filters or {}

    if df.empty or "Satisfaction" not in df.columns:
        return ToolResult(
            tool="get_average_satisfaction",
            value={},
            definition="Average customer satisfaction",
            scope={"filters": filters or "none (full survey table)"},
            rows_used=0,
            caveats=["No customer satisfaction data is available."],
        )

    satisfaction = df.dropna(subset=["Satisfaction"])

    if "Location" in filters:
        location = str(filters["Location"]).strip().casefold()
        satisfaction = satisfaction[
            satisfaction["Location"].astype(str).str.strip().str.casefold()
            == location
        ]

    if satisfaction.empty:
        return ToolResult(
            tool="get_average_satisfaction",
            value={
                "overall_average": None,
                "by_location": {},
                "location_filter": filters.get("Location"),
            },
            definition="Average customer satisfaction on a 0–5 scale",
            scope={"filters": filters},
            rows_used=0,
            caveats=["No customer satisfaction data is available for this region."],
        )

    overall_average = float(satisfaction["Satisfaction"].mean())

    by_location = {}
    if "Location" in satisfaction.columns:
        by_location = (
            satisfaction.groupby("Location")["Satisfaction"]
            .agg(["mean", "count"])
            .round(2)
            .to_dict("index")
        )

    return ToolResult(
        tool="get_average_satisfaction",
        value={
            "overall_average": round(overall_average, 2),
            "by_location": by_location,
            "location_filter": filters.get("Location"),
        },
        definition="Average customer satisfaction on a 0–5 scale",
        scope={"filters": filters or "none (full survey table)"},
        rows_used=len(satisfaction),
    )

# ------------------------------------------------------------ merge check

def check_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on,
    value_col: str,
    how: str = "left",
):
    """Check whether a merge changes row count or revenue."""
    before_rows = len(left)
    before_sum = float(
        pd.to_numeric(left[value_col], errors="coerce").sum()
    )

    merged = left.merge(right, on=on, how=how)

    after_rows = len(merged)
    after_sum = float(
        pd.to_numeric(merged[value_col], errors="coerce").sum()
    )

    changed = (
        after_rows != before_rows
        or abs(after_sum - before_sum) > 1e-9
    )

    report = {
        "rows_before": before_rows,
        "rows_after": after_rows,
        "sum_before": before_sum,
        "sum_after": after_sum,
        "changed": changed,
        "warning": (
            "The join changed the row count or total. "
            "Check the grain and keys."
            if changed else ""
        ),
    }

    return merged, report


# ------------------------------------------------------ E-Presso analysis

def prepare_sales_data(
    sales: pd.DataFrame,
    stores: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Join the Sales table to its three dimension tables safely."""

    required = {
        "Sales": (
            sales,
            [
                "Sales ID", "Date", "Store ID",
                "Category ID", "Product ID", "Revenue",
            ],
        ),
        "Stores": (
            stores,
            ["ID", "StoreType", "Market", "Location"],
        ),
        "Products": (
            products,
            ["Product ID", "Product"],
        ),
        "Categories": (
            categories,
            ["Category ID", "Category"],
        ),
    }

    for table_name, (df, columns) in required.items():
        missing = [col for col in columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"{table_name} is missing required columns: {missing}"
            )

    # Dimension keys must be unique and non-missing.
    for df, key, table_name in [
        (stores, "ID", "Stores"),
        (products, "Product ID", "Products"),
        (categories, "Category ID", "Categories"),
    ]:
        if df[key].isna().any():
            raise ValueError(f"{table_name} has missing {key} values.")
        if df[key].duplicated().any():
            raise ValueError(f"{table_name} has duplicate {key} values.")

    result = sales.copy()

    result["Date"] = pd.to_datetime(
        result["Date"], errors="coerce"
    )
    result["Revenue"] = pd.to_numeric(
        result["Revenue"], errors="coerce"
    )

    if result["Date"].isna().any():
        raise ValueError("Sales contains invalid dates.")

    if result["Revenue"].isna().any():
        raise ValueError("Sales contains missing or invalid revenue.")

    original_rows = len(result)
    original_revenue = float(result["Revenue"].sum())
    reports = {}

    # Stores
    store_lookup = stores.rename(columns={"ID": "Store ID"})
    unmatched = (
        set(result["Store ID"].dropna())
        - set(store_lookup["Store ID"].dropna())
    )
    if unmatched:
        raise ValueError(
            f"Unknown Store IDs in Sales: {sorted(unmatched)}"
        )

    result, reports["Stores"] = check_merge(
        result, store_lookup, "Store ID", "Revenue"
    )

    # Products
    unmatched = (
        set(result["Product ID"].dropna())
        - set(products["Product ID"].dropna())
    )
    if unmatched:
        raise ValueError(
            f"Unknown Product IDs in Sales: {sorted(unmatched)}"
        )

    result, reports["Products"] = check_merge(
        result, products, "Product ID", "Revenue"
    )

    # Categories
    unmatched = (
        set(result["Category ID"].dropna())
        - set(categories["Category ID"].dropna())
    )
    if unmatched:
        raise ValueError(
            f"Unknown Category IDs in Sales: {sorted(unmatched)}"
        )

    result, reports["Categories"] = check_merge(
        result, categories, "Category ID", "Revenue"
    )

    final_revenue = float(result["Revenue"].sum())

    if len(result) != original_rows:
        raise ValueError(
            "The joins changed the Sales row count."
        )

    if abs(final_revenue - original_revenue) > 0.01:
        raise ValueError(
            "The joins changed total revenue."
        )

    # Date fields used by the dashboard.
    result["Year"] = result["Date"].dt.year
    result["Month"] = result["Date"].dt.month
    result["Month Name"] = result["Date"].dt.strftime("%b")

    reports["Final check"] = {
        "rows_before": original_rows,
        "rows_after": len(result),
        "revenue_before": original_revenue,
        "revenue_after": final_revenue,
        "passed": True,
    }

    return result, reports
