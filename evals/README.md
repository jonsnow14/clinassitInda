# Eval quality track

Offline evaluation harness for ClinAssistIndia. Design: [`docs/eval-pipleine.md`](../docs/eval-pipleine.md).

This is **not** a PHC product feature. Production agents stay human-triggered. The harness may call the same functions because it is a test runner.

## PR-1 / E0 (this tree)

Implemented now:

- Tagged-union gold schema (`app.eval.schema`)
- Ops-agent judge (`app.eval.agents.ops_judge`) over `evals/gold/agents.jsonl` (9 Purnia ranking rows)
- CLI `--suite unit_ops` (loads gold, runs `judge_ops`, exit 0 only if every row passes)
- Merge gate: `pytest -m unit` (no Sarvam, no Chroma)

Later PRs add retrieval, clinical replay, TraceCollector, journeys, and red-team. Census in `evals/gold/manifest.json` is the frozen v1 target (49 rows); only `n_agents` is on disk in PR-1.

## Run

From `apps/api`:

```bash
python -m app.eval
python -m app.eval.run --suite unit_ops
python -m app.eval.run --suite unit_ops --case A-BEDS-ICU
pytest -m unit -q
```

Exit codes: `0` all ops assertions pass, `1` a gold row failed, `2` missing/invalid gold or an unimplemented suite.

Do not import `app.eval` from `app.main`.
