from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.reconciliation import router as reconciliation_router
from app.api.investigations import router as investigations_router
from app.api.reviews import router as reviews_router
from app.api.audit import router as audit_router
from app.api.finance_qa import router as finance_qa_router
from app.api.forecast import router as forecast_router
from app.api.tax_matching import router as tax_matching_router

app = FastAPI(
    title="FINCTRL AI",
    description="The AI Finance Controller that investigates the books, not just reconciles them.",
    version="0.11.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(reconciliation_router)
app.include_router(investigations_router)
app.include_router(reviews_router)
app.include_router(audit_router)
app.include_router(finance_qa_router)
app.include_router(forecast_router)
app.include_router(tax_matching_router)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to FINCTRL AI API",
        "docs": "/docs",
        "health": "/health",
        "health_db": "/health/db",
        "reconciliation": "/api/reconciliation",
        "investigations": "/api/investigations/{case_id}",
        "human_review": "/api/reviews",
        "audit": "/api/audit",
        "finance_qa": "/api/finance/qa",
        "cash_forecast": "/api/forecast/cash",
        "tax_matching": "/api/tax-matching"
    }
