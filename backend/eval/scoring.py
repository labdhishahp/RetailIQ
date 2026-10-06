"""Scores one investigation result against a question's ground truth.

Every metric is mechanical; there is no subjective grading.

* answer_recall   share of expected entities named in the conclusion
                  (rootCause, evidence, nextSteps, suggestedCampaign)
* finding_recall  share named anywhere in the specialists' findings
* number_match    for numeric questions: the expected figure appears (to 0.1)
* correct         answer_recall == 1.0, or number_match in the conclusion
* tool_coverage   share of the question's required tools that were called
* grounding_rate  share of findings containing figures whose figures all
                  appear in tool output (the runtime's verified flag)
* completion      complete | partial | fallback  (see _completion)

An entity counts as named if its key (SKU, campaign code, store) is a finding's
`entity`, or its key or name appears in the text, case-insensitively.
"""

import json
import re

from eval.benchmark import Question, Truth

_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _texts(result: dict) -> tuple[str, str, set[str]]:
    answer = " ".join([result.get("rootCause", ""), result.get("suggestedCampaign", ""),
                       *result.get("evidence", []), *result.get("nextSteps", [])])
    findings = [f for a in result.get("agents", []) for f in a.get("findings", [])]
    return (answer, " ".join(f.get("statement", "") for f in findings),
            {f["entity"] for f in findings if f.get("entity")})


def _named(entity, text: str, entity_fields: set[str]) -> bool:
    lowered = text.lower()
    return (entity.key in entity_fields or entity.key.lower() in lowered
            or entity.name.lower() in lowered)


def _has_number(text: str, expected: float) -> bool:
    for raw in _NUMBER.findall(text):
        try:
            if abs(abs(float(raw.replace(",", ""))) - abs(expected)) <= 0.051:
                return True
        except ValueError:
            continue
    return False


def _completion(result: dict, expect_llm: bool) -> str:
    """complete: the run used the intended path end to end.
    partial:  model run where a specialist fell back or a conclusion field was missing.
    fallback: model run that ended up entirely on the rule path."""
    if not expect_llm:
        return "complete"
    trace = result.get("trace", {})
    if trace.get("mode") != "llm":
        return "fallback"
    if result.get("synthesis") != "llm" or any(a.get("fallback") for a in result.get("agents", [])):
        return "partial"
    return "complete"


def score(question: Question, truth: Truth, result: dict, *, expect_llm: bool) -> dict:
    answer, findings, entity_fields = _texts(result)
    row: dict = {"question": question.id}

    if truth.entities:
        hits_answer = [e.key for e in truth.entities if _named(e, answer, set())]
        hits_findings = [e.key for e in truth.entities
                         if _named(e, findings, entity_fields) or e.key in hits_answer]
        row["expected"] = [e.key for e in truth.entities]
        row["answer_recall"] = round(len(hits_answer) / len(truth.entities), 3)
        row["finding_recall"] = round(len(hits_findings) / len(truth.entities), 3)
        row["missed"] = [k for k in row["expected"] if k not in hits_findings]
        row["correct"] = row["answer_recall"] == 1.0
    elif truth.number is not None:
        row["expected"] = truth.number
        row["number_match_answer"] = _has_number(answer, truth.number)
        row["number_match_findings"] = _has_number(findings, truth.number)
        row["correct"] = row["number_match_answer"]
    else:
        # The rule selects nothing (e.g. no shampoo declined): not scorable.
        row["expected"] = []
        row["correct"] = None

    steps = [s for a in result.get("agents", []) for s in a.get("steps", [])]
    called = {s["tool"] for s in steps if s.get("ok")}
    seen, redundant = set(), 0
    for s in steps:
        if not s.get("ok"):
            continue
        key = (s["tool"], json.dumps(s.get("args", {}), sort_keys=True))
        redundant += key in seen
        seen.add(key)
    row["tool_coverage"] = round(len(question.required_tools & called) / len(question.required_tools), 3)
    row["missing_tools"] = sorted(question.required_tools - called)
    row["tool_calls"] = sum(1 for s in steps if s.get("ok"))
    row["redundant_calls"] = redundant
    row["refused_calls"] = sum(1 for s in steps if not s.get("ok"))

    flags = [f.get("verified") for a in result.get("agents", []) for f in a.get("findings", [])]
    checked = [v for v in flags if v is not None]
    row["grounding_rate"] = round(sum(checked) / len(checked), 3) if checked else None
    row["unverified_conclusion_claims"] = len(result.get("trace", {}).get("unverifiedClaims", []))

    row["completion"] = _completion(result, expect_llm)
    row["delegations"] = result.get("trace", {}).get("delegations", 0)
    row["latency_ms"] = result.get("elapsedMs")
    return row
