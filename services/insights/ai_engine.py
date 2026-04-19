import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("GROQ KEY LOADED:", GROQ_API_KEY[:10] if GROQ_API_KEY else "NOT FOUND")


def generate_insights(seller_id: int, metrics: dict, trends: dict) -> dict:

    # Extract rule-based signals
    rising_keywords    = trends.get("alerts", {}).get("rising_keywords", [])
    declining_keywords = trends.get("alerts", {}).get("declining_keywords", [])
    losing_share       = trends.get("alerts", {}).get("losing_share_keywords", [])
    price_hurting      = trends.get("alerts", {}).get("price_hurting_keywords", [])

    avg_purchase_share = metrics.get("brand_share", {}).get("avg_purchase_share", 0)
    funnel             = metrics.get("funnel", {})
    brand_share        = metrics.get("brand_share", {})
    price_gaps         = metrics.get("price_gap_analysis", [])
    opportunities      = metrics.get("top_opportunities", [])
    summary            = metrics.get("summary", {})

    # Rule-based insights (always generated as fallback)
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

    # ── Groq AI Layer ─────────────────────────────────────────────
    ai_insights = None
    ai_status   = "RULE_BASED"
    ai_model    = None

    if GROQ_API_KEY:
        try:
            from groq import Groq

            client = Groq(api_key=GROQ_API_KEY)

            # Build keyword summary for prompt (top 10 only)
            keyword_trends = trends.get("keyword_trends", [])
            keyword_lines  = []
            for kw in keyword_trends[:10]:
                vt = kw.get("volume_trend", {})
                st = kw.get("share_trend",  {})
                pa = kw.get("price_analysis", {})
                fc = kw.get("forecast", {})
                keyword_lines.append(
                    f"  - {kw['search_query']}: "
                    f"pattern={vt.get('pattern','N/A')}, "
                    f"growth={vt.get('growth_pct', 0)}%, "
                    f"confidence={vt.get('confidence', 0)}%, "
                    f"share_momentum={st.get('share_momentum','N/A')}, "
                    f"price_correlation={pa.get('correlation','N/A')} ({pa.get('correlation_strength','N/A')}), "
                    f"next_week_forecast={fc.get('next_week_volume','N/A')}"
                )

            price_gap_lines = []
            for pg in price_gaps[:5]:
                price_gap_lines.append(
                    f"  - {pg['search_query']}: market=₹{pg['market_price']}, "
                    f"brand=₹{pg['brand_price']}, "
                    f"gap={pg['price_gap_pct']}% ({pg['positioning']})"
                )

            opportunity_lines = []
            for op in opportunities[:5]:
                opportunity_lines.append(
                    f"  - {op['search_query']}: volume={op['volume']:,}, "
                    f"brand_share={op['brand_purchase_share']}%"
                )

            prompt = f"""You are a senior Amazon market intelligence analyst. Analyze this seller's SQP data and give sharp, specific, actionable insights.

MARKET OVERVIEW:
- Total impressions: {summary.get('total_impressions', 0):,}
- Total clicks: {summary.get('total_clicks', 0):,}
- Total purchases: {summary.get('total_purchases', 0):,}
- Market CTR: {funnel.get('market_ctr_pct', 0)}%
- Market CVR: {funnel.get('market_cvr_pct', 0)}%
- Click to cart rate: {funnel.get('click_to_cart_pct', 0)}%
- Cart to purchase rate: {funnel.get('cart_to_purchase_pct', 0)}%

BRAND SHARE:
- Avg impression share: {brand_share.get('avg_impression_share', 0)}%
- Avg click share: {brand_share.get('avg_click_share', 0)}%
- Avg purchase share: {brand_share.get('avg_purchase_share', 0)}%

KEYWORD TRENDS (ML Analysis):
{chr(10).join(keyword_lines) if keyword_lines else '  No trend data available'}

PRICE GAP ANALYSIS:
{chr(10).join(price_gap_lines) if price_gap_lines else '  No price gap data'}

TOP OPPORTUNITIES (high volume, low brand share):
{chr(10).join(opportunity_lines) if opportunity_lines else '  No opportunity data'}

Write a strategic analysis with exactly these 4 sections:

## Market Health
2-3 sentences on overall market condition based on CTR, CVR, funnel rates.

## Brand Performance
2-3 sentences on how this brand is doing vs the market. Mention specific keywords by name.

## Pricing Impact
2-3 sentences on price gap analysis. If any keyword has strong negative price-share correlation, call it out with exact numbers.

## Action Plan
3-4 bullet points starting with •. Each must be specific — include keyword names, price numbers, percentages where available.

Be direct and data-driven. Use ₹ for prices. No fluff."""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior Amazon market intelligence analyst. Be direct, specific, and data-driven."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1024
            )

            ai_insights = response.choices[0].message.content.strip()
            ai_status   = "GROQ_POWERED"
            ai_model    = "llama-3.3-70b-versatile"
            print("Groq responded successfully")

        except Exception as e:
            print(f"Groq API error: {e}")
            ai_insights = None
            ai_status   = "RULE_BASED"

    return {
        "success":     True,
        "seller_id":   seller_id,
        "insights":    insights,
        "ai_status":   ai_status,
        "ai_insights": ai_insights,
        "ai_model":    ai_model,
        "note": None if ai_insights else "AI integration coming in next phase for deeper insights"
    }