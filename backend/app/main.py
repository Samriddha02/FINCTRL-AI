from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.reconciliation import router as reconciliation_router

app = FastAPI(
    title="FINCTRL AI",
    description="The AI Finance Controller that investigates the books, not just reconciles them.",
    version="0.5.0",
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


@app.get("/")
def read_root():
    return {
        "message": "Welcome to FINCTRL AI API",
        "docs": "/docs",
        "health": "/health",
        "health_db": "/health/db",
        "reconciliation": "/api/reconciliation",
    }
