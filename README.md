# RetailIQ

**Retail Decision Intelligence Platform** — a React dashboard over a FastAPI
service and Supabase PostgreSQL, with an agentic copilot that answers business
questions from live data.

## Architecture

```
frontend/   React 19 + Vite 8 SPA
    │  fetch /api/v1/…  (same origin in every environment, JWT bearer)
    ▼
backend/    FastAPI + SQLAlchemy 2.0
    │       ├── analytics    aggregate queries
    │       ├── agents       planner → specialists → synthesis
    │       ├── RAG          pgvector + full-text hybrid retrieval
    │       └── operations   writes, stock ledger, purchase orders
    │  psycopg2 over TLS
    ▼
            Supabase PostgreSQL (transaction pooler) — 22 tables
```

The frontend never hardcodes a backend host. Vite proxies `/api` in
development; the platform rewrites `/api` in production. `VITE_API_BASE_URL`
overrides this only if the API is on a different origin.

## Running locally

**Backend**

```bash
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                        # set DATABASE_URL
python -m app.database.init_db --recreate   # schema + seed data
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                                 # http://localhost:5173
```

**Sign in**

| Account | Role | Password |
|---|---|---|
| `admin@retailiq.app` | admin — full access | `RetailIQ2026!` |
| `manager@retailiq.app` | manager — read + write | `RetailIQ2026!` |
| `analyst@retailiq.app` | analyst — read only | `RetailIQ2026!` |

API docs: <http://localhost:8000/docs>

## What the application does

| Page | Behaviour |
|---|---|
| Dashboard | KPIs, revenue trend, store and category breakdowns, top products, live alerts, and open recommendations that can be accepted or dismissed |
| Products | Catalogue with cross-store stock and computed margin; create, edit, delete, CSV export |
| Inventory | Stock health, low/dead/overstock, warehouse utilisation, category heatmap; raise purchase orders from reorder suggestions |
| Customers | Segments, spend and churn status rolled up from real sales |
| Sales Analytics | Daily / weekly / monthly revenue, profit and order series |
| Campaign Analytics | Campaign spend, ROI and channel performance |
| AI Copilot | Ask a question in natural language; specialist agents query the database and retrieve documents, and return an evidenced recommendation with per-agent traces and citations |
| Knowledge Base | Upload and search the RAG corpus (hybrid vector + full-text) |
| Reports | Generate executive/inventory/campaign/customer reports from live data; download CSV or JSON |
| Decision History | Every accepted or rejected recommendation, tracked to its outcome |
| Settings / Profile | Preferences and profile persisted per user |

**Writes are real.** Adjusting stock appends to a `stock_movements` ledger and
updates on-hand quantity in the same transaction; a sale decrements stock
atomically and rolls back entirely if any line is invalid; receiving a
purchase order restocks. Product status follows its actual stock position.

## The copilot

Not scripted. `POST /api/v1/copilot/query` plans which specialists to run from
the question's intent, each specialist calls tools that are SQL queries against
the operational tables, a knowledge agent retrieves supporting passages, and
the findings are synthesised into a root cause, evidence, impact and next
steps. Conversations and per-agent traces (tools called, timings, findings)
are persisted.

`LLM_API_KEY` is **optional**: without it the pipeline runs identically and
only the prose is composed by rules instead of a model.

## Database

22 tables: `stores`, `categories`, `products`, `inventory`, `sales`,
`sale_items`, `customers`, `campaigns`, `stock_movements`, `purchase_orders`,
`recommendations`, `decisions`, `simulations`, `reports`, `alerts`,
`conversations`, `messages`, `agent_runs`, `documents`, `document_chunks`,
`users`, `user_preferences`.

Seeded with 24 products across 5 stores, 40 customers, 8 campaigns and roughly
2,400 sales with 4,800 line items over 12 months, plus a 7-document knowledge
corpus. See `backend/README.md` for seeding and migration commands.

## Testing

```bash
cd backend && pytest -q     # 67 tests
cd frontend && npm run lint && npm run build
```

## Deployment (Vercel)

`vercel.json` builds the SPA and runs FastAPI as a Python serverless function
(`api/index.py` imports `backend/app`). `/api/v1/*`, `/health`, `/docs` and
`/openapi.json` route to the function; everything else serves the SPA.

Set these environment variables in the Vercel project:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Supabase transaction pooler (port 6543) |
| `JWT_SECRET` | yes | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | recommended | your deployed origin |
| `LLM_API_KEY` | no | enables LLM planning and narrative |
| `LLM_PROVIDER` / `LLM_MODEL` | no | `anthropic` (default) or `openai` |

No `.env` is deployed; real environment variables take precedence over the file.

## Not implemented

No payment processing, multi-tenancy, or email delivery. Report export is CSV
and JSON (not PDF). Alerts are evaluated on demand rather than on a schedule.
