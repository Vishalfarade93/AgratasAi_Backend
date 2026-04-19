from sqlalchemy.orm import Session
from models.sqp_model import SqpReport, SqpBrandKeyword
from services.ml.pattern_detector import analyse_keyword_ml, ml_active
from services.analytics.trend_engine import get_filtered_reports
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def generate_keyword_insight(
    search_query, pattern, volume_growth, share_change,
    share_momentum, correlation, corr_strength,
    price_gaps, forecast, funnel, brand_prices, market_prices
) -> str:
    """Generate AI insight for a single keyword using Groq."""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        latest_gap = price_gaps[-1] if price_gaps else 0
        latest_brand = brand_prices[-1] if brand_prices else 0
        latest_market = market_prices[-1] if market_prices else 0
        next_vol = forecast.get("next_week_volume") if forecast else "N/A"

        prompt = f"""Analyze this single Amazon keyword for a seller and give a sharp 3-4 sentence insight.

Keyword: {search_query}
Volume Pattern: {pattern} ({volume_growth:+.1f}% over tracked period)
Brand Share: {share_momentum} ({share_change:+.2f}% change)
Price Gap: ₹{latest_gap} (brand=₹{latest_brand}, market=₹{latest_market})
Price-Share Correlation: {correlation} ({corr_strength})
Next Week Forecast: {next_vol:,} searches
Funnel CTR: {funnel.get('ctr')}%, CVR: {funnel.get('cvr')}%

Write 3-4 sentences covering:
1. What is happening with this keyword (volume + share together)
2. Whether pricing is helping or hurting
3. One specific recommendation with a number in it

Be direct. Use ₹. No fluff."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an Amazon market analyst. Be concise and specific."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Keyword AI insight error: {e}")
        return None


def get_keyword_detail(seller_id: int, search_query: str, filter_type: str, db: Session) -> dict:
    """
    Get detailed analysis for a single keyword.
    Uses the same ML engine as trends page.
    filter_type: '4weeks', '6weeks', '8weeks', 'this_month', 'last_month', 'all'
    """
    # Get all reports for this seller ordered by date
    all_reports = db.query(SqpReport).filter(
        SqpReport.seller_id == seller_id,
        SqpReport.period_type == "WEEKLY"
    ).order_by(SqpReport.period_start.asc()).all()

    if not all_reports:
        return {"success": False, "message": "No reports found"}

    # Apply the same filter as trends page
    filtered_reports, range_start, range_end = get_filtered_reports(filter_type, all_reports)

    if len(filtered_reports) < 2:
        return {
            "success": False,
            "message": f"Need at least 2 weeks of data for filter '{filter_type}'. Currently have {len(filtered_reports)} weeks."
        }

    # Build history for this keyword from filtered reports only
    history = []
    for report in filtered_reports:
        kw = db.query(SqpBrandKeyword).filter(
            SqpBrandKeyword.report_id == report.id,
            SqpBrandKeyword.search_query == search_query
        ).first()

        if kw:
            price_gap_pct = 0
            if kw.clicks_price_median and kw.clicks_brand_price_median and kw.clicks_price_median > 0:
                price_gap_pct = round(
                    ((kw.clicks_brand_price_median - kw.clicks_price_median) / kw.clicks_price_median) * 100, 2
                )

            history.append({
                "week": str(report.period_start),
                "report_id": report.id,
                "volume": kw.search_query_volume,
                "impressions_brand_share": kw.impressions_brand_share,
                "clicks_brand_share": kw.clicks_brand_share,
                "purchase_share": kw.purchases_brand_share,
                "market_price": kw.clicks_price_median,
                "brand_price": kw.clicks_brand_price_median,
                "price_gap_pct": price_gap_pct,
                "data_quality": report.data_quality,
                "impressions_total": kw.impressions_total,
                "clicks_total": kw.clicks_total,
                "clicks_click_rate": kw.clicks_click_rate,
                "cart_adds_total": kw.cart_adds_total,
                "cart_adds_brand": kw.cart_adds_brand,
                "cart_adds_brand_share": kw.cart_adds_brand_share,
                "purchases_total": kw.purchases_total,
                "purchases_brand": kw.purchases_brand,
                "purchases_rate": kw.purchases_rate,
            })

    if not history:
        return {"success": False, "message": f"Keyword '{search_query}' not found in filtered reports"}

    # Run the same ML analysis as trends page
    ml_result = analyse_keyword_ml(history, len(filtered_reports))
    volume_trend = ml_result.get("volume_trend", {})
    share_trend = ml_result.get("share_trend", {})
    price_corr = ml_result.get("price_share_correlation", {})
    forecast = ml_result.get("volume_forecast", {})
    anomalies = ml_result.get("volume_anomalies", {})
    smoothed = ml_result.get("smoothed_volumes", [])

    volumes = [h["volume"] for h in history]
    shares = [h["purchase_share"] for h in history]

    share_change = round(shares[-1] - shares[0], 2) if shares else 0
    share_momentum = "GAINING" if share_change > 0 else "LOSING" if share_change < 0 else "STABLE"

    # Latest funnel data (last week)
    latest = history[-1]
    funnel = {
        "impressions": latest["impressions_total"],
        "clicks": latest["clicks_total"],
        "cart_adds": latest["cart_adds_total"],
        "purchases": latest["purchases_total"],
        "ctr": latest["clicks_click_rate"],
        "cvr": latest["purchases_rate"],
        "click_to_cart": round(
            (latest["cart_adds_total"] / latest["clicks_total"]) * 100, 2
        ) if latest["clicks_total"] > 0 else 0,
        "cart_to_purchase": round(
            (latest["purchases_total"] / latest["cart_adds_total"]) * 100, 2
        ) if latest["cart_adds_total"] > 0 else 0,
    }

    return {
        "success": True,
        "search_query": search_query,
        "filter_applied": filter_type,
        "date_range": {
            "from": str(range_start),
            "to": str(range_end)
        },
        "weeks_tracked": len(history),
        "total_reports_analysed": len(filtered_reports),
        "ml_active": ml_active(len(filtered_reports)),
        "volume_trend": {
            "pattern": volume_trend.get("pattern"),
            "confidence": volume_trend.get("confidence"),
            "growth_pct": volume_trend.get("total_change_pct", 0),
            "slope_pct_per_week": volume_trend.get("slope_pct_per_week"),
            "volumes": volumes,
            "smoothed": smoothed,
            "weeks": [h["week"] for h in history],
            "forecast": {
                "next_week_volume": forecast.get("forecast_volume"),
                "forecast_lower": forecast.get("forecast_lower"),
                "forecast_upper": forecast.get("forecast_upper"),
                "confidence": forecast.get("confidence")
            } if forecast else None
        },
        "share_trend": {
            "shares": shares,
            "share_change": share_change,
            "share_momentum": share_momentum,
            "weeks": [h["week"] for h in history]
        },
        "price_analysis": {
            "market_prices": [h["market_price"] for h in history],
            "brand_prices": [h["brand_price"] for h in history],
            "price_gaps": [h["price_gap_pct"] for h in history],
            "correlation": price_corr.get("correlation"),
            "corr_strength": price_corr.get("strength"),
            "weeks": [h["week"] for h in history]
        },
        "funnel": funnel,
        "history": history,
        "anomalies": anomalies,
        "ai_insight": generate_keyword_insight(
            search_query=search_query,
            pattern=volume_trend.get("pattern"),
            volume_growth=volume_trend.get("total_change_pct", 0),
            share_change=share_change,
            share_momentum=share_momentum,
            correlation=price_corr.get("correlation"),
            corr_strength=price_corr.get("strength"),
            price_gaps=[h["price_gap_pct"] for h in history],
            forecast=forecast,
            funnel=funnel,
            brand_prices=[h["brand_price"] for h in history],
            market_prices=[h["market_price"] for h in history]
        )
    }