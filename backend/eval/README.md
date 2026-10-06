# Copilot evaluation

Runs one fixed benchmark against the rule baseline and each supported model,
on a freshly seeded local database, and scores every run the same way.

```bash
cd backend
export EVAL_DATABASE_URL=postgresql://postgres@localhost:5432/retailiq_eval   # local throwaway
python -m eval.run                                   # baseline; + models if LLM_API_KEY is set
python -m eval.run --baseline-only
python -m eval.run --models claude-sonnet-5-5 --questions reorder,churn --repeats 3
```

The database is **dropped and re-seeded** (`init_db`, fixed `SEED`) before
every run, so any non-local host is refused. Output goes to
`eval/results/<UTC time>/results.json` (every row, ground truth, definitions,
pricing, git commit) and `summary.md`. Each row carries its scores and, under
`response`, the investigation itself: conclusion, recommendation, evidence,
lead decisions per round, every agent's findings and tool calls, and the
trace's mode / fallback / unverified claims (`null` if the run errored).

## What runs

| Client | How |
|---|---|
| `rules` | No model: lead and specialists run their rule policies. Free. |
| `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-4-5` | The production agents through `LLMClient`, every call pinned to the model, **server-side fallback off** (a fallback would answer with another model). Needs `LLM_API_KEY`; costs money. |

Model ids are the tool-calling Anthropic models in the installed SDK's model
list. The OpenAI provider is not included: the agent runtime only supports
tool calling through Anthropic.

## Ground truth

`benchmark.py` defines each question's expected answer as a rule, computed
from the database at evaluation time with queries written independently of
the agent tools. Each rule is also stored in `results.json`.

| Question | Expected answer |
|---|---|
| reorder | ≤3 products with fewest days of cover where cover < 21 (cover = on hand ÷ 90-day units/90) |
| dead_stock | ≤3 products with stock and no units sold in 90 days, by stock value |
| shampoo | ≤3 "shampoo" products whose 90-day revenue is below the prior 90 days |
| campaigns | every active campaign with revenue ÷ spend < 2.5 |
| churn | number of customers at risk or churned |
| stores | stores with the lowest and highest 90-day revenue growth |
| margins | ≤3 products selling > 2% below list in the last 90 days |
| revenue | % revenue change, last 90 vs prior 90 days |

If a rule selects nothing on the current data (e.g. no product is under 21
days of cover), the question is reported as not scorable (`correct: null`),
never as correct.

## Metrics

All mechanical; nothing is graded subjectively.

| Metric | Definition |
|---|---|
| correct | all expected entities named in the conclusion, or the expected figure (±0.05) appears in it |
| answer_recall / finding_recall | share of expected entities named in the conclusion / in any specialist finding |
| tool_coverage | share of the question's required tools that were called; plus `redundant_calls` (identical tool + args repeated) and `refused_calls` (out-of-scope calls the gate rejected) |
| grounding_rate | share of findings with figures whose figures all appear in tool output (the runtime's `verified` flag); plus unverified claims in the conclusion |
| completion | `complete`, `partial` (a specialist fell back or a conclusion field was missing), `fallback` (whole run ended on rules), `error` |
| latency | wall-clock per investigation |
| tokens / cost | input and output tokens summed over every model call; cost from the list prices in `clients.py` (re-check before publishing) |
| model_mismatch | a call was answered by a different model than requested |

## Reading the results

- The rule baseline shares its thresholds with the ground-truth rules (21 days,
  2.5x, 2%), so a high baseline score confirms the rules are implemented as
  specified; it is not an independent accuracy measure. Model runs are where
  the comparison is informative.
- The seed is fixed but its dates are relative to the day it runs, so week and
  month boundaries shift; ground truth is always recomputed for the data the
  agents see.
- Model output varies run to run: use `--repeats` before comparing models.
