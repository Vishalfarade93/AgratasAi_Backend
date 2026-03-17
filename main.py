from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import engine, Base
import models.sqp_model
from routers import sqp_routes, auth_routes

app = FastAPI(
    title="Agratas AI",
    description="Amazon SQP Market Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_routes.router)
app.include_router(sqp_routes.router)


@app.get("/")
def home():
    return {
        "message": "Agratas AI Backend Running",
        "version": "1.0.0",
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "upload": "POST /upload/sqp",
            "latest_analytics": "GET /analytics/latest",
            "trends": "GET /analytics/trends",
            "monthly": "GET /analytics/monthly",
            "quarterly": "GET /analytics/quarterly",
            "reports": "GET /reports",
            "insights": "GET /insights"
        }
    }