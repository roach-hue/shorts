"""Core Engine entry point (Agent A -> Agent B -> Fallback).

STEP 3b: greedy slot-fixed allocation scoring on 3 axes -- semantic (RULE 6,
cosine over the cut/segment vectors), motion fit, and duration fit -- with Soft
Penalty reuse (RULE 10). Slot order is absolute (RULE 4): cuts are filled in
template order and each strict slot is pinned to its template beat (RULE 8/12).
When a cut carries no semantic_vector the semantic axis simply contributes 0.
"""
from __future__ import annotations

import math

from . import invariants
from .config import Thresholds
from .schemas import AssetDB, EditClip, EditInstruction, Reject, Template

# Coarse motion targets per template motion label. seg.motion_score is in [0, 1].
_MOTION_TARGET = {
    "static": 0.0,
    "medium": 0.5,
    "high": 1.0,
}


def _motion_target(label: str) -> float:
    """Map a template motion label to a target motion_score in [0, 1]."""
    return _MOTION_TARGET.get((label or "static").lower(), 0.5)


def _motion_fit(cut, seg) -> float:
    """Closeness of seg.motion_score to the cut's desired motion (1.0 == exact)."""
    target = _motion_target(cut.visual.motion)
    return 1.0 - abs(seg.motion_score - target)


def _duration_fit(cut, seg) -> float:
    """Can the segment cover the slot? >= slot duration -> 1.0, else proportional.

    A segment shorter than the slot can still be used (speed-compressed), so it is
    penalised proportionally rather than excluded.
    """
    if cut.duration <= 0:
        return 1.0
    if seg.duration >= cut.duration:
        return 1.0
    return seg.duration / cut.duration


def _semantic_fit(cut, seg) -> float:
    """Cosine similarity between the cut's required-visual vector and the segment
    vector (RULE 6), clamped to [0, 1]. 0 when either side has no usable vector."""
    cv, sv = cut.semantic_vector, seg.semantic_vector
    if not cv or not sv or len(cv) != len(sv):
        return 0.0
    dot = sum(a * b for a, b in zip(cv, sv))
    ncv = math.sqrt(sum(a * a for a in cv))
    nsv = math.sqrt(sum(b * b for b in sv))
    if ncv == 0.0 or nsv == 0.0:
        return 0.0
    return max(0.0, dot / (ncv * nsv))


def _score(cut, seg, used_ids: set[str], cfg: Thresholds) -> float:
    """Weighted 3-axis fit score for placing `seg` into `cut` (RULE 6 weights:
    semantic 50% / motion 30% / duration 20%).

    Reused segments are softly penalised (RULE 10) but never permanently discarded.
    """
    base = (
        cfg.semantic_weight * _semantic_fit(cut, seg)
        + cfg.motion_weight * _motion_fit(cut, seg)
        + cfg.duration_weight * _duration_fit(cut, seg)
    )
    if seg.seg_id in used_ids:
        base *= cfg.soft_penalty_factor
    return base


def _agent_a_assemble(
    template: Template, asset_db: AssetDB, cfg: Thresholds
) -> EditInstruction:
    """Agent A: greedy, slot-fixed allocation (RULE 4) using the 3-axis score."""
    # Flatten every segment together with its owning asset (for source_file).
    candidates = [
        (asset, seg) for asset in asset_db.assets for seg in asset.segments
    ]

    used_ids: set[str] = set()
    clips: list[EditClip] = []

    # RULE 4: slots filled strictly in template order; pick the best segment per slot.
    for cut in template.cuts:
        best_asset, best_seg, best_score = None, None, None
        for asset, seg in candidates:
            s = _score(cut, seg, used_ids, cfg)
            if best_score is None or s > best_score:
                best_asset, best_seg, best_score = asset, seg, s

        # RULE 8/12: fill the slot to its exact duration, pinned to the beat.
        available = best_seg.out - best_seg.in_
        if available >= cut.duration:
            # Smart Trim: take exactly the slot duration at native speed.
            out_point = best_seg.in_ + cut.duration
            speed = 1.0
        else:
            # Compress with speed so rendered length == slot duration.
            out_point = best_seg.out
            speed = available / cut.duration

        clips.append(
            EditClip(
                slot_id=cut.cut_id,
                source_file=best_asset.file_name,
                seg_id=best_seg.seg_id,
                in_=best_seg.in_,
                out=out_point,
                timeline_position=cut.in_,  # strict: pinned to template beat
                speed=speed,
                keep_audio=cut.keep_audio,
                fallback_used=False,
                re_sync_applied=False,
            )
        )
        used_ids.add(best_seg.seg_id)

    return EditInstruction(
        total_duration=template.total_duration,
        is_original_sync_broken=False,
        clips=clips,
    )


def agent_b_validate(
    template: Template, edit: EditInstruction, cfg: Thresholds
) -> list[str]:
    """Agent B: 1-Hit rhythm fact-check on Agent A's candidate (RULE 12).

    Strict slots must transition on a template beat (+/- beat_tolerance); flexible
    slots bypass the beat check. The assembled timeline must also reach the template
    runtime. Returns a list of violations (empty == accepted).
    """
    violations: list[str] = []
    cut_by_id = {c.cut_id: c for c in template.cuts}
    beats = template.beat_timestamps

    for clip in edit.clips:
        cut = cut_by_id.get(clip.slot_id)
        if cut is None or cut.slot_mode != "strict":
            continue  # flexible mode: beat check bypassed (RULE 12)
        if beats:
            nearest = min(abs(clip.timeline_position - b) for b in beats)
            if nearest > cfg.beat_tolerance_sec:
                violations.append(
                    f"AgentB RULE12: slot {clip.slot_id} transition "
                    f"{clip.timeline_position:.3f}s is {nearest:.3f}s off the nearest "
                    f"beat (> {cfg.beat_tolerance_sec}s)"
                )

    if edit.clips:
        end = max(
            c.timeline_position + (c.out - c.in_) / (c.speed or 1.0)
            for c in edit.clips
        )
        if end < template.total_duration - cfg.beat_tolerance_sec:
            violations.append(
                f"AgentB length: assembled {end:.3f}s < template "
                f"{template.total_duration:.3f}s"
            )

    return violations


def assemble(
    template: Template,
    asset_db: AssetDB,
    cfg: "Thresholds | None" = None,
) -> "EditInstruction | Reject":
    """Orchestrate Agent A -> Agent B -> (Fallback).

    RULE 7 input gate, then Agent A assembles a candidate, then Agent B fact-checks
    it once (RULE 12, 1-Hit). On rejection there is NO re-search -- control passes to
    Fallback. Fallback is the next task, so a rejected candidate currently surfaces as
    a Reject(AGENT_B_REJECTED) placeholder.
    """
    cfg = cfg or Thresholds.load()

    # RULE 7: abuse floor -- not enough total source to honestly fill anything.
    if invariants.is_source_insufficient(asset_db, cfg):
        total = invariants.total_segment_seconds(asset_db)
        return Reject(
            code="SOURCE_INSUFFICIENT",
            reason=(
                f"total source {total:.3f}s is below the minimum "
                f"{cfg.min_source_total_sec:.3f}s required to assemble a fallback"
            ),
        )

    candidate = _agent_a_assemble(template, asset_db, cfg)

    violations = agent_b_validate(template, candidate, cfg)
    if not violations:
        return candidate

    # RULE 12: 1-Hit -- no second search. Fallback (next task) will intercept here.
    return Reject(code="AGENT_B_REJECTED", reason="; ".join(violations))
