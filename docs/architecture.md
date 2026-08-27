# FINCTRL AI Architecture Overview

This document describes the high-level architecture for FINCTRL AI.

## Current High-Level Architecture (Phase 1)

```
+------------------------------------+
|          React Frontend            |
|       (Vite + TypeScript)          |
+------------------------------------+
                  │
                  │  HTTP / REST (GET /health)
                  ▼
+------------------------------------+
|          FastAPI Backend           |
|        (Python 3.11+ App)          |
+------------------------------------+
                  │
                  ▼ [NOT IMPLEMENTED YET]
+------------------------------------+
|    Future Application Services     |
| (Reconciliation, Forecasting, Tax) |
+------------------------------------+
                  │
                  ▼ [NOT IMPLEMENTED YET]
+------------------------------------+
|  Future Database / AI / Tool Layers|
| (PostgreSQL, Agents, Tools, Eval)  |
+------------------------------------+
```

## Component Status Summary

| Component | Technology | Phase | Status |
| :--- | :--- | :--- | :--- |
| Project Structure | Monorepo layout | Phase 1 | ✅ Initialized |
| FastAPI Backend | Python / FastAPI / Uvicorn | Phase 1 | ✅ Initialized (`/health`) |
| React Frontend | React / Vite / TypeScript | Phase 1 | ✅ Initialized |
| Synthetic Datasets | Generator Scripts | Phase 2 | ⏳ Planned |
| Database Layer | PostgreSQL / SQLAlchemy | Phase 3 | ⏳ Planned |
| Deterministic Engine | Rule-based Engine | Phase 4 | ⏳ Planned |
| Evaluation Framework | Pytest / Benchmark Suite | Phase 5 | ⏳ Planned |
| Agent & Tool Layer | LangChain / Custom Agents | Phase 6 | ⏳ Planned |
| Investigation Engine | Discrepancy Analyzer | Phase 7 | ⏳ Planned |
| Human Review & Audit | Approval Workflows | Phase 8 | ⏳ Planned |
| Finance Q&A | RAG / Agent Q&A | Phase 9 | ⏳ Planned |
| Cash Forecasting | Predictive Engine | Phase 10 | ⏳ Planned |
| Tax-Line Matching | Tax Engine | Phase 11 | ⏳ Planned |
