from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from database.db import Base


class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    brand_name = Column(String(100))
    created_at = Column(DateTime, default=func.now())


class SqpReport(Base):
    __tablename__ = "sqp_reports"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    report_type = Column(String(20), default="BRAND")
    period_type = Column(String(20))          # WEEKLY
    period_start = Column(Date)
    period_end = Column(Date)
    data_quality = Column(String(20), default="COMPLETE")   # COMPLETE, GAP_AFTER
    data_source = Column(String(20), default="MANUAL_CSV")  # MANUAL_CSV, SP_API (future)
    uploaded_at = Column(DateTime, default=func.now())


class SqpBrandKeyword(Base):
    __tablename__ = "sqp_brand_keywords"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sqp_reports.id"))
    search_query = Column(String(255))
    search_query_score = Column(Integer)
    search_query_volume = Column(Integer)
    reporting_date = Column(Date)
    impressions_total = Column(Integer)
    impressions_brand = Column(Integer)
    impressions_brand_share = Column(Float)
    clicks_total = Column(Integer)
    clicks_click_rate = Column(Float)
    clicks_brand = Column(Integer)
    clicks_brand_share = Column(Float)
    clicks_price_median = Column(Float)
    clicks_brand_price_median = Column(Float)
    cart_adds_total = Column(Integer)
    cart_adds_rate = Column(Float)
    cart_adds_brand = Column(Integer)
    cart_adds_brand_share = Column(Float)
    purchases_total = Column(Integer)
    purchases_rate = Column(Float)
    purchases_brand = Column(Integer)
    purchases_brand_share = Column(Float)
    purchases_price_median = Column(Float)