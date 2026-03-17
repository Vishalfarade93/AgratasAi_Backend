def calculate_metrics(keywords: list) -> dict:
    """
    Calculate core analytics metrics from a list of keyword objects.
    Works on any set of keywords - single report or aggregated.
    """

    if not keywords:
        return {"error": "No keywords provided"}

    # Deduplicate by search_query — keep most recent date
    seen = {}
    for k in keywords:
        if k.search_query not in seen:
            seen[k.search_query] = k
        else:
            if k.reporting_date > seen[k.search_query].reporting_date:
                seen[k.search_query] = k

    unique_keywords = list(seen.values())

    # ── Core Totals ──────────────────────────────────────────────
    total_impressions = sum(k.impressions_total for k in unique_keywords)
    total_clicks = sum(k.clicks_total for k in unique_keywords)
    total_cart_adds = sum(k.cart_adds_total for k in unique_keywords)
    total_purchases = sum(k.purchases_total for k in unique_keywords)

    # ── Market Funnel Rates ──────────────────────────────────────
    market_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else 0
    market_cvr = round((total_purchases / total_clicks) * 100, 2) if total_clicks > 0 else 0
    click_to_cart = round((total_cart_adds / total_clicks) * 100, 2) if total_clicks > 0 else 0
    cart_to_purchase = round((total_purchases / total_cart_adds) * 100, 2) if total_cart_adds > 0 else 0

    # ── Brand Share Averages ─────────────────────────────────────
    avg_impression_share = round(sum(k.impressions_brand_share for k in unique_keywords) / len(unique_keywords), 2)
    avg_click_share = round(sum(k.clicks_brand_share for k in unique_keywords) / len(unique_keywords), 2)
    avg_purchase_share = round(sum(k.purchases_brand_share for k in unique_keywords) / len(unique_keywords), 2)

    # ── Price Gap Analysis ───────────────────────────────────────
    price_gaps = []
    for k in unique_keywords:
        if k.clicks_price_median and k.clicks_brand_price_median:
            gap = round(k.clicks_brand_price_median - k.clicks_price_median, 2)
            gap_pct = round((gap / k.clicks_price_median) * 100, 2) if k.clicks_price_median > 0 else 0
            price_gaps.append({
                "search_query": k.search_query,
                "market_price": k.clicks_price_median,
                "brand_price": k.clicks_brand_price_median,
                "price_gap": gap,
                "price_gap_pct": gap_pct,
                "positioning": "PREMIUM" if gap > 0 else "DISCOUNT" if gap < 0 else "MATCHED"
            })

    price_gaps.sort(key=lambda x: abs(x["price_gap"]), reverse=True)

    # ── Top Opportunity Keywords ─────────────────────────────────
    # High volume + low brand share = biggest growth opportunity
    opportunities = []
    for k in unique_keywords:
        if k.search_query_volume > 0 and k.purchases_brand_share < 15:
            opportunities.append({
                "search_query": k.search_query,
                "volume": k.search_query_volume,
                "brand_purchase_share": k.purchases_brand_share,
                "purchases_total": k.purchases_total,
                "purchases_brand": k.purchases_brand
            })

    opportunities.sort(key=lambda x: x["volume"], reverse=True)

    return {
        "summary": {
            "total_keywords": len(unique_keywords),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_cart_adds": total_cart_adds,
            "total_purchases": total_purchases
        },
        "funnel": {
            "market_ctr_pct": market_ctr,
            "market_cvr_pct": market_cvr,
            "click_to_cart_pct": click_to_cart,
            "cart_to_purchase_pct": cart_to_purchase
        },
        "brand_share": {
            "avg_impression_share": avg_impression_share,
            "avg_click_share": avg_click_share,
            "avg_purchase_share": avg_purchase_share
        },
        "price_gap_analysis": price_gaps[:5],
        "top_opportunities": opportunities[:5]
    }