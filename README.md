# FINCTRL AI

"The AI Finance Controller that investigates the books, not just reconciles them."

## Project Description

FINCTRL AI is an evidence-driven AI Finance Controller designed to reconcile financial records, investigate discrepancies, forecast cash position, validate tax lines, safely resolve high-confidence cases, and escalate uncertain cases.

## Current Development Phase

Phase 1 — Project Foundation

## Current Status

Initial project structure and development environment setup.

## Planned Architecture

FINCTRL AI is designed around a modular, multi-tier architecture:

- **React Frontend**: Single-page application for controller dashboards, reconciliation views, and investigation flows.
- **FastAPI Backend**: Asynchronous Python API providing core endpoints and service orchestration.
- **PostgreSQL Database**: Storage engine for ledger entries, bank statements, discrepancy cases, and audit trails.
- **Deterministic Financial Engine**: Rule-based matching engine for exact, rule-bound financial reconciliation.
- **Agentic AI Layer**: Multi-agent orchestration for root cause investigation, discrepancy resolution, and Q&A.
- **Tool Layer**: Specialized tools (database search, ledger lookup, document parser, calculation verification).
- **Evaluation Framework**: Benchmarking suite for reconciliation accuracy, agent reasoning quality, and regression testing.

> Note: Currently, only the Phase 1 foundation (FastAPI app shell, React/Vite app shell, and project structure) is initialized. AI features, databases, and financial engines will be implemented in subsequent development phases.
