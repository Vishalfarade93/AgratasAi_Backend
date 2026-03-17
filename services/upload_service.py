from sqlalchemy.orm import Session
from models.sqp_model import SqpReport, SqpBrandKeyword
from services.ingestion.csv_parser import parse_csv
from services.analytics.gap_detector import detect_gap
from services.analytics.metrics_engine import calculate_metrics


def process_upload(file, seller_id: int, db: Session) -> dict:
    """
    Complete upload pipeline:
    1. Parse CSV
    2. Validate
    3. Detect gaps
    4. Store report + keywords
    5. Run metrics automatically
    """

    # Step 1: Parse CSV
    parsed = parse_csv(file)
    if not parsed["success"]:
        return parsed

    period_start = parsed["period_start"]
    period_end = parsed["period_end"]

    # Step 2: Check for duplicate report
    existing = db.query(SqpReport).filter(
        SqpReport.seller_id == seller_id,
        SqpReport.report_type == "BRAND",
        SqpReport.period_start == period_start,
        SqpReport.period_end == period_end
    ).first()

    if existing:
        return {
            "success": False,
            "error": "Report already exists for this period",
            "existing_report_id": existing.id
        }

    # Step 3: Find previous report and detect gap
    previous_report = db.query(SqpReport).filter(
        SqpReport.seller_id == seller_id,
        SqpReport.report_type == "BRAND",
        SqpReport.period_start < period_start
    ).order_by(SqpReport.period_start.desc()).first()

    gap_info = detect_gap(
        previous_period_end=previous_report.period_end if previous_report else None,
        current_period_start=period_start
    )

    # Step 4: Create report record
    report = SqpReport(
        seller_id=seller_id,
        report_type="BRAND",
        period_type="WEEKLY",
        period_start=period_start,
        period_end=period_end,
        data_quality=gap_info["data_quality"],
        data_source="MANUAL_CSV"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Step 5: Mark previous report as GAP_AFTER if gap detected
    if gap_info["has_gap"] and previous_report:
        previous_report.data_quality = "GAP_AFTER"
        db.commit()

    # Step 6: Insert all keyword rows
    for row in parsed["rows"]:
        keyword = SqpBrandKeyword(
            report_id=report.id,
            **row
        )
        db.add(keyword)

    db.commit()

    # Step 7: Auto run metrics on this report
    keywords = db.query(SqpBrandKeyword).filter(
        SqpBrandKeyword.report_id == report.id
    ).all()

    metrics = calculate_metrics(keywords)

    # Step 8: Build response
    response = {
        "success": True,
        "report_id": report.id,
        "period_start": str(period_start),
        "period_end": str(period_end),
        "keywords_stored": parsed["total_rows"],
        "data_quality": gap_info["data_quality"],
        "metrics": metrics
    }

    # Add gap warning if detected
    if gap_info["has_gap"]:
        response["gap_warning"] = gap_info.get("message")

    return response