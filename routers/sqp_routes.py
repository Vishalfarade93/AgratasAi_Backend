from fastapi import APIRouter, UploadFile, File, Depends, Form
from sqlalchemy.orm import Session
from database.db import get_db
from core.dependencies import get_current_seller
from models.sqp_model import Seller, SqpReport, SqpBrandKeyword
from services.upload_service import process_upload
from services.analytics.metrics_engine import calculate_metrics
from services.analytics.trend_engine import get_keyword_trends
from services.analytics.aggregation_engine import get_aggregated_view
from services.insights.ai_engine import generate_insights

router = APIRouter()


@router.post("/upload/sqp")
async def upload_sqp(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
    return process_upload(file=file.file, seller_id=current_seller.id, db=db)


@router.get("/analytics/latest")
def get_latest_analytics(db: Session = Depends(get_db), current_seller: Seller = Depends(get_current_seller)):
    latest_report = db.query(SqpReport).filter(
        SqpReport.seller_id == current_seller.id
    ).order_by(SqpReport.period_start.desc()).first()

    if not latest_report:
        return {"success": False, "message": "No reports found. Please upload your first SQP CSV."}

    keywords = db.query(SqpBrandKeyword).filter(SqpBrandKeyword.report_id == latest_report.id).all()
    metrics = calculate_metrics(keywords)

    return {
        "success": True,
        "seller_id": current_seller.id,
        "report_id": latest_report.id,
        "period_start": str(latest_report.period_start),
        "period_end": str(latest_report.period_end),
        "data_quality": latest_report.data_quality,
        "metrics": metrics
    }


@router.get("/analytics/trends")
def get_trends(
    range_filter: str = "6weeks",
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
    """
    filter options:
      6weeks     → latest 6 weeks (default)
      4weeks     → latest 4 weeks
      8weeks     → latest 8 weeks
      this_month → current calendar month
      last_month → previous calendar month
      all        → all available data
    """
    return get_keyword_trends(seller_id=current_seller.id, db=db, filter_type=range_filter)


@router.get("/analytics/monthly")
def get_monthly_view(db: Session = Depends(get_db), current_seller: Seller = Depends(get_current_seller)):
    return get_aggregated_view(seller_id=current_seller.id, view_type="MONTHLY", db=db)


@router.get("/analytics/quarterly")
def get_quarterly_view(db: Session = Depends(get_db), current_seller: Seller = Depends(get_current_seller)):
    return get_aggregated_view(seller_id=current_seller.id, view_type="QUARTERLY", db=db)


@router.get("/reports")
def get_reports(db: Session = Depends(get_db), current_seller: Seller = Depends(get_current_seller)):
    reports = db.query(SqpReport).filter(
        SqpReport.seller_id == current_seller.id
    ).order_by(SqpReport.period_start.desc()).all()

    return {
        "success": True,
        "seller_id": current_seller.id,
        "total_reports": len(reports),
        "reports": [
            {
                "report_id": r.id,
                "period_start": str(r.period_start),
                "period_end": str(r.period_end),
                "period_type": r.period_type,
                "data_quality": r.data_quality,
                "data_source": r.data_source,
                "uploaded_at": str(r.uploaded_at)
            }
            for r in reports
        ]
    }


@router.get("/insights")
def get_insights(
    range_filter: str = "6weeks",
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
    latest_report = db.query(SqpReport).filter(
        SqpReport.seller_id == current_seller.id
    ).order_by(SqpReport.period_start.desc()).first()

    if not latest_report:
        return {"success": False, "message": "No reports found"}

    keywords = db.query(SqpBrandKeyword).filter(SqpBrandKeyword.report_id == latest_report.id).all()
    metrics  = calculate_metrics(keywords)
    trends   = get_keyword_trends(seller_id=current_seller.id, db=db, filter_type=range_filter)

    return generate_insights(
        seller_id=current_seller.id,
        metrics=metrics,
        trends=trends if trends.get("success") else {}
    )