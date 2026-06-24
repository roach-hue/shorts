"""Threshold knobs (the 'soft' part of the oracle).

Numbers that legitimately get tuned live here, NOT hardcoded in the engine or the
invariants. Tests read the same values, so 'changing the oracle's criteria' for a
threshold == editing config/thresholds.json. The RULE invariants themselves stay
rigid (see decisions/schema_contradictions.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.json"


@dataclass(frozen=True)
class Thresholds:
    beat_tolerance_sec: float = 0.1  # (5) +/-100ms
    soft_penalty_factor: float = 0.7  # RULE 10 (30% penalty on reuse)
    duration_overrun_hard_cutoff: float = 2.5  # RULE 8 (beat-priority 2.5x)
    semantic_weight: float = 0.5  # RULE 6 / Agent A scoring weights
    motion_weight: float = 0.3
    duration_weight: float = 0.2
    min_source_total_sec: float = 5.0  # RULE 7 abuse floor

    @classmethod
    def load(cls, path: "str | Path | None" = None) -> "Thresholds":
        p = Path(path) if path is not None else DEFAULT_PATH
        if not p.exists():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        w = data.get("score_weights", {})
        return cls(
            beat_tolerance_sec=data.get("beat_tolerance_sec", cls.beat_tolerance_sec),
            soft_penalty_factor=data.get("soft_penalty_factor", cls.soft_penalty_factor),
            duration_overrun_hard_cutoff=data.get(
                "duration_overrun_hard_cutoff", cls.duration_overrun_hard_cutoff
            ),
            semantic_weight=w.get("semantic", cls.semantic_weight),
            motion_weight=w.get("motion", cls.motion_weight),
            duration_weight=w.get("duration", cls.duration_weight),
            min_source_total_sec=data.get("min_source_total_sec", cls.min_source_total_sec),
        )
