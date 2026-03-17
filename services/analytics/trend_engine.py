from sqlalchemy.orm import Session
from models.sqp_model import SqpReport, SqpBrandKeyword
from services.ml.pattern_detector import analyse_keyword_ml, ml_active
from datetime import date, timedelta


def get_filtered_reports(filter_type: str, all_reports: list):
    """
    Filter reports based on filter type.
    Uses report COUNT for weekly filters — more intuitive than calendar weeks.
    Uses calendar dates for monthly filters.
    """
    if not all_reports:
        return [], None, None

    # Sort ascending by date
    sorted_reports = sorted(all_reports, key=lambda r: r.period_start)
    latest_date   = sorted_reports[-1].period_start
    earliest_date = sorted_reports[0].period_start

    if filter_type == "4weeks":
        # Last 4 uploaded reports
        filtered = sorted_reports[-4:]

    elif filter_type == "6weeks":
        # Last 6 uploaded reports
        filtered = sorted_reports[-6:]

    elif filter_type == "8weeks":
        # Last 8 uploaded reports
        filtered = sorted_reports[-8:]

    elif filter_type == "this_month":
        # Reports in current calendar month of latest report
        month_start = latest_date.replace(day=1)
        filtered = [r for r in sorted_reports if r.period_start >= month_start]

    elif filter_type == "last_month":
        # Reports in previous calendar month
        first_of_this  = latest_date.replace(day=1)
        last_month_end = first_of_this - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        filtered = [r for r in sorted_reports if last_month_start <= r.period_start <= last_month_end]

    elif filter_type == "all":
        filtered = sorted_reports

    else:
        # Default → last 6 reports
        filtered = sorted_reports[-6:]

    # Fallback — need at least 2 reports for any analysis
    if len(filtered) < 2:
        filtered = sorted_reports[-2:] if len(sorted_reports) >= 2 else sorted_reports

    range_start = filtered[0].period_start  if filtered else earliest_date
    range_end   = filtered[-1].period_start if filtered else latest_date

    return filtered, range_start, range_end


def get_keyword_trends(seller_id: int, db: Session, filter_type: str = "6weeks") -> dict:
    """
    Calculate historical trends for keywords.

    filter_type options:
      4weeks     → last 4 uploaded reports
      6weeks     → last 6 uploaded reports (default)
      8weeks     → last 8 uploaded reports
      this_month → current calendar month
      last_month → previous calendar month
      all        → all available data
    """

    # Get ALL reports
    all_reports = db.query(SqpReport).filter(
        SqpReport.seller_id == seller_id,
        SqpReport.period_type == "WEEKLY"
    ).order_by(SqpReport.period_start.asc()).all()

    if len(all_reports) < 2:
        return {
            "success":            False,
            "message":            "Need at least 2 weekly uploads for trend analysis",
            "reports_available":  len(all_reports)
        }

    # Apply filter
    reports, range_start, range_end = get_filtered_reports(filter_type, all_reports)
    num_reports = len(reports)

    # Build keyword history for filtered reports only
    keyword_history = {}

    for report in reports:
        keywords = db.query(SqpBrandKeyword).filter(
            SqpBrandKeyword.report_id == report.id
        ).all()

        for k in keywords:
            query = k.search_query
            if query not in keyword_history:
                keyword_history[query] = []

            price_gap_pct = 0
            if k.clicks_price_median and k.clicks_brand_price_median and k.clicks_price_median > 0:
                price_gap_pct = round(
                    ((k.clicks_brand_price_median - k.clicks_price_median) / k.clicks_price_median) * 100, 2
                )

            keyword_history[query].append({
                "week":                    str(report.period_start),
                "report_id":               report.id,
                "volume":                  k.search_query_volume,
                "impressions_brand_share": k.impressions_brand_share,
                "clicks_brand_share":      k.clicks_brand_share,
                "purchase_share":          k.purchases_brand_share,
                "market_price":            k.clicks_price_median,
                "brand_price":             k.clicks_brand_price_median,
                "price_gap_pct":           price_gap_pct,
                "data_quality":            report.data_quality
            })

    # Run ML analysis on each keyword
    keyword_trends = []

    for query, history in keyword_history.items():
        if len(history) < 2:
            continue

        ml_result    = analyse_keyword_ml(history, num_reports)
        volume_trend = ml_result.get("volume_trend", {})
        share_trend  = ml_result.get("share_trend", {})
        price_corr   = ml_result.get("price_share_correlation", {})
        forecast     = ml_result.get("volume_forecast", {})
        anomalies    = ml_result.get("volume_anomalies", {})
        smoothed     = ml_result.get("smoothed_volumes", [])

        volumes = [h["volume"] for h in history]
        shares  = [h["purchase_share"] for h in history]

        share_change   = round(shares[-1] - shares[0], 2) if shares else 0
        share_momentum = "GAINING" if share_change > 0 else "LOSING" if share_change < 0 else "STABLE"

        keyword_trends.append({
            "search_query":     query,
            "weeks_tracked":    len(history),
            "history":          history,
            "smoothed_volumes": smoothed,
            "volume_trend": {
                "pattern":            volume_trend.get("pattern"),
                "confidence":         volume_trend.get("confidence"),
                "method":             volume_trend.get("method"),
                "slope_pct_per_week": volume_trend.get("slope_pct_per_week"),
                "total_change_pct":   volume_trend.get("total_change_pct"),
                "first_week_volume":  volumes[0],
                "latest_volume":      volumes[-1]
            },
            "share_trend": {
                "pattern":            share_trend.get("pattern"),
                "confidence":         share_trend.get("confidence"),
                "method":             share_trend.get("method"),
                "momentum":           share_momentum,
                "first_week_share":   shares[0],
                "latest_share":       shares[-1],
                "total_share_change": share_change
            },
            "forecast": {
                "next_week_volume": forecast.get("forecast_volume"),
                "forecast_lower":   forecast.get("forecast_lower"),
                "forecast_upper":   forecast.get("forecast_upper"),
                "confidence":       forecast.get("confidence"),
                "method":           forecast.get("method")
            },
            "price_analysis": {
                "correlation":          price_corr.get("correlation"),
                "price_hurting_share":  price_corr.get("price_hurting_share"),
                "correlation_strength": price_corr.get("strength"),
                "method":               price_corr.get("method"),
                "first_week_gap_pct":   history[0]["price_gap_pct"],
                "latest_gap_pct":       history[-1]["price_gap_pct"]
            },
            "anomalies": anomalies
        })

    keyword_trends.sort(key=lambda x: x["volume_trend"]["latest_volume"] or 0, reverse=True)

    rising        = [k for k in keyword_trends if k["volume_trend"]["pattern"] in ["RISING", "CONSISTENTLY_RISING"]]
    declining     = [k for k in keyword_trends if k["volume_trend"]["pattern"] in ["DECLINING", "CONSISTENTLY_DECLINING"]]
    losing_share  = [k for k in keyword_trends if k["share_trend"]["momentum"] == "LOSING"]
    price_hurting = [k for k in keyword_trends if k["price_analysis"]["price_hurting_share"]]
    has_anomalies = [k for k in keyword_trends if k["anomalies"].get("has_anomaly")]

    return {
        "success":                 True,
        "seller_id":               seller_id,
        "filter_applied":          filter_type,
        "date_range": {
            "from": str(range_start),
            "to":   str(range_end)
        },
        "total_reports_available": len(all_reports),
        "total_reports_analysed":  num_reports,
        "total_keywords_tracked":  len(keyword_trends),
        "ml_active":               ml_active(num_reports),
        "report_dates":            [str(r.period_start) for r in reports],
        "keyword_trends":          keyword_trends,
        "summary": {
            "rising_keywords":              len(rising),
            "declining_keywords":           len(declining),
            "keywords_losing_share":        len(losing_share),
            "keywords_where_price_hurting": len(price_hurting),
            "keywords_with_anomalies":      len(has_anomalies)
        },
        "alerts": {
            "rising_keywords":        [k["search_query"] for k in rising[:5]],
            "declining_keywords":     [k["search_query"] for k in declining[:5]],
            "losing_share_keywords":  [k["search_query"] for k in losing_share[:5]],
            "price_hurting_keywords": [k["search_query"] for k in price_hurting[:5]],
            "anomaly_keywords":       [k["search_query"] for k in has_anomalies[:5]]
        }
    }