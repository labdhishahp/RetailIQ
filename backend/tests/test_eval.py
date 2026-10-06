"""The evaluation framework: ground truth, scoring, the per-model client, the
LLM request shape it depends on, and the runner's safety guard. No API calls."""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.llm import llm_client
from eval.benchmark import QUESTIONS, QUESTIONS_BY_ID, Truth
from eval.clients import ModelClient, RulesOnly, cost_usd
from eval.harness import model_mismatch, run_suite
from eval.run import is_local_database, main
from eval.scoring import score


def test_every_question_has_a_defined_rule_and_required_tools():
    assert len({q.id for q in QUESTIONS}) == len(QUESTIONS)
    for q in QUESTIONS:
        assert q.definition and q.required_tools


def test_ground_truth_reflects_the_seeded_data(SessionLocal, seeded):
    db = SessionLocal()
    try:
        keys = lambda qid: [e.key for e in QUESTIONS_BY_ID[qid].truth(db).entities]  # noqa: E731
        assert "T-001" in keys("reorder"), "15 units at ~1/day is under 21 days of cover"
        assert "T-002" in keys("dead_stock"), "500 units and no sales"
        assert "T-CMP1" in keys("campaigns"), "active, ROI 1.0x"
        assert QUESTIONS_BY_ID["churn"].truth(db).number is not None
    finally:
        db.close()


def test_rule_baseline_runs_and_scores(SessionLocal, seeded):
    db = SessionLocal()
    try:
        report = run_suite(db, [RulesOnly()],
                           [QUESTIONS_BY_ID[q] for q in ("reorder", "dead_stock", "campaigns")])
    finally:
        db.close()
    rows = {r["question"]: r for r in report["rows"]}
    for qid in ("reorder", "dead_stock", "campaigns"):
        row = rows[qid]
        assert row["completion"] == "complete" and row["model"] == "rules"
        assert row["tool_coverage"] == 1.0
        assert row["finding_recall"] == 1.0, row
        assert row["cost_usd"] == 0.0 and row["input_tokens"] == 0
    summary = report["summary"][0]
    assert summary["model"] == "rules" and summary["runs"] == 3


def test_scoring_numbers_tools_and_grounding():
    question = QUESTIONS_BY_ID["revenue"]
    result = {
        "rootCause": "Revenue fell 12.3% over the period.", "evidence": [], "nextSteps": [],
        "suggestedCampaign": "", "synthesis": "llm",
        "trace": {"mode": "llm", "unverifiedClaims": ["x"], "delegations": 2},
        "agents": [{"findings": [{"statement": "a", "verified": True},
                                 {"statement": "b", "verified": False},
                                 {"statement": "c", "verified": None}],
                    "fallback": None,
                    "steps": [{"tool": "sales_summary", "args": {"days": 90}, "ok": True},
                              {"tool": "sales_summary", "args": {"days": 90}, "ok": True},
                              {"tool": "campaign_status", "args": {}, "ok": False}]}],
        "elapsedMs": 10,
    }
    row = score(question, Truth(number=-12.3), result, expect_llm=True)
    assert row["number_match_answer"] is True and row["correct"] is True
    assert row["tool_coverage"] == 1.0 and row["redundant_calls"] == 1 and row["refused_calls"] == 1
    assert row["grounding_rate"] == 0.5 and row["unverified_conclusion_claims"] == 1
    assert row["completion"] == "complete"

    result["agents"][0]["fallback"] = "llm_budget"
    assert score(question, Truth(number=-12.3), result, expect_llm=True)["completion"] == "partial"
    result["trace"]["mode"] = "rules"
    assert score(question, Truth(number=-12.3), result, expect_llm=True)["completion"] == "fallback"
    assert score(question, Truth(), result, expect_llm=False)["correct"] is None


class _FakeInner:
    tool_calling_available = True

    def __init__(self, served="claude-sonnet-5-5"):
        self.served, self.calls = served, []

    def create_message(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(model=self.served, stop_reason="end_turn", content=[],
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=200,
                                                     cache_read_input_tokens=0,
                                                     cache_creation_input_tokens=0))


def test_model_client_pins_model_disables_fallback_and_counts_usage():
    inner = _FakeInner()
    client = ModelClient("claude-sonnet-5-5", inner=inner)
    client.create_message(system="s", messages=[], effort="low")
    client.create_message(system="s", messages=[], effort="low")
    assert all(c["model"] == "claude-sonnet-5-5" and c["fallbacks"] is False for c in inner.calls)
    usage = client.usage()
    assert usage["calls"] == 2 and usage["input_tokens"] == 2000 and usage["output_tokens"] == 400
    assert cost_usd("claude-sonnet-5-5", 2000, 400) == pytest.approx(2000 / 1e6 * 2 + 400 / 1e6 * 10)
    client.reset()
    assert client.usage()["calls"] == 0


def test_model_mismatch_detection():
    assert not model_mismatch("claude-opus-5-5", {"claude-opus-5-5": 3})
    assert not model_mismatch("claude-haiku-4-5", {"claude-haiku-4-5-20251001": 1})
    assert model_mismatch("claude-opus-5-5", {"claude-opus-5-5": 2, "claude-opus-4-8": 1})


class _FakeSDK:
    def __init__(self):
        self.kwargs = None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(stop_reason="end_turn", content=[], usage=None)

    def with_options(self, **_):
        return self


def test_create_message_request_shape(monkeypatch):
    sdk = _FakeSDK()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(llm_client, "_sdk", sdk)

    llm_client.create_message(system="s", messages=[], effort="low")
    assert sdk.kwargs["model"] == settings.llm_model
    assert sdk.kwargs["output_config"] == {"effort": "low"}
    assert sdk.kwargs["fallbacks"] == "default"

    llm_client.create_message(system="s", messages=[], model="claude-haiku-4-5", fallbacks=False)
    assert sdk.kwargs["model"] == "claude-haiku-4-5"
    assert "output_config" not in sdk.kwargs, "Haiku 4.5 rejects effort"
    assert "fallbacks" not in sdk.kwargs and "betas" not in sdk.kwargs


@pytest.mark.parametrize("url,local", [
    ("postgresql://postgres@localhost:5432/eval", True),
    ("postgresql://postgres@127.0.0.1/eval", True),
    ("postgresql://postgres:@/postgres?host=/tmp/pg", True),
    ("postgresql:///eval", True),
    ("postgresql://u:p@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres", False),
    ("mysql://root@localhost/eval", False),
])
def test_runner_only_reseeds_local_databases(url, local):
    assert is_local_database(url) is local


def test_runner_refuses_remote_database():
    with pytest.raises(SystemExit):
        main(["--database-url", "postgresql://u:p@db.example.com:5432/x", "--baseline-only"])


def test_rows_persist_the_actual_investigation(SessionLocal, seeded):
    import json

    db = SessionLocal()
    try:
        report = run_suite(db, [RulesOnly()], [QUESTIONS_BY_ID["reorder"]])
    finally:
        db.close()
    row = json.loads(json.dumps(report, default=str))["rows"][0]   # as written to results.json
    r = row["response"]
    assert row["question_text"] == QUESTIONS_BY_ID["reorder"].text
    assert r["conclusion"]["rootCause"] and r["conclusion"]["synthesis"] == "rules"
    assert r["recommendation"]["action"] and r["recommendation"]["nextSteps"]
    assert r["evidence"] and r["decisions"] and r["rounds"] >= 1
    assert r["agents"] and all("steps" in a and "findings" in a for a in r["agents"])
    assert "inventory_status" in r["tools_called"]
    assert r["trace"]["mode"] == "rules" and "fallback" in r["trace"]
    # scores sit next to the response in the same row
    assert {"correct", "finding_recall", "grounding_rate", "completion", "wall_ms",
            "input_tokens", "output_tokens"} <= row.keys()


def test_errored_run_is_recorded_without_a_response(SessionLocal, seeded, monkeypatch):
    import eval.harness as harness

    def boom(*_, **__):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(harness, "investigate", boom)
    db = SessionLocal()
    try:
        row = run_suite(db, [RulesOnly()], [QUESTIONS_BY_ID["churn"]])["rows"][0]
    finally:
        db.close()
    assert row["completion"] == "error" and row["response"] is None
    assert "provider exploded" in row["error"]
