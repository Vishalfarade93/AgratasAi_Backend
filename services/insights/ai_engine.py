"""
AI Insight Engine
Uses Claude API to generate plain English strategic insights
from calculated metrics and trend data.

This will be fully implemented after trend engine is complete.
"""


def generate_insights(seller_id: int, metrics: dict, trends: dict) -> dict:
    """
    Send calculated metrics and trends to Claude API.
    Returns plain English strategic recommendations.

    Currently returns structured placeholder.
    Claude API integration coming in next phase.
    """

    # Extract key signals for insight generation
    rising_keywords = trends.get("alerts", {}).get("rising_keywords", [])
    declining_keywords = trends.get("alerts", {}).get("declining_keywords", [])
    losing_share = trends.get("alerts", {}).get("losing_share_keywords", [])
    price_hurting = trends.get("alerts", {}).get("price_hurting_keywords", [])

    avg_purchase_share = metrics.get("brand_share", {}).get("avg_purchase_share", 0)
    market_cvr = metrics.get("funnel", {}).get("market_cvr_pct", 0)

    # Rule based insights until Claude API is integrated
    insights = []

    if rising_keywords:
        insights.append({
            "type": "OPPORTUNITY",
            "priority": "HIGH",
            "message": f"Market demand is growing for: {', '.join(rising_keywords[:3])}. Focus your advertising budget here."
        })

    if losing_share:
        insights.append({
            "type": "WARNING",
            "priority": "HIGH",
            "message": f"You are losing market share in: {', '.join(losing_share[:3])}. Competitors are gaining ground."
        })

    if price_hurting:
        insights.append({
            "type": "PRICING",
            "priority": "MEDIUM",
            "message": f"Price gap is hurting conversions for: {', '.join(price_hurting[:3])}. Consider reducing price gap."
        })

    if declining_keywords:
        insights.append({
            "type": "ALERT",
            "priority": "MEDIUM",
            "message": f"Demand declining for: {', '.join(declining_keywords[:3])}. Reduce ad spend on these keywords."
        })

    if avg_purchase_share < 10:
        insights.append({
            "type": "SHARE",
            "priority": "HIGH",
            "message": f"Average purchase share is {avg_purchase_share}% which is below 10%. Strong growth opportunity exists."
        })

    return {
        "success": True,
        "seller_id": seller_id,
        "insights": insights,
        "ai_status": "RULE_BASED",
        "note": "Claude API integration coming in next phase for deeper insights"
    }