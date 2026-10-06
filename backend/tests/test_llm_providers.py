"""OpenAI / Gemini adapters: translation in both directions, preserved provider
state between turns, errors, and a full run of the unchanged runtime loop.
HTTP is faked; no API calls."""

import time

import pytest

from app.agents.runtime import Budget, run_tool_loop
from app.agents.tools import TOOL_SPECS
from app.core.config import settings
from app.services import llm_providers
from app.services.llm import LLMUnavailable
from app.services.llm_providers import GeminiClient, OpenAIResponsesClient
from eval.clients import ModelClient, provider_client

FINISH = {"name": "submit_findings", "description": "finish",
          "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}},
                           "required": ["summary"], "additionalProperties": False},
          "strict": True}


class FakeHTTP:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, url, *, headers, params, json, timeout):
        self.requests.append({"url": url, "headers": headers, "json": json})
        status, body = self.replies.pop(0)
        return type("R", (), {"status_code": status, "json": lambda self=None: body, "text": str(body)})()


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "gemini_api_key", "g-test")
    monkeypatch.setattr(llm_providers.time, "sleep", lambda s: None)


def _fake(monkeypatch, replies):
    fake = FakeHTTP(replies)
    monkeypatch.setattr(llm_providers.httpx, "post", fake)
    return fake


# ---- OpenAI Responses API -------------------------------------------------

REASONING = {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "ENC=="}
CALL = {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "inventory_status",
        "arguments": '{"name_contains":""}', "status": "completed"}


def _openai_turn(*items, status="completed"):
    return 200, {"model": "gpt-5.5-2026-04-23", "status": status, "output": list(items),
                 "usage": {"input_tokens": 100, "output_tokens": 20}}


def test_openai_round_trip_preserves_reasoning_and_tool_calls(monkeypatch, keys):
    fake = _fake(monkeypatch, [
        _openai_turn(REASONING, CALL),
        _openai_turn({"type": "message", "content": [{"type": "output_text", "text": "done"}]}),
    ])
    client = OpenAIResponsesClient()
    tools = [TOOL_SPECS["inventory_status"]]
    first = client.create_message(system="sys", messages=[{"role": "user", "content": "q"}],
                                  tools=tools, effort="low", model="gpt-5.5")
    use = next(b for b in first.content if b.type == "tool_use")
    assert (first.stop_reason, use.id, use.name, use.input) == (
        "tool_use", "call_1", "inventory_status", {"name_contains": ""})
    assert first.usage.input_tokens == 100 and first.model == "gpt-5.5-2026-04-23"

    req = fake.requests[0]["json"]
    assert fake.requests[0]["url"].endswith("/v1/responses")
    assert req["model"] == "gpt-5.5" and req["reasoning"] == {"effort": "low"}
    assert req["store"] is False and req["include"] == ["reasoning.encrypted_content"]
    assert req["tools"][0] == {"type": "function", "name": "inventory_status",
                               "description": tools[0]["description"],
                               "parameters": tools[0]["input_schema"], "strict": True}

    # Second turn exactly as the runtime builds it.
    history = [{"role": "user", "content": "q"},
               {"role": "assistant", "content": first.content},
               {"role": "user", "content": [
                   {"type": "tool_result", "tool_use_id": "call_1", "content": "[]", "is_error": False},
                   {"type": "text", "text": "finish now"}]}]
    second = client.create_message(system="sys", messages=history, tools=tools, model="gpt-5.5")
    assert second.stop_reason == "end_turn"
    assert [b.text for b in second.content if b.type == "text"] == ["done"]
    assert fake.requests[1]["json"]["input"] == [
        {"role": "user", "content": "q"},
        REASONING, CALL,                                   # replayed verbatim
        {"type": "function_call_output", "call_id": "call_1", "output": "[]"},
        {"role": "user", "content": "finish now"},
    ]


def test_openai_max_tokens_and_errors(monkeypatch, keys):
    client = OpenAIResponsesClient()
    _fake(monkeypatch, [(200, {"status": "incomplete", "output": [],
                               "incomplete_details": {"reason": "max_output_tokens"}})])
    assert client.create_message(system="s", messages=[{"role": "user", "content": "q"}]).stop_reason == "max_tokens"

    _fake(monkeypatch, [(400, {"error": {"message": "bad request"}})])
    with pytest.raises(LLMUnavailable, match="HTTP 400: bad request"):
        client.create_message(system="s", messages=[{"role": "user", "content": "q"}])

    fake = _fake(monkeypatch, [(503, {"error": {"message": "busy"}}), _openai_turn()])
    client.create_message(system="s", messages=[{"role": "user", "content": "q"}], timeout=60)
    assert len(fake.requests) == 2, "503 is retried"

    _fake(monkeypatch, [_openai_turn({"type": "message", "content": [{"type": "refusal", "refusal": "no"}]})])
    with pytest.raises(LLMUnavailable, match="declined"):
        client.create_message(system="s", messages=[{"role": "user", "content": "q"}])


# ---- Gemini ---------------------------------------------------------------

def _gemini_turn(*parts, finish="STOP"):
    return 200, {"modelVersion": "gemini-3.5-flash", "candidates": [
        {"content": {"role": "model", "parts": list(parts)}, "finishReason": finish}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 50}}


def test_gemini_round_trip_preserves_thought_signature(monkeypatch, keys):
    call_part = {"functionCall": {"id": "g1", "name": "inventory_status", "args": {"name_contains": ""}},
                 "thoughtSignature": "SIG=="}
    fake = _fake(monkeypatch, [_gemini_turn({"text": "thinking", "thought": True}, call_part),
                               _gemini_turn({"text": "done"})])
    client = GeminiClient()
    tools = [TOOL_SPECS["inventory_status"]]
    first = client.create_message(system="sys", messages=[{"role": "user", "content": "q"}],
                                  tools=tools, model="gemini-3.5-flash", effort="low")
    use = next(b for b in first.content if b.type == "tool_use")
    assert (first.stop_reason, use.id, use.name, use.input) == (
        "tool_use", "g1", "inventory_status", {"name_contains": ""})
    assert not [b for b in first.content if b.type == "text"], "thought parts are not answer text"
    assert first.usage.output_tokens == 70, "thinking tokens count as output"

    req = fake.requests[0]
    assert req["url"].endswith("/gemini-3.5-flash:generateContent")
    assert req["headers"] == {"x-goog-api-key": "g-test"}
    assert req["json"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "low"}
    decl = req["json"]["tools"][0]["functionDeclarations"][0]
    assert decl == {"name": "inventory_status", "description": tools[0]["description"],
                    "parametersJsonSchema": tools[0]["input_schema"]}

    history = [{"role": "user", "content": "q"},
               {"role": "assistant", "content": first.content},
               {"role": "user", "content": [
                   {"type": "tool_result", "tool_use_id": "g1", "content": "[]", "is_error": False},
                   {"type": "tool_result", "tool_use_id": "g1", "content": "bad", "is_error": True}]}]
    second = client.create_message(system="sys", messages=history, tools=tools)
    assert second.stop_reason == "end_turn"
    contents = fake.requests[1]["json"]["contents"]
    assert contents[1] == {"role": "model", "parts": [{"text": "thinking", "thought": True}, call_part]}
    assert contents[2]["parts"] == [
        {"functionResponse": {"id": "g1", "name": "inventory_status", "response": {"result": "[]"}}},
        {"functionResponse": {"id": "g1", "name": "inventory_status", "response": {"error": "bad"}}},
    ]


def test_gemini_safety_block_and_missing_call_id(monkeypatch, keys):
    client = GeminiClient()
    _fake(monkeypatch, [_gemini_turn(finish="SAFETY")])
    with pytest.raises(LLMUnavailable, match="declined"):
        client.create_message(system="s", messages=[{"role": "user", "content": "q"}])

    _fake(monkeypatch, [_gemini_turn({"functionCall": {"name": "campaign_status", "args": {}}})])
    r = client.create_message(system="s", messages=[{"role": "user", "content": "q"}])
    use = next(b for b in r.content if b.type == "tool_use")
    assert use.id.startswith("call_")
    state = next(b for b in r.content if b.type == "gemini_parts")
    assert state.parts[0]["functionCall"]["id"] == use.id, "generated id is replayed too"


# ---- the unchanged runtime drives both adapters ---------------------------

@pytest.mark.parametrize("client,replies", [
    (OpenAIResponsesClient(), [
        _openai_turn(REASONING, CALL),
        _openai_turn({"type": "function_call", "id": "fc_2", "call_id": "call_2",
                      "name": "submit_findings", "arguments": '{"summary":"ok"}'})]),
    (GeminiClient(), [
        _gemini_turn({"functionCall": {"id": "g1", "name": "inventory_status",
                                       "args": {"name_contains": ""}}, "thoughtSignature": "S"}),
        _gemini_turn({"functionCall": {"id": "g2", "name": "submit_findings",
                                       "args": {"summary": "ok"}}, "thoughtSignature": "T"})]),
])
def test_runtime_loop_runs_through_adapter(monkeypatch, keys, client, replies):
    _fake(monkeypatch, replies)
    executed = []

    def execute(batch):
        executed.extend(batch)
        return [("[]", False) for _ in batch]

    outcome = run_tool_loop(llm=client, system="s", prompt="q",
                            tools=[TOOL_SPECS["inventory_status"], FINISH],
                            finish_tool="submit_findings", execute=execute,
                            budget=Budget(deadline=time.monotonic() + 60, max_turns=4), effort="low")
    assert outcome.final == {"summary": "ok"} and outcome.stopped == "finished"
    assert [(name, args) for _, name, args in executed] == [("inventory_status", {"name_contains": ""})]
    assert outcome.turns == 2 and outcome.input_tokens == 200


def test_eval_routes_models_to_their_provider(monkeypatch):
    assert isinstance(provider_client("gpt-5.5"), OpenAIResponsesClient)
    assert isinstance(provider_client("gemini-3.5-flash"), GeminiClient)
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "x")
    assert ModelClient("gpt-5.5").tool_calling_available is False
    assert ModelClient("gemini-3.5-flash").tool_calling_available is True


# ---- OpenAI as the live provider (LLM_PROVIDER=openai) ----------------------

@pytest.fixture
def live_openai(monkeypatch, keys):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", "")


def test_live_client_uses_openai_adapter(monkeypatch, live_openai):
    from app.services.llm import llm_client

    assert settings.llm_enabled and llm_client.tool_calling_available
    assert llm_client.model == "gpt-5.5"
    fake = _fake(monkeypatch, [_openai_turn({"type": "message", "content": [{"type": "output_text", "text": "hi"}]})])
    r = llm_client.create_message(system="s", messages=[{"role": "user", "content": "q"}], effort="low")
    assert fake.requests[0]["url"].endswith("/v1/responses")
    assert fake.requests[0]["json"]["model"] == "gpt-5.5"
    assert fake.requests[0]["headers"] == {"Authorization": "Bearer sk-test"}
    assert [b.text for b in r.content if b.type == "text"] == ["hi"]

    monkeypatch.setattr(settings, "openai_api_key", "")
    assert not settings.llm_enabled and not llm_client.tool_calling_available


def test_live_report_summary_uses_openai(monkeypatch, live_openai):
    from app.services.llm import llm_client

    _fake(monkeypatch, [_openai_turn({"type": "message", "content": [{"type": "output_text", "text": "Summary."}]})])
    assert llm_client.complete(system="s", prompt="p") == "Summary."


class _RoutedOpenAI:
    """Scripted Responses API: replies chosen by which agent is calling."""

    def __init__(self, scripts):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.calls = []

    def __call__(self, url, *, headers, params, json, timeout):
        role = next(k for k in self.scripts if json["instructions"].startswith(f"You are the {k}"))
        self.calls.append((role, json))
        status, body = _openai_turn(*self.scripts[role].pop(0))
        return type("R", (), {"status_code": status, "json": lambda self=None: body, "text": ""})()


def _fc(call_id, name, args):
    import json as _json
    return {"type": "function_call", "id": f"fc_{call_id}", "call_id": call_id, "name": name,
            "arguments": _json.dumps(args)}


def test_live_investigation_runs_on_openai(monkeypatch, live_openai, SessionLocal, seeded):
    from app.agents.orchestrator import investigate

    fake = _RoutedOpenAI({
        "lead investigator": [
            [REASONING, _fc("L1", "delegate", {"agent": "inventory", "objective": "find stock risk", "focus": ""})],
            [_fc("L2", "submit_conclusion", {
                "rootCause": "Fast Mover is about to stock out.", "evidence": ["Fast Mover has 15 units."],
                "businessImpact": "Lost sales.", "riskLevel": "high",
                "suggestedCampaign": "Reorder Fast Mover.", "nextSteps": ["Raise a PO for Fast Mover."]})],
        ],
        "Inventory Agent": [
            [_fc("I1", "inventory_status", {"name_contains": ""})],
            [_fc("I2", "submit_findings", {"summary": "Short.", "follow_up": "", "findings": [
                {"statement": "Fast Mover has 15 units on hand.", "severity": "critical", "entity": "T-001"}]})],
        ],
    })
    monkeypatch.setattr(llm_providers.httpx, "post", fake)

    db = SessionLocal()
    try:
        result = investigate(db, "Which products need immediate reorder?")   # default live client
    finally:
        db.close()
    assert result["trace"]["mode"] == "llm" and result["synthesis"] == "llm"
    assert result["plan"]["planner"] == "llm"
    assert [d["agent"] for d in result["trace"]["decisions"]] == ["inventory"]
    inventory = result["agents"][0]
    assert inventory["mode"] == "llm" and inventory["toolsCalled"] == ["inventory_status"]
    assert inventory["findings"][0]["verified"] is True
    assert result["rootCause"] == "Fast Mover is about to stock out."
    assert all(json["model"] == "gpt-5.5" for _, json in fake.calls)
    # the lead's reasoning item was replayed on its second turn
    lead_second = [json for role, json in fake.calls if role == "lead investigator"][1]
    assert REASONING in lead_second["input"]


def test_health_reports_live_provider(client, live_openai):
    body = client.get("/health").json()
    assert body["llm_configured"] is True
    assert body["llm_provider"] == "openai" and body["llm_model"] == "gpt-5.5"
