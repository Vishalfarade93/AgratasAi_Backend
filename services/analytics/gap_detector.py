from datetime import date


def detect_gap(previous_period_end: date, current_period_start: date) -> dict:
    """
    Detect if there is a gap between last uploaded report
    and current upload.

    Weekly report structure:
      period_start = reporting date (e.g. 2024-10-06)
      period_end   = period_start + 6 days (e.g. 2024-10-12)

    So consecutive weeks look like:
      Week 1: start=Oct 06, end=Oct 12
      Week 2: start=Oct 13, end=Oct 19
      days_gap between Oct 12 → Oct 13 = 1 day  ← COMPLETE

    We allow up to 10 days to handle any slight irregularity.
    """

    if previous_period_end is None:
        return {
            "has_gap":     False,
            "weeks_missed": 0,
            "strategy":    "NONE",
            "data_quality": "COMPLETE"
        }

    days_gap = (current_period_start - previous_period_end).days

    # Consecutive week — 1 day gap (end of week 1 to start of week 2)
    # Allow up to 10 days for any slight irregularity
    if days_gap <= 10:
        return {
            "has_gap":      False,
            "weeks_missed": 0,
            "strategy":     "NONE",
            "data_quality": "COMPLETE"
        }

    weeks_missed = round(days_gap / 7) - 1

    # 1 week gap → interpolate, still mark COMPLETE
    if weeks_missed == 1:
        return {
            "has_gap":      True,
            "weeks_missed": 1,
            "strategy":     "INTERPOLATE",
            "data_quality": "COMPLETE",
            "message":      "1 week gap detected. Trend estimated for missing week."
        }

    # 2-3 weeks gap → break trend line
    elif weeks_missed <= 3:
        return {
            "has_gap":      True,
            "weeks_missed": weeks_missed,
            "strategy":     "BREAK_TREND",
            "data_quality": "GAP_AFTER",
            "message":      f"{weeks_missed} weeks gap detected. Trend line will show gap. Upload missing weeks for better accuracy."
        }

    # 4+ weeks gap → fresh start
    else:
        return {
            "has_gap":      True,
            "weeks_missed": weeks_missed,
            "strategy":     "FRESH_START",
            "data_quality": "GAP_AFTER",
            "message":      f"{weeks_missed} weeks gap detected. Starting fresh baseline. Historical comparison limited."
        }