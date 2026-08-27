# FINCTRL AI Architecture Overview

This document describes the high-level architecture for FINCTRL AI.

## Current High-Level Architecture (Phase 3)

```
+------------------------------------+
|          React Frontend            |
|       (Vite + TypeScript)          |
+------------------------------------+
                  │
                  │  HTTP / REST (GET /health, GET /health/db)
                  ▼
+------------------------------------+
|          FastAPI Backend           |
|        (Python 3.11+ App)          |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|       Database Service Layer       |
| (app.services.database_service)    |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|        PostgreSQL Database         |
|   (finctrl / 8 Operational Tables) |
+------------------------------------+
           ▲                ▲
           │                │
    [seed_database.py]   [init_db.py]
           │
+------------------------------------+
|    Phase 2 Synthetic Dataset       |
|        (data/output/*.csv)         |
+------------------------------------+
                  │
                  ▼ [NOT IMPLEMENTED YET]
+------------------------------------+
|  Future Deterministic Engine / AI  |
|  (Phase 4 Reconciliation & Agents) |
+------------------------------------+
```

## Component Status Summary

| Component | Technology | Phase | Status |
| :--- | :--- | :--- | :--- |
| Project Structure | Monorepo layout | Phase 1 | ✅ Initialized |
| FastAPI Backend | Python / FastAPI / Uvicorn | Phase 1 | ✅ Initialized (`/health`, `/health/db`) |
| React Frontend | React / Vite / TypeScript | Phase 1 | ✅ Initialized |
| Synthetic Datasets | Generator & Validators | Phase 2 | ✅ Initialized (100 cases, 9 CSVs) |
| Database Layer | PostgreSQL 18.6 / SQLAlchemy | Phase 3 | ✅ Initialized & Seeded (8 tables) |
| Deterministic Engine | Rule-based Engine | Phase 4 | ⏳ Planned |
| Evaluation Framework | Pytest / Benchmark Suite | Phase 5 | ⏳ Planned |
| Agent & Tool Layer | LangChain / Custom Agents | Phase 6 | ⏳ Planned |
| Investigation Engine | Discrepancy Analyzer | Phase 7 | ⏳ Planned |
| Human Review & Audit | Approval Workflows | Phase 8 | ⏳ Planned |
| Finance Q&A | RAG / Agent Q&A | Phase 9 | ⏳ Planned |
| Cash Forecasting | Predictive Engine | Phase 10 | ⏳ Planned |
| Tax-Line Matching | Tax Engine | Phase 11 | ⏳ Planned |
