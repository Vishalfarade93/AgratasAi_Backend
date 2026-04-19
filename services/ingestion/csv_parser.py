import pandas as pd
from datetime import timedelta

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


def parse_csv(file) -> dict:
    """
    Parse and validate an SQP Brand View CSV.
    Returns parsed rows ready for DB insertion.
    """

    try:
        df = pd.read_csv(file)
    except Exception as e:
        return {"success": False, "error": f"Could not read CSV file: {str(e)}"}

    # Validate columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return {
            "success": False,
            "error":   f"Missing columns: {missing}"
        }

    # Auto detect period dates from CSV
    df["Reporting Date"] = pd.to_datetime(df["Reporting Date"])
    period_start = df["Reporting Date"].min().date()

    # period_end = period_start + 6 days (full week)
    # This ensures consecutive weeks have:
    #   Week 1 end = Oct 12, Week 2 start = Oct 13 → 1 day gap → COMPLETE
    period_end = period_start + timedelta(days=6)

    # Parse each row into DB-ready dict
    rows = []
    for _, row in df.iterrows():
        try:
            rows.append({
                "search_query":              str(row["Search Query"]),
                "search_query_score":        int(row["Search Query Score"]),
                "search_query_volume":       int(row["Search Query Volume"]),
                "reporting_date":            pd.to_datetime(row["Reporting Date"]).date(),
                "impressions_total":         int(row["Impressions: Total Count"]),
                "impressions_brand":         int(row["Impressions: Brand Count"]),
                "impressions_brand_share":   float(row["Impressions: Brand Share %"]),
                "clicks_total":              int(row["Clicks: Total Count"]),
                "clicks_click_rate":         float(row["Clicks: Click Rate %"]),
                "clicks_brand":              int(row["Clicks: Brand Count"]),
                "clicks_brand_share":        float(row["Clicks: Brand Share %"]),
                "clicks_price_median":       float(row["Clicks: Price (Median)"]),
                "clicks_brand_price_median": float(row["Clicks: Brand Price (Median)"]),
                "cart_adds_total":           int(row["Cart Adds: Total Count"]),
                "cart_adds_rate":            float(row["Cart Adds: Cart Add Rate %"]),
                "cart_adds_brand":           int(row["Cart Adds: Brand Count"]),
                "cart_adds_brand_share":     float(row["Cart Adds: Brand Share %"]),
                "purchases_total":           int(row["Purchases: Total Count"]),
                "purchases_rate":            float(row["Purchases: Purchase Rate %"]),
                "purchases_brand":           int(row["Purchases: Brand Count"]),
                "purchases_brand_share":     float(row["Purchases: Brand Share %"]),
                "purchases_price_median":    float(row["Purchases: Price (Median)"]),
            })
        except Exception as e:
            return {
                "success": False,
                "error":   f"Error parsing row for '{row.get('Search Query', 'unknown')}': {str(e)}"
            }

    return {
        "success":      True,
        "period_start": period_start,
        "period_end":   period_end,
        "total_rows":   len(rows),
        "rows":         rows
    }