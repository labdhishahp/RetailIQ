"""Benchmark the copilot on a freshly seeded local database.

    cd backend
    EVAL_DATABASE_URL=postgresql://user@localhost:5432/retailiq_eval \\
        python -m eval.run                       # rule baseline (+ models if a key is set)
    python -m eval.run --models claude-sonnet-5-5 --repeats 3 --questions reorder,churn

The database is dropped and re-seeded first (fixed seed), so it must be a local
throwaway: any non-local host is refused. Model runs call the provider APIs and
cost money; a model whose provider key (LLM_API_KEY for Anthropic,
OPENAI_API_KEY, GEMINI_API_KEY) is not set is skipped.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_local_database(url: str) -> bool:
    parts = urlsplit(url)
    if not parts.scheme.startswith("postgresql"):
        return False
    host = parts.hostname or ""
    socket = parse_qs(parts.query).get("host", [""])[0]
    return host in _LOCAL_HOSTS or (not host and (socket.startswith("/") or not socket))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", default=os.environ.get("EVAL_DATABASE_URL"),
                        help="Local Postgres with pgvector (default: $EVAL_DATABASE_URL).")
    parser.add_argument("--models", default=None,
                        help="Comma-separated model ids (default: all supported).")
    parser.add_argument("--baseline-only", action="store_true", help="Run only the rule baseline.")
    parser.add_argument("--questions", default=None, help="Comma-separated question ids.")
    parser.add_argument("--repeats", type=int, default=1, help="Runs per question per model.")
    parser.add_argument("--out", default=None, help="Output directory (default: eval/results/<UTC time>).")
    args = parser.parse_args(argv)

    if not args.database_url:
        parser.error("set --database-url or EVAL_DATABASE_URL to a local throwaway database")
    if not is_local_database(args.database_url):
        parser.error("refusing to re-seed a non-local database; point this at a local throwaway")

    # Settings are read at import time, so the URL must be in place first.
    os.environ["DATABASE_URL"] = args.database_url
    from app.database.init_db import SEED, initialize_database
    from app.database.session import SessionLocal
    from eval.benchmark import QUESTIONS, QUESTIONS_BY_ID
    from eval.clients import DEFAULT_MODELS, PRICING, ModelClient, RulesOnly
    from eval.harness import run_suite, to_markdown

    questions = ([QUESTIONS_BY_ID[q] for q in args.questions.split(",")]
                 if args.questions else QUESTIONS)
    models = args.models.split(",") if args.models else DEFAULT_MODELS
    unknown = [m for m in models if m not in PRICING]
    if unknown:
        parser.error(f"unsupported model id(s): {', '.join(unknown)}; supported: {', '.join(PRICING)}")

    clients, skipped = [RulesOnly()], []
    if not args.baseline_only:
        for model in models:
            client = ModelClient(model)
            if client.tool_calling_available:
                clients.append(client)
            else:
                skipped.append(model)
        if skipped:
            print(f"No API key for: {', '.join(skipped)} (skipped).")

    print("Re-seeding the evaluation database…")
    initialize_database(seed=True, recreate=True)

    db = SessionLocal()
    try:
        report = run_suite(db, clients, questions, repeats=args.repeats)
    finally:
        db.close()

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    report["meta"] = {
        "run_at": datetime.now(timezone.utc).isoformat(), "git_commit": commit, "seed": SEED,
        "questions": [q.id for q in questions], "repeats": args.repeats,
        "models": [c.model for c in clients], "skipped_models": skipped,
        "pricing_usd_per_mtok": {m: PRICING[m] for m in models},   # None = unknown
        "definitions": {q.id: {"question": q.text, "ground_truth": q.definition,
                               "required_tools": sorted(q.required_tools)} for q in questions},
    }

    out = Path(args.out or Path(__file__).parent / "results" /
               datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(report, indent=2, default=str))
    summary = to_markdown(report)
    (out / "summary.md").write_text(summary)
    print(summary)
    print(f"Wrote {out / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
