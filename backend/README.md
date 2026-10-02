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
│   ├── base.py                # Agent, Finding, AgentResult, grounding check
│   ├── runtime.py             # model tool loop: call, observe, continue, conclude
│   ├── specialists.py         # sales, inventory, pricing, campaign, customer, store, knowledge
│   ├── planner.py             # first-round routing and focus extraction (rules)
│   └── orchestrator.py        # lead investigator: delegates, follows up, concludes
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

`POST /api/v1/copilot/query` runs an investigation:

1. **Lead investigator** (`orchestrator.py`) delegates to specialists with an
   objective and optional product focus, reads what they report, and decides
   whether to send follow-ups before concluding.
2. **Specialists** (`specialists.py`) each own a toolset from `agents/tools.py`
   — every tool is a SQL query with a strict JSON schema — and choose their
   next call from the previous result: e.g. Sales finds the worst-declining
   product, then `product_drilldown` separates a demand, price, stock or
   single-store cause. Calls outside an agent's toolset are refused.
3. **Grounding**: every number in a finding is checked against that agent's
   tool output (`verified: true/false`); unverified claims in the conclusion
   are listed in `trace.unverifiedClaims`.
4. **Synthesis**: confidence, revenue and inventory impact are always computed
   from tool output; the narrative comes from the lead's conclusion, with any
   missing or malformed field filled by the rule composer.

The response includes `trace` (mode, each delegation with its round and
reason, tool-call and token counts) and per-agent `steps` (tool, arguments,
result summary, timing). Per-agent runs are persisted in `agent_runs`.

**Two modes, same agents.** With an Anthropic `LLM_API_KEY` the lead and the
specialists are model tool loops (`runtime.py`, default `claude-opus-5-5`,
server-side refusal fallback on), bounded by `AGENT_DEADLINE_SECONDS`,
`AGENT_MAX_TURNS`, `LEAD_MAX_TURNS` and `LEAD_MAX_DELEGATIONS`; parallel
delegations run concurrently on separate sessions. Without a key — or if the
model is unreachable — the lead and specialists run on rule policies that are
also observation-driven: round 2 is chosen from the leads round 1 raised, and
the knowledge search is phrased from what was found.

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
