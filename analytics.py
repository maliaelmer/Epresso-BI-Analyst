
# ------------------------------------------------------ E-Presso analysis


def prepare_sales_data(
    sales: pd.DataFrame,
    stores: pd.DataFrame,
    products: pd.DataFrame,
    categories: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Connect Sales with Stores, Products and Categories.
    Check that joins do not duplicate or lose sales records or revenue.
    """

    required = {
        "sales": (sales, [
            "Sales ID", "Date", "Store ID", "Category ID",
            "Product ID", "Revenue"
        ]),
        "stores": (stores, [
            "ID", "StoreType", "Market", "Location"
        ]),
        "products": (products, ["Product ID", "Product"]),
        "categories": (categories, ["Category ID", "Category"]),
    }

    for table_name, (df, columns) in required.items():
        missing = [col for col in columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"{table_name} is missing required columns: {missing}"
            )

    # Check that dimension-table keys are unique.
    for df, key, table_name in [
        (stores, "ID", "Stores"),
        (products, "Product ID", "Products"),
        (categories, "Category ID", "Categories"),
    ]:
        if df[key].isna().any():
            raise ValueError(f"{table_name} contains missing {key} values.")
        if df[key].duplicated().any():
            raise ValueError(f"{table_name} contains duplicate {key} values.")

    # Work with a copy so the original uploaded data stays unchanged.
    result = sales.copy()

    result["Date"] = pd.to_datetime(result["Date"], errors="coerce")
    result["Revenue"] = pd.to_numeric(
        result["Revenue"], errors="coerce"
    )

    if result["Date"].isna().any():
        raise ValueError("Sales contains invalid dates.")

    if result["Revenue"].isna().any():
        raise ValueError("Sales contains missing or invalid revenue values.")

    original_rows = len(result)
    original_revenue = float(result["Revenue"].sum())

    reports = {}

    # Connect Sales to Stores.
    store_lookup = stores.rename(columns={"ID": "Store ID"})

    unmatched_stores = set(result["Store ID"].dropna()) - set(
        store_lookup["Store ID"].dropna()
    )
    if unmatched_stores:
        raise ValueError(
            f"Sales contains unknown Store IDs: {sorted(unmatched_stores)}"
        )

    result, reports["Stores"] = check_merge(
        result, store_lookup, on="Store ID",
        value_col="Revenue", how="left"
    )

    # Connect Sales to Products.
    unmatched_products = set(result["Product ID"].dropna()) - set(
        products["Product ID"].dropna()
    )
    if unmatched_products:
        raise ValueError(
            f"Sales contains unknown Product IDs: {sorted(unmatched_products)}"
        )

    result, reports["Products"] = check_merge(
        result, products, on="Product ID",
        value_col="Revenue", how="left"
    )

    # Connect Sales to Categories.
    unmatched_categories = set(result["Category ID"].dropna()) - set(
        categories["Category ID"].dropna()
    )
    if unmatched_categories:
        raise ValueError(
            f"Sales contains unknown Category IDs: {sorted(unmatched_categories)}"
        )

    result, reports["Categories"] = check_merge(
        result, categories, on="Category ID",
        value_col="Revenue", how="left"
    )

    # Final integrity check.
    if len(result) != original_rows:
        raise ValueError(
            "The joins changed the number of Sales rows. "
            "Check the table keys."
        )

    final_revenue = float(result["Revenue"].sum())

    if abs(final_revenue - original_revenue) > 0.01:
        raise ValueError(
            "The joins changed total revenue. "
            "Check for duplicated or missing records."
        )

    # Add useful date fields for dashboard filters and charts.
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
