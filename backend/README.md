# RetailIQ Backend

FastAPI + SQLAlchemy service over Supabase PostgreSQL, providing the analytics,
agentic copilot, RAG retrieval and operational write APIs.

## Stack

Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · psycopg2 · pgvector ·
PyJWT · Alembic · pytest

## Layout

```
backend/app/
├── main.py                    # app factory, CORS, error handlers, /health
├── api/
│   ├── deps.py                # get_db, get_current_user, role guards
│   └── v1/
│       ├── router.py          # entity + analytics endpoints
│       └── routes/            # auth, copilot, insights, operations
├── agents/
│   ├── tools.py               # the tool surface agents may call (all hit the DB)
│   ├── base.py                # Agent, Finding, AgentResult
│   ├── specialists.py         # sales, inventory, pricing, campaign, customer, store, knowledge
│   ├── planner.py             # intent -> agent plan (LLM or rules)
│   └── orchestrator.py        # runs the plan, synthesises the result
├── core/                      # settings, password hashing, JWT
├── database/                  # base, session, init_db, seed_knowledge
├── models/                    # 22 ORM models
├── schemas/                   # request/response models
└── services/                  # analytics, rag, embedding, llm, recommendations,
                               # simulation, alerts, reports, operations, cache
```

## Setup

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL
python -m app.database.init_db --recreate
uvicorn app.main:app --reload --port 8000
```

Sign in with `admin@retailiq.app` / `RetailIQ2026!` (also `manager@` and
`analyst@`, same password).

## Security

- JWT access + refresh tokens; passwords hashed with PBKDF2-HMAC-SHA256
  (240k iterations, per-password salt) from the standard library, so there is
  no binary wheel dependency on the serverless runtime.
- Three roles: `analyst` (read), `manager` (read + write), `admin` (+ user
  management). Every endpoint is authenticated; writes require manager.
- Database errors return a generic 503 — driver text can contain the
  connection string and is only logged.

## The copilot

`POST /api/v1/copilot/query` runs a real pipeline:

1. **Planner** picks specialists from the question's intent and extracts a
   focus term by matching against actual product and category names.
2. **Specialists** each call tools in `agents/tools.py`. Every tool is a SQL
   query against the operational tables, so findings always cite real numbers.
3. **Knowledge agent** retrieves supporting passages from the document corpus.
4. **Synthesis** ranks findings by relevance to the question, then severity,
   and composes the root cause, evidence, impact and next steps.

Conversations, messages and per-agent traces (tools called, duration,
findings) are persisted.

**`LLM_API_KEY` is optional.** Without it, planning uses an intent classifier
and synthesis uses the rule composer — the data analysis is identical either
way. With a key, the LLM handles planning and narrative on top of the same
findings.

## RAG

Documents are chunked, embedded and stored in `document_chunks.embedding`
(`pgvector`, 384 dims). Retrieval is **hybrid**: vector cosine distance fused
with Postgres full-text ranking via reciprocal rank fusion.

Embeddings are computed locally (`services/embedding.py`) from hashed word
unigrams, bigrams and character 4-grams with sub-linear weighting, L2
normalised. This was chosen over a hosted embedding API or a transformer so
retrieval works with no API key and no large dependency; the trade-off is
lexical rather than deep semantic matching, which is why retrieval is hybrid.

## Endpoints

Auth: `POST /auth/login`, `/auth/refresh`, `GET|PATCH /auth/me`,
`POST /auth/me/password`, `GET|PUT /auth/me/preferences`,
`GET|POST /auth/users` (admin).

Entities: `stores`, `products`, `inventory`, `sales`, `customers`, `campaigns`
(+ single-item lookups).

Analytics: `kpis`, `revenue-trend`, `monthly-sales`, `sales?period=`,
`store-comparison`, `category-sales`, `top-products`, `products-overview`,
`inventory-overview`, `inventory-trend`, `campaign-performance`.

Copilot: `POST /copilot/query`, conversations CRUD, `GET /copilot/search`,
documents CRUD, `GET /copilot/knowledge-stats`.

Intelligence: recommendations (list / generate / action), decisions,
`POST /simulations/run`, alerts (list / evaluate / read), reports
(list / generate / download as CSV or JSON).

Operations: product create/update/delete, `POST /inventory/adjust`,
`PATCH /inventory/{id}`, `GET /stock-movements`, `POST /sales`,
purchase orders (create / receive).

Interactive docs at `/docs`.

## Derived metrics

Figures with no column behind them are derived; each derivation is documented
at its method:

- **healthScore** — equal-weight composite of margin ratio, fill rate and
  order-growth momentum.
- **heatmap / inventory trend** — historical stock is reconstructed by adding
  units sold after each week onto current on-hand, for periods predating the
  `stock_movements` ledger.
- **daysLeft / days_cover** — on-hand ÷ 90-day average daily sales, capped 99.
- **dead stock** — on hand with no sale in 60 days.
- **elasticity** — regressed from the product's own monthly price/volume
  history when there are ≥3 distinct price points, else a category default.
  Each simulated product reports which source was used.

## Performance

Analytics responses are cached in-process (`ANALYTICS_CACHE_SECONDS`, default
60) and the cache is flushed on every write. The dashboard's 15-call fan-out
takes ~3s cold and ~1.4s warm; before caching and the set-based rewrite of the
weekly loops it exceeded two minutes.

## Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

`init_db --recreate` remains available for rebuilding a demo database from
scratch. Use migrations for schema changes to an existing one — `create_all`
never ALTERs an existing table.

## Tests

```bash
pytest -q          # 67 tests
```

Tests run against a throwaway schema in the same PostgreSQL database, created
via SQLAlchemy's `schema_translate_map` (the Supabase pooler is transaction-mode
and does not preserve `search_path`). Application data is never touched, and
the schema is dropped afterwards.

Coverage: password hashing, JWT issuing/expiry/misuse, role enforcement,
endpoint auth, product CRUD, the stock ledger, oversell prevention, sale
atomicity and rollback, purchase-order lifecycle, embeddings, hybrid
retrieval, every agent tool, planner routing, investigation grounding,
simulation monotonicity, and recommendation rules.

## Seeding

```bash
python -m app.database.init_db              # seed only if empty
python -m app.database.init_db --reset      # clear seeded rows, re-seed
python -m app.database.init_db --recreate   # drop + recreate tables, re-seed
```

Seeds 5 stores, 6 categories, 24 products, ~95 inventory rows, 40 customers,
8 campaigns, ~2,400 sales with ~4,800 line items over 12 months, 3 users,
7 knowledge documents, and runs the first recommendation and alert sweeps.
Random generation is seeded with a fixed value, so the dataset is reproducible.
Customer spend, segment and churn status are rolled up from their real sales;
product status is derived from actual stock; a share of sale lines transact
below list price so margin analysis has genuine signal.
