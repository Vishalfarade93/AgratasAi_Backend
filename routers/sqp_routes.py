from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from database.db import get_db
from core.dependencies import get_current_seller
from models.sqp_model import Seller, SqpReport, SqpBrandKeyword
from services.upload_service import process_upload
from services.analytics.metrics_engine import calculate_metrics
from services.analytics.trend_engine import get_keyword_trends
from services.analytics.aggregation_engine import get_aggregated_view
from services.insights.ai_engine import generate_insights
from services.analytics.keyword_service import get_keyword_detail  # <-- correct import

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

    keywords = db.query(SqpBrandKeyword).filter(
        SqpBrandKeyword.report_id == latest_report.id).all()
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
    range_filter: str = Query(
        "6weeks", description="Filter: 4weeks,6weeks,8weeks,this_month,last_month,all"),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
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
    range_filter: str = Query("6weeks", description="Filter for trends"),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
    latest_report = db.query(SqpReport).filter(
        SqpReport.seller_id == current_seller.id
    ).order_by(SqpReport.period_start.desc()).first()

    if not latest_report:
        return {"success": False, "message": "No reports found"}

    keywords = db.query(SqpBrandKeyword).filter(
        SqpBrandKeyword.report_id == latest_report.id).all()
    metrics = calculate_metrics(keywords)
    trends = get_keyword_trends(
        seller_id=current_seller.id, db=db, filter_type=range_filter)

    return generate_insights(
        seller_id=current_seller.id,
        metrics=metrics,
        trends=trends if trends.get("success") else {}
    )


@router.get("/keyword/detail")
def get_keyword_detail_endpoint(
    search_query: str = Query(..., description="The keyword to analyze"),
    filter_type: str = Query(
        "6weeks", description="Time filter: 4weeks,6weeks,8weeks,this_month,last_month,all"),
    db: Session = Depends(get_db),
    current_seller: Seller = Depends(get_current_seller)
):
    return get_keyword_detail(current_seller.id, search_query, filter_type, db)
