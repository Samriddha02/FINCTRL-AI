# FINCTRL AI Architecture Overview

This document describes the high-level architecture for FINCTRL AI.

## Current High-Level Architecture (Phase 5)

```
+------------------------------------+
|          React Frontend            |
|       (Vite + TypeScript)          |
+------------------------------------+
                  │
                  │  HTTP / REST (/health, /health/db, /api/reconciliation)
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
                  │
                  ▼
+------------------------------------+
| Deterministic Reconciliation Engine|
|   (app.reconciliation.engine)      |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|    Structured Result & Evidence    |
|   (ReconciliationResult Pydantic)  |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|   Evaluation & Benchmark Layer     |
|     (app.evaluation.evaluator)     |
+------------------------------------+
                  |
                  v 
+------------------------------------+
|     AI Investigation & Agent       |
|    (app.agents.controller)         |
|  Facts -> Evidence -> Explanation  |
+------------------------------------+
```

## Component Status Summary

| Component | Technology | Phase | Status |
| :--- | :--- | :--- | :--- |
| Project Structure | Monorepo layout | Phase 1 | ✅ Initialized |
| FastAPI Backend | Python / FastAPI / Uvicorn | Phase 1 | ✅ Initialized (`/health`, `/health/db`, `/api/reconciliation`) |
| React Frontend | React / Vite / TypeScript | Phase 1 | ✅ Initialized |
| Synthetic Datasets | Generator & Validators | Phase 2 | ✅ Initialized (100 cases, 9 CSVs) |
| Database Layer | PostgreSQL 18.6 / SQLAlchemy | Phase 3 | ✅ Initialized & Seeded (8 tables) |
| Deterministic Engine | Rule-based Engine | Phase 4 | ✅ Initialized (100.0% Benchmark Accuracy) |
| Evaluation Framework | Pytest / Benchmark Suite | Phase 5 | ✅ Initialized (Multi-seed evaluation, 100% accuracy) |
| Agent & Tool Layer | Custom State Machine Agent | Phase 6 | ✅ Initialized (LLM/Mock providers, validator) |
| Investigation Engine | Discrepancy Analyzer | Phase 7 | Done (Integrated in Phase 6/8) |
| Human Review & Audit | Approval Workflows & Immutable Audit | Phase 8 | Done (`/api/reviews`, `/api/audit`, policy & verification) |
| Finance Q&A | RAG / Grounded Finance Assistant | Phase 9 | Done (`/api/finance/qa`, fact-first & validation) |
| Cash Forecasting | Deterministic Cash Forecasting Engine | Phase 10 | Done (`/api/forecast/cash`, uncertainty & risk-aware) |
| Tax-Line Matching | Deterministic Tax Control Engine | Phase 11 | Done (`/api/tax-matching`, precedence-based rules & evidence) |
