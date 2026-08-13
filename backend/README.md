# RetailIQ Backend

FastAPI backend for the RetailIQ Agentic Retail Decision Intelligence Platform.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL (Supabase)
- Pydantic v2
- python-dotenv / pydantic-settings

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entrypoint
│   ├── api/                    # HTTP routes and dependencies
│   │   ├── deps.py             # get_db dependency
│   │   └── v1/
│   │       └── router.py       # Retail data endpoints
│   ├── core/
│   │   └── config.py           # Environment configuration
│   ├── database/
│   │   ├── base.py             # Declarative base + timestamps
│   │   ├── session.py          # Engine, SessionLocal, get_db
│   │   └── init_db.py          # Table creation + optional seed
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer (placeholder)
│   ├── agents/                 # Future LangGraph agents
│   ├── copilot/                # Future AI Copilot layer
│   ├── recommendations/        # Future recommendation engine
│   └── simulation/             # Future what-if simulation
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Supabase PostgreSQL connection string:

```env
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
API_HOST=0.0.0.0
API_PORT=8000
```

> Supabase requires SSL. If needed, append `?sslmode=require` to `DATABASE_URL`.

### 4. Initialize the database

Create tables (schema only):

```bash
python -c "from app.database.init_db import initialize_database; initialize_database()"
```

Create tables and seed sample retail data:

```bash
python -m app.database.init_db
```

## Run

Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use values from `.env`:

```bash
uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API metadata |
| GET | `/health` | Health check |
| GET | `/api/v1/stores` | List stores |
| GET | `/api/v1/products` | List products |
| GET | `/api/v1/inventory` | List inventory records |
| GET | `/api/v1/sales` | List sales with items |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Development Notes

- Authentication, LangGraph agents, RAG, and LLM integrations are intentionally not implemented yet.
- Service classes are placeholder implementations ready for richer business logic.
- Future AI modules live under `app/agents`, `app/copilot`, `app/recommendations`, and `app/simulation`.
