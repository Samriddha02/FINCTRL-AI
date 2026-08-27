# FINCTRL AI — Backend Service

FastAPI service powering FINCTRL AI.

## Getting Started

### Prerequisites
- Python 3.11+
- Virtual environment activated (`.venv`)

### Running locally

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

Or from project root:

```bash
uvicorn backend.app.main:app --reload
```

### Endpoints

- `GET /health` — Service health check
- `GET /docs` — Interactive OpenAPI swagger documentation
