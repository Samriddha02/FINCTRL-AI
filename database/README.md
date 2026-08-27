# FINCTRL AI Database & Data Layer

## Purpose
This directory and associated backend modules manage the PostgreSQL database schema, SQLAlchemy ORM models, data ingestion, database services, and schema verification for FINCTRL AI.

---

## Environment & Connection

- **Database Engine**: PostgreSQL 18.6
- **Database Name**: `finctrl`
- **Database User**: `postgres`
- **Host / Port**: `localhost:5432`
- **Connection URI Format** (configured in `.env`):
  ```env
  DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/finctrl
  ```

---

## Schema & Operational Tables (8 Total)

1. **`customers`**: Customer master records (`customer_id`, `customer_name`, `email`, `created_at`).
2. **`orders`**: E-commerce / POS sales orders (`order_id`, `customer_id`, `order_amount`, `currency`, `order_status`, `created_at`).
3. **`payments`**: Payment gateway transactions (`payment_id`, `order_id`, `customer_id`, `amount`, `currency`, `payment_method`, `payment_status`, `created_at`).
4. **`refunds`**: Payment refund records (`refund_id`, `payment_id`, `refund_amount`, `refund_reason`, `refund_status`, `created_at`).
5. **`settlements`**: Gateway payout settlements (`settlement_id`, `payment_id`, `gross_amount`, `fee_amount`, `tax_amount`, `adjustment_amount`, `net_amount`, `settlement_status`, `settlement_date`).
6. **`bank_transactions`**: Bank statement credit records (`bank_txn_id`, `reference_id`, `amount`, `transaction_type`, `description`, `transaction_date`).
7. **`invoices`**: Tax invoices (`invoice_id`, `order_id`, `customer_id`, `subtotal`, `tax_rate`, `tax_amount`, `total_amount`, `invoice_status`, `invoice_date`).
8. **`tax_records`**: Tax ledger entries (`tax_id`, `invoice_id`, `tax_type`, `taxable_amount`, `tax_rate`, `tax_amount`, `filing_period`, `recorded_at`).

---

## Ground Truth Isolation

> **CRITICAL ARCHITECTURAL RULE:**
> `ground_truth.csv` is evaluation-only metadata. It is **NOT** created as a PostgreSQL table, **NOT** ingested by `seed_database.py`, and **NOT** accessible via any database service or operational API endpoint.

---

## Instructions & Management Commands

All commands are run from the project root using the Python virtual environment:

### 1. Initialize Database Tables
Creates all 8 operational tables in PostgreSQL:
```bash
python backend/scripts/init_db.py
```

### 2. Seed Database
Ingests Phase 2 CSV data into PostgreSQL inside a safe database transaction (idempotent, skips existing business IDs on repeated runs):
```bash
python backend/scripts/seed_database.py
```

### 3. Verify Database Setup
Runs schema inspection, row count comparison, monetary precision check, and ground truth isolation verification:
```bash
python backend/scripts/verify_database.py
```

### 4. Run Test Suite
Runs all Phase 1, Phase 2, and Phase 3 integration tests:
```bash
pytest tests/
```
