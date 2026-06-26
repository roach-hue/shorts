"""Core Engine entry point (Agent A -> Agent B -> Fallback).

Best-effort, non-stop assembly: with sufficient source the engine ALWAYS returns an
EditInstruction. Agent A does the smart 3-axis match (RULE 6/4/10); Agent B fact-
checks the rhythm once (RULE 12, 1-Hit); on reject control falls through to Fallback,
which drops the semantic axis and force-fills by rhythm (motion) so a tempo-correct
result is still returned (every clip flagged fallback_used=True).

Every stage's outcome (ok/fail), how a success was reached, and what a failure fell
back to is recorded to a FILE via trace.RunTrace -- never to the terminal.
"""
from __future__ import annotations

import math

from . import invariants
from .config import Thresholds
from .schemas import AssetDB, EditClip, EditInstruction, Reject, Template
from .trace import RunTrace

# Coarse motion targets per template motion label. seg.motion_score is in [0, 1].
_MOTION_TARGET = {"static": 0.0, "medium": 0.5, "high": 1.0}


def _motion_target(label: str) -> float:
    return _MOTION_TARGET.get((label or "static").lower(), 0.5)


def _motion_fit(cut, seg) -> float:
    """Closeness of seg.motion_score to the cut's desired motion (1.0 == exact)."""
    return 1.0 - abs(seg.motion_score - _motion_target(cut.visual.motion))


def _duration_fit(cut, seg) -> float:
    """>= slot duration -> 1.0, else proportional (a short clip can be speed-filled)."""
    if cut.duration <= 0:
        return 1.0
    if seg.duration >= cut.duration:
        return 1.0
    return seg.duration / cut.duration


def _semantic_fit(cut, seg) -> float:
    """Cosine similarity between cut/segment vectors (RULE 6), clamped to [0, 1].
    0 when either side has no usable vector."""
    cv, sv = cut.semantic_vector, seg.semantic_vector
    if not cv or not sv or len(cv) != len(sv):
        return 0.0
    dot = sum(a * b for a, b in zip(cv, sv))
    ncv = math.sqrt(sum(a * a for a in cv))
    nsv = math.sqrt(sum(b * b for b in sv))
    if ncv == 0.0 or nsv == 0.0:
        return 0.0
    return max(0.0, dot / (ncv * nsv))


def _score(cut, seg, used_ids, cfg, *, use_semantic: bool) -> float:
    """3-axis fit (RULE 6: 50/30/20). Fallback drops the semantic axis.
    Reused segments are softly penalised (RULE 10) but never permanently discarded."""
    base = cfg.semantic_weight * _semantic_fit(cut, seg) if use_semantic else 0.0
    base += cfg.motion_weight * _motion_fit(cut, seg)
    base += cfg.duration_weight * _duration_fit(cut, seg)
    if seg.seg_id in used_ids:
        base *= cfg.soft_penalty_factor
    return base


def _allocate(template, asset_db, cfg, *, use_semantic, fallback_used, tr) -> EditInstruction:
    """Greedy slot-fixed allocation (RULE 4). Shared by Agent A and Fallback; the only
    difference is whether the semantic axis is scored. Logs each slot decision."""
    candidates = [(asset, seg) for asset in asset_db.assets for seg in asset.segments]
    used_ids: set[str] = set()
    clips: list[EditClip] = []
    stage = "fallback_slot" if fallback_used else "agentA_slot"

    for cut in template.cuts:
        best = None
        for asset, seg in candidates:
            s = _score(cut, seg, used_ids, cfg, use_semantic=use_semantic)
            if best is None or s > best[2]:
                best = (asset, seg, s)
        asset, seg, score = best

        # RULE 8/12: fill the slot to its exact duration, pinned to the beat.
        available = seg.out - seg.in_
        if available >= cut.duration:
            out_point, speed = seg.in_ + cut.duration, 1.0
        else:
            out_point, speed = seg.out, available / cut.duration

        clips.append(EditClip(
            slot_id=cut.cut_id, source_file=asset.file_name, seg_id=seg.seg_id,
            in_=seg.in_, out=out_point, timeline_position=cut.in_, speed=speed,
            keep_audio=cut.keep_audio, fallback_used=fallback_used, re_sync_applied=False,
        ))
        used_ids.add(seg.seg_id)
        tr.step(stage, "ok", slot=cut.cut_id, seg=seg.seg_id, score=round(score, 4),
                how=("rhythm-only" if not use_semantic else "semantic+rhythm"))

    return EditInstruction(total_duration=template.total_duration,
                           is_original_sync_broken=False, clips=clips)


def agent_b_validate(template, edit, cfg) -> list[str]:
    """Agent B: 1-Hit rhythm fact-check (RULE 12). Strict slots must transition on a
    template beat (+/- tolerance); flexible slots bypass; the timeline must reach the
    template length. Returns violations (empty == accepted)."""
    violations: list[str] = []
    cut_by_id = {c.cut_id: c for c in template.cuts}
    beats = template.beat_timestamps
    for clip in edit.clips:
        cut = cut_by_id.get(clip.slot_id)
        if cut is None or cut.slot_mode != "strict":
            continue  # flexible mode: beat check bypassed
        if beats:
            nearest = min(abs(clip.timeline_position - b) for b in beats)
            if nearest > cfg.beat_tolerance_sec:
                violations.append(
                    f"slot {clip.slot_id} transition {clip.timeline_position:.3f}s is "
                    f"{nearest:.3f}s off the nearest beat (> {cfg.beat_tolerance_sec}s)")
    if edit.clips:
        end = max(c.timeline_position + (c.out - c.in_) / (c.speed or 1.0) for c in edit.clips)
        if end < template.total_duration - cfg.beat_tolerance_sec:
            violations.append(f"assembled {end:.3f}s < template {template.total_duration:.3f}s")
    return violations


def assemble(template: Template, asset_db: AssetDB, cfg: "Thresholds | None" = None):
    """Orchestrate RULE7 gate -> Agent A -> Agent B -> Fallback.

    With sufficient source this NEVER dead-ends: an Agent B reject falls through to
    Fallback (1-Hit, no re-search). The only Reject is the RULE 7 input abuse gate.
    Every stage is traced to logs/ (see trace.py) -- never to the terminal.
    """
    cfg = cfg or Thresholds.load()
    tr = RunTrace(template.template_id)

    # RULE 7: input abuse gate -- the one place we refuse outright.
    total = invariants.total_segment_seconds(asset_db)
    if invariants.is_source_insufficient(asset_db, cfg):
        tr.step("rule7_gate", "fail", total=round(total, 3), floor=cfg.min_source_total_sec)
        rej = Reject(
            code="SOURCE_INSUFFICIENT",
            reason=f"total source {total:.3f}s below floor {cfg.min_source_total_sec:.3f}s",
        )
        tr.finish("REJECT", {"code": rej.code, "reason": rej.reason})
        return rej
    tr.step("rule7_gate", "ok", total=round(total, 3))

    # Agent A: smart 3-axis match.
    candidate = _allocate(template, asset_db, cfg, use_semantic=True, fallback_used=False, tr=tr)
    tr.step("agent_a", "ok", picks=[[c.slot_id, c.seg_id] for c in candidate.clips])

    # Agent B: 1-Hit rhythm fact-check.
    violations = agent_b_validate(template, candidate, cfg)
    if not violations:
        tr.step("agent_b", "ok")
        tr.finish("SUCCESS", {"how": "Agent A semantic match accepted by Agent B",
                              "fallback_used": False,
                              "picks": [[c.slot_id, c.seg_id] for c in candidate.clips]})
        return candidate

    # RULE 12 1-Hit: no re-search. Fallback drops semantic, fills by rhythm, never rejects.
    tr.step("agent_b", "fail", violations=violations)
    fb = _allocate(template, asset_db, cfg, use_semantic=False, fallback_used=True, tr=tr)
    tr.finish("FALLBACK", {"why": violations,
                           "how": "rhythm-only forced allocation (semantic dropped)",
                           "fallback_used": True,
                           "picks": [[c.slot_id, c.seg_id] for c in fb.clips]})
    return fb
