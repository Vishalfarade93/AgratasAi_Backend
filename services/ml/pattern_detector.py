"""
ML Layer - scikit-learn based intelligence
Activates when seller has 4+ weekly reports.
Below 4 reports → falls back to pure Python logic.
"""

import numpy as np

# Try importing sklearn - guide user if not installed
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ── Activation Check ─────────────────────────────────────────────

def ml_active(num_reports: int) -> bool:
    """ML activates only when we have enough data to be meaningful"""
    return SKLEARN_AVAILABLE and num_reports >= 4


# ── Trend Pattern Detection ───────────────────────────────────────

def detect_trend_pattern(values: list) -> dict:
    """
    Detect trend pattern from a list of values over time.

    < 4 points → Pure Python direction check
    ≥ 4 points → Linear Regression with R² confidence
    """
    n = len(values)

    if n < 2:
        return {
            "pattern": "INSUFFICIENT_DATA",
            "confidence": 0,
            "method": "NONE"
        }

    # Pure Python fallback for < 4 points
    if n < 4 or not SKLEARN_AVAILABLE:
        return _python_pattern(values)

    # ML-based pattern detection
    return _ml_pattern(values)


def _python_pattern(values: list) -> dict:
    """Pure Python pattern — used when < 4 data points"""
    first, last = values[0], values[-1]
    change_pct = ((last - first) / first) * 100 if first > 0 else 0

    if all(values[i] < values[i + 1] for i in range(len(values) - 1)):
        pattern = "CONSISTENTLY_RISING"
    elif all(values[i] > values[i + 1] for i in range(len(values) - 1)):
        pattern = "CONSISTENTLY_DECLINING"
    elif change_pct > 10:
        pattern = "RISING"
    elif change_pct < -10:
        pattern = "DECLINING"
    else:
        pattern = "STABLE"

    return {
        "pattern": pattern,
        "confidence": None,
        "method": "PYTHON",
        "total_change_pct": round(change_pct, 2)
    }


def _ml_pattern(values: list) -> dict:
    """
    Linear Regression based trend pattern.
    R² score tells us how consistent/reliable the trend is.
    """
    n = len(values)
    X = np.arange(n).reshape(-1, 1)
    y = np.array(values, dtype=float)

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    r2 = model.score(X, y)

    # Normalize slope as % change per week
    baseline = y[0] if y[0] != 0 else 1
    slope_pct = (slope / baseline) * 100

    # Pattern based on slope direction and strength
    if slope_pct > 2 and r2 > 0.7:
        pattern = "CONSISTENTLY_RISING"
    elif slope_pct > 0.5:
        pattern = "RISING"
    elif slope_pct < -2 and r2 > 0.7:
        pattern = "CONSISTENTLY_DECLINING"
    elif slope_pct < -0.5:
        pattern = "DECLINING"
    else:
        pattern = "STABLE"

    total_change_pct = ((values[-1] - values[0]) / values[0]) * 100 if values[0] > 0 else 0

    return {
        "pattern": pattern,
        "confidence": round(r2 * 100, 1),   # R² as 0-100%
        "method": "ML_LINEAR_REGRESSION",
        "slope_pct_per_week": round(slope_pct, 2),
        "total_change_pct": round(total_change_pct, 2)
    }


# ── Demand Forecasting ────────────────────────────────────────────

def forecast_next_week(volumes: list) -> dict:
    """
    Forecast next week's search volume using Linear Regression.
    Returns prediction + confidence interval.
    """
    n = len(volumes)

    if n < 4 or not SKLEARN_AVAILABLE:
        # Simple average growth fallback
        if n >= 2:
            avg_growth = (volumes[-1] - volumes[0]) / (n - 1)
            forecast = round(volumes[-1] + avg_growth)
            return {
                "forecast_volume": forecast,
                "confidence": None,
                "method": "PYTHON_AVERAGE_GROWTH"
            }
        return {"forecast_volume": None, "confidence": None, "method": "INSUFFICIENT_DATA"}

    X = np.arange(n).reshape(-1, 1)
    y = np.array(volumes, dtype=float)

    model = LinearRegression()
    model.fit(X, y)

    # Predict next week (index = n)
    next_week_pred = model.predict([[n]])[0]
    r2 = model.score(X, y)

    # Residual std dev for confidence interval
    predictions = model.predict(X)
    residuals = y - predictions
    std_dev = np.std(residuals)

    return {
        "forecast_volume": round(max(0, next_week_pred)),
        "forecast_lower": round(max(0, next_week_pred - 1.5 * std_dev)),
        "forecast_upper": round(next_week_pred + 1.5 * std_dev),
        "confidence": round(r2 * 100, 1),
        "method": "ML_LINEAR_REGRESSION"
    }


# ── Price-Share Correlation ───────────────────────────────────────

def price_share_correlation(price_gaps: list, shares: list) -> dict:
    """
    Detect if price gap changes correlate with share changes.
    High negative correlation = price is hurting share.

    Returns Pearson correlation coefficient.
    """
    n = len(price_gaps)

    if n < 4 or not SKLEARN_AVAILABLE:
        # Simple direction check
        if n >= 2:
            gap_increased = price_gaps[-1] > price_gaps[0]
            share_declined = shares[-1] < shares[0]
            hurting = gap_increased and share_declined
            return {
                "correlation": None,
                "price_hurting_share": hurting,
                "strength": "UNKNOWN",
                "method": "PYTHON_DIRECTION"
            }
        return {"correlation": None, "price_hurting_share": False, "method": "INSUFFICIENT_DATA"}

    # Pearson correlation
    gap_arr = np.array(price_gaps, dtype=float)
    share_arr = np.array(shares, dtype=float)

    # Handle zero variance
    if np.std(gap_arr) == 0 or np.std(share_arr) == 0:
        return {
            "correlation": 0,
            "price_hurting_share": False,
            "strength": "NO_VARIATION",
            "method": "ML_PEARSON"
        }

    correlation = float(np.corrcoef(gap_arr, share_arr)[0, 1])

    # Negative correlation means: as price gap increases, share decreases
    if correlation < -0.7:
        strength = "STRONG"
        hurting = True
    elif correlation < -0.4:
        strength = "MODERATE"
        hurting = True
    elif correlation < 0:
        strength = "WEAK"
        hurting = False
    else:
        strength = "NONE"
        hurting = False

    return {
        "correlation": round(correlation, 3),
        "price_hurting_share": hurting,
        "strength": strength,
        "method": "ML_PEARSON_CORRELATION"
    }


# ── Anomaly Detection ─────────────────────────────────────────────

def detect_anomalies(values: list) -> dict:
    """
    Detect sudden spikes or drops using Z-score.
    Z-score > 2 = anomaly (value is 2 standard deviations from mean)
    """
    n = len(values)

    if n < 4:
        return {"anomalies": [], "method": "INSUFFICIENT_DATA"}

    arr = np.array(values, dtype=float)
    mean = np.mean(arr)
    std = np.std(arr)

    if std == 0:
        return {"anomalies": [], "method": "NO_VARIATION"}

    z_scores = (arr - mean) / std
    anomalies = []

    for i, (val, z) in enumerate(zip(values, z_scores)):
        if abs(z) > 2:
            anomalies.append({
                "week_index": i,
                "value": val,
                "z_score": round(float(z), 2),
                "type": "SPIKE" if z > 0 else "DROP"
            })

    return {
        "anomalies": anomalies,
        "has_anomaly": len(anomalies) > 0,
        "method": "ML_ZSCORE"
    }


# ── Moving Average Smoothing ──────────────────────────────────────

def smooth_trend(values: list, window: int = 3) -> list:
    """
    Apply moving average to smooth out noisy week-to-week fluctuations.
    Useful for chart rendering in React dashboard.
    """
    if len(values) < window:
        return values

    smoothed = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_vals = values[start:i + 1]
        smoothed.append(round(sum(window_vals) / len(window_vals), 2))

    return smoothed


# ── Full ML Analysis for one keyword ─────────────────────────────

def analyse_keyword_ml(keyword_history: list, num_reports: int) -> dict:
    """
    Run complete ML analysis on a single keyword's history.
    Called by trend_engine for each keyword.
    """
    if not keyword_history:
        return {}

    volumes = [h["volume"] for h in keyword_history]
    shares = [h["purchase_share"] for h in keyword_history]
    price_gaps = [h["price_gap_pct"] for h in keyword_history]

    # Run all ML analyses
    volume_trend = detect_trend_pattern(volumes)
    share_trend = detect_trend_pattern(shares)
    volume_forecast = forecast_next_week(volumes)
    price_correlation = price_share_correlation(price_gaps, shares)
    volume_anomalies = detect_anomalies(volumes)
    smoothed_volumes = smooth_trend(volumes)

    return {
        "ml_active": ml_active(num_reports),
        "volume_trend": volume_trend,
        "share_trend": share_trend,
        "volume_forecast": volume_forecast,
        "price_share_correlation": price_correlation,
        "volume_anomalies": volume_anomalies,
        "smoothed_volumes": smoothed_volumes
    }