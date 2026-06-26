"""The oracle, as code: RULEs expressed as checkable invariants over engine output.

check_all() returns a list of human-readable violation strings (empty == valid).
These are video-INDEPENDENT and threshold-driven. The core RULE invariants are LAW
(change only via deliberate spec revision); thresholds are config knobs.

Mapping (see schema_decisions.md / decisions/schema_contradictions.md):
  RULE 4  -> inv_slot_order_preserved      (template cut order is absolute)
  RULE 7  -> is_source_insufficient        (abuse-floor reject gate)
  RULE 8  -> inv_strict_slot_pinned        (strict slot fills its duration)
  RULE 12 -> inv_strict_slot_pinned        (strict slot pinned to beat position)
  RULE 13 -> inv_sync_broken_flag          (sync-broken flag <=> re_sync OR off-beat)
  (3)     -> inv_speed_scalar_positive     (speed is a positive scalar)
"""
from __future__ import annotations

from .config import Thresholds
from .schemas import AssetDB, EditInstruction, Template

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def total_segment_seconds(asset_db: AssetDB) -> float:
    return sum(seg.duration for a in asset_db.assets for seg in a.segments)


def is_source_insufficient(asset_db: AssetDB, cfg: Thresholds) -> bool:
    """RULE 7 abuse gate: total user source below the absolute floor -> Reject."""
    return total_segment_seconds(asset_db) < cfg.min_source_total_sec


def offbeat_strict_slots(
    template: Template, edit: EditInstruction, cfg: Thresholds
) -> list[tuple[int, float]]:
    """[(slot_id, offset_sec)] for strict clips whose transition lands off every
    template beat (> beat_tolerance). The single source of truth for "is the rhythm
    intact?" -- shared by Agent B, the sync-broken flag, and the RULE 13 invariant."""
    result: list[tuple[int, float]] = []
    cut_by_id = {c.cut_id: c for c in template.cuts}
    beats = template.beat_timestamps
    if not beats:
        return result
    for clip in edit.clips:
        cut = cut_by_id.get(clip.slot_id)
        if cut is None or cut.slot_mode != "strict":
            continue
        nearest = min(abs(clip.timeline_position - b) for b in beats)
        if nearest > cfg.beat_tolerance_sec:
            result.append((clip.slot_id, nearest))
    return result


# --------------------------------------------------------------------------- #
# invariants over a produced EditInstruction
# --------------------------------------------------------------------------- #


def inv_slot_order_preserved(template: Template, result: EditInstruction) -> list[str]:
    """RULE 4: output slot order == template cut order, exactly."""
    cut_ids = [c.cut_id for c in template.cuts]
    slot_ids = [c.slot_id for c in result.clips]
    if slot_ids != cut_ids:
        return [f"RULE4 (slot order): {slot_ids} != template cut order {cut_ids}"]
    return []


def inv_all_slots_filled(template: Template, result: EditInstruction) -> list[str]:
    if len(result.clips) != len(template.cuts):
        return [f"slots filled {len(result.clips)} != template cuts {len(template.cuts)}"]
    return []


def inv_timeline_monotonic(result: EditInstruction) -> list[str]:
    """Timeline positions never go backwards; clips do not overlap."""
    v: list[str] = []
    prev_end = None
    for clip in result.clips:
        if prev_end is not None and clip.timeline_position < prev_end - 1e-6:
            v.append(
                f"timeline: slot {clip.slot_id} starts {clip.timeline_position:.3f} "
                f"before previous end {prev_end:.3f}"
            )
        speed = clip.speed if clip.speed else 1.0
        rendered = (clip.out - clip.in_) / speed
        prev_end = clip.timeline_position + rendered
    return v


def inv_strict_slot_pinned(
    template: Template, result: EditInstruction, cfg: Thresholds
) -> list[str]:
    """RULE 12 + RULE 8: strict (beat-priority) slots stay pinned to the template
    beat position and fill the slot duration exactly (within beat tolerance)."""
    v: list[str] = []
    cut_by_id = {c.cut_id: c for c in template.cuts}
    for clip in result.clips:
        cut = cut_by_id.get(clip.slot_id)
        if cut is None or cut.slot_mode != "strict":
            continue
        if abs(clip.timeline_position - cut.in_) > cfg.beat_tolerance_sec:
            v.append(
                f"RULE12 (strict pin): slot {clip.slot_id} pos {clip.timeline_position:.3f} "
                f"not within {cfg.beat_tolerance_sec}s of pinned {cut.in_:.3f}"
            )
        speed = clip.speed if clip.speed else 1.0
        rendered = (clip.out - clip.in_) / speed
        if abs(rendered - cut.duration) > cfg.beat_tolerance_sec:
            v.append(
                f"RULE8 (strict fill): slot {clip.slot_id} rendered {rendered:.3f}s "
                f"!= slot {cut.duration:.3f}s"
            )
    return v


def inv_sync_broken_flag(
    template: Template, result: EditInstruction, cfg: Thresholds
) -> list[str]:
    """RULE 13: is_original_sync_broken is true iff the output's rhythm is compromised
    -- by a Cascading Shift (any re_sync_applied) OR by an off-beat strict slot that
    Fallback could not fix. The flag must honestly reflect that state."""
    expected = (
        any(c.re_sync_applied for c in result.clips)
        or bool(offbeat_strict_slots(template, result, cfg))
    )
    if result.is_original_sync_broken != expected:
        return [
            f"RULE13: is_original_sync_broken={result.is_original_sync_broken} "
            f"but expected {expected} (re_sync or off-beat strict slot)"
        ]
    return []


def inv_speed_scalar_positive(result: EditInstruction) -> list[str]:
    """(3): speed is a positive scalar (no speed_ramp arrays)."""
    v: list[str] = []
    for c in result.clips:
        if isinstance(c.speed, bool) or not isinstance(c.speed, (int, float)):
            v.append(f"slot {c.slot_id}: speed must be a scalar, got {c.speed!r}")
        elif c.speed <= 0:
            v.append(f"slot {c.slot_id}: speed must be > 0, got {c.speed}")
    return v


def check_all(
    template: Template,
    asset_db: "AssetDB | None",
    result: EditInstruction,
    cfg: Thresholds,
) -> list[str]:
    """Run every universal invariant. Empty list == valid output."""
    v: list[str] = []
    v += inv_slot_order_preserved(template, result)
    v += inv_all_slots_filled(template, result)
    v += inv_timeline_monotonic(result)
    v += inv_strict_slot_pinned(template, result, cfg)
    v += inv_sync_broken_flag(template, result, cfg)
    v += inv_speed_scalar_positive(result)
    return v
