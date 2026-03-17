from datetime import date


def detect_gap(previous_period_end: date, current_period_start: date) -> dict:
    """
    Detect if there is a gap between last uploaded report
    and current upload.

    Returns gap info and recommended handling strategy.
    """
    if previous_period_end is None:
        return {
            "has_gap": False,
            "weeks_missed": 0,
            "strategy": "NONE",
            "data_quality": "COMPLETE"
        }

    days_gap = (current_period_start - previous_period_end).days

    # Normal consecutive week = 1-3 days gap between end and next start
    if days_gap <= 3:
        return {
            "has_gap": False,
            "weeks_missed": 0,
            "strategy": "NONE",
            "data_quality": "COMPLETE"
        }

    weeks_missed = round(days_gap / 7) - 1

    # 1 week gap → interpolate
    if weeks_missed == 1:
        return {
            "has_gap": True,
            "weeks_missed": 1,
            "strategy": "INTERPOLATE",
            "data_quality": "COMPLETE",
            "message": "1 week gap detected. Trend estimated for missing week."
        }

    # 2-3 weeks gap → break trend line
    elif weeks_missed <= 3:
        return {
            "has_gap": True,
            "weeks_missed": weeks_missed,
            "strategy": "BREAK_TREND",
            "data_quality": "GAP_AFTER",
            "message": f"{weeks_missed} weeks gap detected. Trend line will show gap. Upload missing weeks for better accuracy."
        }

    # 4+ weeks gap → fresh start
    else:
        return {
            "has_gap": True,
            "weeks_missed": weeks_missed,
            "strategy": "FRESH_START",
            "data_quality": "GAP_AFTER",
            "message": f"{weeks_missed} weeks gap detected. Starting fresh baseline. Historical comparison limited."
        }