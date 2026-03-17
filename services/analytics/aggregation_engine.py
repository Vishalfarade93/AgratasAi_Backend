from sqlalchemy.orm import Session
from models.sqp_model import SqpReport, SqpBrandKeyword
from services.analytics.metrics_engine import calculate_metrics
from datetime import date


def get_aggregated_view(seller_id: int, view_type: str, db: Session) -> dict:
    """
    Aggregate weekly data into monthly or quarterly views.

    view_type: MONTHLY or QUARTERLY

    Seller only uploads weekly. System automatically
    aggregates into monthly and quarterly views.
    """

    # Get all weekly reports for seller
    all_reports = db.query(SqpReport).filter(
        SqpReport.seller_id == seller_id,
        SqpReport.period_type == "WEEKLY"
    ).order_by(SqpReport.period_start.asc()).all()

    if not all_reports:
        return {
            "success": False,
            "message": "No weekly reports found"
        }

    # Group reports into periods
    if view_type == "MONTHLY":
        periods = group_by_month(all_reports)
        min_weeks_required = 2
    elif view_type == "QUARTERLY":
        periods = group_by_quarter(all_reports)
        min_weeks_required = 6
    else:
        return {"success": False, "message": "view_type must be MONTHLY or QUARTERLY"}

    aggregated_periods = []

    for period_label, period_reports in periods.items():

        # Get all keywords for all reports in this period
        all_keywords = []
        for report in period_reports:
            keywords = db.query(SqpBrandKeyword).filter(
                SqpBrandKeyword.report_id == report.id
            ).all()
            all_keywords.extend(keywords)

        if not all_keywords:
            continue

        # Calculate coverage
        weeks_in_period = len(period_reports)
        expected_weeks = 4 if view_type == "MONTHLY" else 13
        coverage_pct = round((weeks_in_period / expected_weeks) * 100)

        # Calculate metrics for this period
        metrics = calculate_metrics(all_keywords)

        aggregated_periods.append({
            "period": period_label,
            "weeks_available": weeks_in_period,
            "expected_weeks": expected_weeks,
            "coverage_pct": coverage_pct,
            "data_complete": weeks_in_period >= min_weeks_required,
            "warning": None if coverage_pct >= 75 else f"Only {coverage_pct}% data available for this period",
            "metrics": metrics
        })

    return {
        "success": True,
        "seller_id": seller_id,
        "view_type": view_type,
        "periods": aggregated_periods
    }


def group_by_month(reports: list) -> dict:
    """Group weekly reports by calendar month"""
    months = {}
    for report in reports:
        key = report.period_start.strftime("%Y-%m")
        if key not in months:
            months[key] = []
        months[key].append(report)
    return months


def group_by_quarter(reports: list) -> dict:
    """Group weekly reports by calendar quarter"""
    quarters = {}
    for report in reports:
        quarter = (report.period_start.month - 1) // 3 + 1
        key = f"{report.period_start.year}-Q{quarter}"
        if key not in quarters:
            quarters[key] = []
        quarters[key].append(report)
    return quarters