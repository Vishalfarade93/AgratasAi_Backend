import pandas as pd

REQUIRED_COLUMNS = [
    "Search Query",
    "Search Query Score",
    "Search Query Volume",
    "Reporting Date",
    "Impressions: Total Count",
    "Impressions: Brand Count",
    "Impressions: Brand Share %",
    "Clicks: Total Count",
    "Clicks: Click Rate %",
    "Clicks: Brand Count",
    "Clicks: Brand Share %",
    "Clicks: Price (Median)",
    "Clicks: Brand Price (Median)",
    "Cart Adds: Total Count",
    "Cart Adds: Cart Add Rate %",
    "Cart Adds: Brand Count",
    "Cart Adds: Brand Share %",
    "Purchases: Total Count",
    "Purchases: Purchase Rate %",
    "Purchases: Brand Count",
    "Purchases: Brand Share %",
    "Purchases: Price (Median)"
]


def validate_columns(df: pd.DataFrame):
    """Check if all required columns exist in uploaded CSV"""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return missing


def parse_csv(file) -> dict:
    """
    Read and parse the uploaded SQP CSV file.
    Returns normalized data ready for storage.
    """
    df = pd.read_csv(file)

    # Validate columns first
    missing_columns = validate_columns(df)
    if missing_columns:
        return {
            "success": False,
            "error": f"Missing columns: {missing_columns}"
        }

    # Normalize search queries to lowercase and strip whitespace
    df["Search Query"] = df["Search Query"].str.lower().str.strip()

    # Auto detect period dates from CSV
    df["Reporting Date"] = pd.to_datetime(df["Reporting Date"])
    period_start = df["Reporting Date"].min().date()
    period_end = df["Reporting Date"].max().date()

    # Convert rows to list of dicts for easy processing
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "search_query": row["Search Query"],
            "search_query_score": int(row["Search Query Score"]),
            "search_query_volume": int(row["Search Query Volume"]),
            "reporting_date": pd.to_datetime(row["Reporting Date"]).date(),
            "impressions_total": int(row["Impressions: Total Count"]),
            "impressions_brand": int(row["Impressions: Brand Count"]),
            "impressions_brand_share": float(row["Impressions: Brand Share %"]),
            "clicks_total": int(row["Clicks: Total Count"]),
            "clicks_click_rate": float(row["Clicks: Click Rate %"]),
            "clicks_brand": int(row["Clicks: Brand Count"]),
            "clicks_brand_share": float(row["Clicks: Brand Share %"]),
            "clicks_price_median": float(row["Clicks: Price (Median)"]),
            "clicks_brand_price_median": float(row["Clicks: Brand Price (Median)"]),
            "cart_adds_total": int(row["Cart Adds: Total Count"]),
            "cart_adds_rate": float(row["Cart Adds: Cart Add Rate %"]),
            "cart_adds_brand": int(row["Cart Adds: Brand Count"]),
            "cart_adds_brand_share": float(row["Cart Adds: Brand Share %"]),
            "purchases_total": int(row["Purchases: Total Count"]),
            "purchases_rate": float(row["Purchases: Purchase Rate %"]),
            "purchases_brand": int(row["Purchases: Brand Count"]),
            "purchases_brand_share": float(row["Purchases: Brand Share %"]),
            "purchases_price_median": float(row["Purchases: Price (Median)"])
        })

    return {
        "success": True,
        "period_start": period_start,
        "period_end": period_end,
        "total_rows": len(rows),
        "rows": rows
    }