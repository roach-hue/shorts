"""The engine logs every run to FILES (never the terminal)."""
import json
import logging

from fallback_engine import trace as trace_mod
from fallback_engine.config import Thresholds
from fallback_engine.engine import assemble
from fixtures import scenario_obvious_winner, scenario_offbeat_strict

CFG = Thresholds()


def _records() -> list[dict]:
    p = trace_mod.DUMP_FILE
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_run_is_dumped_to_file_not_terminal():
    t, a = scenario_obvious_winner()
    assemble(t, a, CFG)

    recs = [r for r in _records() if r["template"] == "t_winner"]
    assert recs, "no dump record was written to logs/runs.jsonl"
    assert recs[-1]["outcome"] in ("SUCCESS", "FALLBACK")
    assert recs[-1]["events"], "events were not recorded"

    # The logger must never reach the terminal: no propagation, file handler only.
    log = logging.getLogger("fallback_engine")
    assert log.propagate is False
    assert log.handlers and all(isinstance(h, logging.FileHandler) for h in log.handlers)


def test_fallback_outcome_is_recorded_with_reason():
    t, a = scenario_offbeat_strict()
    assemble(t, a, CFG)

    recs = [r for r in _records() if r["template"] == "t_offbeat"]
    assert recs and recs[-1]["outcome"] == "FALLBACK"
    assert recs[-1]["result"]["fallback_used"] is True
    assert recs[-1]["result"]["why"], "fallback reason (Agent B violations) not logged"
