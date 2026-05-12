# Gym management — BLM3722

Python **FastAPI** app with **SQLite** (`gym.db` — one file, no server setup).

**Full project context** (UML, traceability, course-oriented detail): [`docs/MODEL_REFERENCE.md`](docs/MODEL_REFERENCE.md) — **English**.

## Setup

```powershell
cd c:\Users\cmsrb\Desktop\Projects\yazmuh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Run

```powershell
python -m uvicorn gym_management.main:app --reload
```

- **Web UI:** http://127.0.0.1:8000/ui/  
- **REST docs (Swagger):** http://127.0.0.1:8000/docs  
- **OpenAPI JSON:** http://127.0.0.1:8000/openapi.json  

**Database:** SQLite file `gym.db` in the folder you run the app from (usually the project root). Delete that file to reset all data; on next start the app recreates the schema and runs **seed** when the package catalog is empty ([`seed.py`](src/gym_management/infrastructure/seed.py)): sample members (realistic-style emails), mixed **monthly / multi-month / yearly** subscription packages, payments, ~18 equipment rows, maintenance/repairs, and budget lines aligned to seeded totals. If you add ORM columns (e.g. `billing_cycle_months`), delete `gym.db` once so `create_schema()` rebuilds tables.

**Web UI highlights:** Dashboard shows health reports expiring in the **next 30 days** (not already expired); members table shows **active** package only; equipment page uses compact expandable rows; package form includes **billing period** (1 / 3 / 6 / 12 months).

## Tests

```powershell
pytest -q
```
