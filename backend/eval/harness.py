"""Runs the benchmark for each client and aggregates the scores."""

import time
from statistics import mean

from sqlalchemy.orm import Session

from app.agents.orchestrator import investigate
from eval.benchmark import Question
from eval.clients import cost_usd
from eval.scoring import score


def model_mismatch(requested: str, served: dict) -> bool:
    """Any call answered by a different model (a dated snapshot of the same id
    is the same model) invalidates that run's comparison."""
    return any(m != requested and not m.startswith(f"{requested}-") for m in served)


def response_record(result: dict) -> dict:
    """The investigation itself, saved next to its scores so model answers can
    be read side by side. Taken verbatim from the investigate() result."""
    trace = result.get("trace", {})
    return {
        "conclusion": {k: result.get(k) for k in (
            "rootCause", "businessImpact", "riskLevel", "priority", "confidence",
            "revenueImpact", "inventoryImpact", "synthesis")},
        "recommendation": {"action": result.get("suggestedCampaign"),
                           "nextSteps": result.get("nextSteps", [])},
        "evidence": result.get("evidence", []),
        "rounds": result.get("plan", {}).get("rounds"),
        "decisions": trace.get("decisions", []),          # who was sent, in which round, and why
        "agents": [
            {k: a.get(k) for k in ("id", "agent", "round", "objective", "mode", "fallback",
                                   "severity", "duration", "findings", "toolsCalled", "steps")}
            for a in result.get("agents", [])
        ],
        "tools_called": [s["tool"] for a in result.get("agents", [])
                         for s in a.get("steps", []) if s.get("ok")],
        "citations": [c.get("title") for c in result.get("citations", [])],
        "trace": {k: trace.get(k) for k in ("mode", "delegations", "toolCalls", "llmTurns",
                                             "tokens", "unverifiedClaims", "fallback")},
        "elapsed_ms": result.get("elapsedMs"),
    }


def run_suite(db: Session, clients: list, questions: list[Question], *, repeats: int = 1) -> dict:
    """Ground truth is computed once per question, before any agent runs."""
    truths = {q.id: q.truth(db) for q in questions}
    rows = []
    for client in clients:
        expect_llm = client.tool_calling_available
        for q in questions:
            for attempt in range(1, repeats + 1):
                client.reset()
                started = time.perf_counter()
                try:
                    result = investigate(db, q.text, llm=client)
                    row = score(q, truths[q.id], result, expect_llm=expect_llm)
                    row["response"] = response_record(result)
                except Exception as exc:  # noqa: BLE001 - an errored run is a result
                    row = {"question": q.id, "completion": "error", "correct": False,
                           "error": f"{type(exc).__name__}: {exc}"[:300], "response": None}
                finally:
                    db.rollback()   # investigations without a conversation write nothing
                usage = client.usage()
                row.update({
                    "model": client.model, "question_text": q.text, "attempt": attempt,
                    "wall_ms": int((time.perf_counter() - started) * 1000),
                    "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
                    "cache_read_input_tokens": usage["cache_read_input_tokens"],
                    "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
                    "llm_calls": usage["calls"], "llm_errors": usage["errors"],
                    "served_models": usage["served_models"],
                    "cost_usd": (0.0 if client.model == "rules"
                                 else cost_usd(client.model, usage["input_tokens"], usage["output_tokens"])),
                })
                row["model_mismatch"] = model_mismatch(client.model, usage["served_models"])
                rows.append(row)
    return {"truth": {qid: {"entities": [e.key for e in t.entities], "number": t.number,
                            "detail": t.detail} for qid, t in truths.items()},
            "rows": rows, "summary": summarise(rows)}


def _avg(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(mean(values), 3) if values else None


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    for model in dict.fromkeys(r["model"] for r in rows):
        mine = [r for r in rows if r["model"] == model]
        scorable = [r for r in mine if r.get("correct") is not None]
        costs = [r["cost_usd"] for r in mine]
        out.append({
            "model": model,
            "runs": len(mine),
            "correct": f"{sum(1 for r in scorable if r['correct'])}/{len(scorable)}",
            "answer_recall": _avg(r.get("answer_recall") for r in mine),
            "finding_recall": _avg(r.get("finding_recall") for r in mine),
            "tool_coverage": _avg(r.get("tool_coverage") for r in mine),
            "redundant_calls": sum(r.get("redundant_calls", 0) for r in mine),
            "refused_calls": sum(r.get("refused_calls", 0) for r in mine),
            "grounding_rate": _avg(r.get("grounding_rate") for r in mine),
            "completion": {s: sum(1 for r in mine if r.get("completion") == s)
                           for s in ("complete", "partial", "fallback", "error")},
            "mean_latency_ms": _avg(r.get("wall_ms") for r in mine),
            "input_tokens": sum(r["input_tokens"] for r in mine),
            "output_tokens": sum(r["output_tokens"] for r in mine),
            "cost_usd": None if any(c is None for c in costs) else round(sum(costs), 4),
            "model_mismatch_runs": sum(1 for r in mine if r.get("model_mismatch")),
        })
    return out


def to_markdown(report: dict) -> str:
    head = ("| Model | Correct | Answer recall | Finding recall | Tool coverage | Grounding | "
            "Complete / partial / fallback / error | Mean latency (ms) | Tokens in / out | Cost (USD) |")
    lines = [head, "|" + "---|" * 10]
    for s in report["summary"]:
        c = s["completion"]
        lines.append(
            f"| {s['model']} | {s['correct']} | {s['answer_recall']} | {s['finding_recall']} | "
            f"{s['tool_coverage']} | {s['grounding_rate']} | "
            f"{c['complete']} / {c['partial']} / {c['fallback']} / {c['error']} | "
            f"{s['mean_latency_ms']} | {s['input_tokens']} / {s['output_tokens']} | {s['cost_usd']} |")
    return "\n".join(lines) + "\n"
