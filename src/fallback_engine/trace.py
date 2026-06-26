"""File-based run trace for the engine.

Records every stage's outcome (ok/fail), how a success was reached, and what a
failure fell back to -- to FILES under logs/, NEVER to the terminal:
  logs/engine.log   human-readable, one line per step
  logs/runs.jsonl   one JSON object per assemble() call (machine-readable dump)

The logger sets propagate=False and uses only a FileHandler, so nothing is ever
printed to stdout/stderr (terminal output truncates; files do not).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "engine.log"
DUMP_FILE = LOG_DIR / "runs.jsonl"


def _logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    log = logging.getLogger("fallback_engine")
    if not log.handlers:
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(handler)
        log.propagate = False  # never bubble up to the terminal
    return log


class RunTrace:
    """Accumulates structured events for one assemble() call and writes them out."""

    def __init__(self, template_id: str):
        self.log = _logger()
        self.template_id = template_id
        self.events: list[dict] = []
        self.log.info(f"=== RUN start  template={template_id} ===")

    def step(self, stage: str, status: str, **detail) -> None:
        """Record one operation: stage name, ok/fail, and how/what (detail)."""
        self.events.append({"stage": stage, "status": status, **detail})
        self.log.info(f"  [{stage}] {status} :: {detail}")

    def finish(self, outcome: str, result: dict) -> None:
        """Close the run: write the final outcome + a full JSON dump line."""
        self.log.info(f"=== RUN end    outcome={outcome} :: {result} ===")
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "template": self.template_id,
            "outcome": outcome,
            "result": result,
            "events": self.events,
        }
        with open(DUMP_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
