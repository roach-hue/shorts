"""Synthetic, forced test inputs + reference good/bad outputs for testing the oracle.

These are video-INDEPENDENT. Real extracted templates (from the reference Shorts)
get plugged in later as additional JSON fixtures -- swapping them never touches the
invariants. The forced scenarios are designed so the *correct* engine behaviour is
unambiguous by construction (no taste required).
"""
from __future__ import annotations

from fallback_engine.schemas import (
    Asset,
    AssetDB,
    Cut,
    EditClip,
    EditInstruction,
    Segment,
    Template,
    Visual,
)


def _vis(shot: str = "close_up", objects=("food",), motion: str = "static") -> Visual:
    return Visual(shot_type=shot, objects=list(objects), motion=motion)


def _cut(cut_id: int, start: float, dur: float, mode: str = "strict", **kw) -> Cut:
    return Cut(
        cut_id=cut_id,
        in_=start,
        out=start + dur,
        duration=dur,
        slot_mode=mode,
        max_duration=kw.get("max_duration", dur * 2.5),
        keep_audio=kw.get("keep_audio", True),
        visual=kw.get("visual", _vis()),
        semantic_vector=list(kw.get("semantic_vector", [])),
    )


def _seg(seg_id: str, dur: float, vec, motion: float = 0.3, shot: str = "close_up", objects=("food",)) -> Segment:
    return Segment(
        seg_id=seg_id,
        in_=0.0,
        out=dur,
        duration=dur,
        visual=_vis(shot, objects),
        motion_score=motion,
        semantic_vector=list(vec),
    )


# --------------------------------------------------------------------------- #
# templates
# --------------------------------------------------------------------------- #


def happy_template() -> Template:
    """Two strict slots, beats at 0.0 / 1.5 / 4.0s."""
    return Template(
        template_id="t_happy",
        total_duration=4.0,
        bpm=120,
        beat_timestamps=[0.0, 1.5, 4.0],
        cuts=[_cut(1, 0.0, 1.5, "strict"), _cut(2, 1.5, 2.5, "strict")],
    )


# --------------------------------------------------------------------------- #
# reference outputs -- used to test the ORACLE itself (no engine needed)
# --------------------------------------------------------------------------- #


def good_output(template: Template) -> EditInstruction:
    """An EditInstruction that satisfies every universal invariant."""
    return EditInstruction(
        total_duration=4.0,
        is_original_sync_broken=False,
        clips=[
            EditClip(slot_id=1, source_file="a.mp4", seg_id="a0", in_=0.0, out=1.5,
                     timeline_position=0.0, speed=1.0, keep_audio=True),
            EditClip(slot_id=2, source_file="a.mp4", seg_id="a1", in_=0.0, out=2.5,
                     timeline_position=1.5, speed=1.0, keep_audio=True),
        ],
    )


def bad_order_output(template: Template) -> EditInstruction:
    """Violates RULE 4 (slot order reversed)."""
    out = good_output(template)
    out.clips[0].slot_id, out.clips[1].slot_id = 2, 1
    return out


def bad_sync_flag_output(template: Template) -> EditInstruction:
    """Violates RULE 13 (re_sync set but sync-broken flag not raised)."""
    out = good_output(template)
    out.clips[0].re_sync_applied = True
    return out


# --------------------------------------------------------------------------- #
# forced input scenarios -- for the engine (STEP 3)
# --------------------------------------------------------------------------- #


def scenario_source_insufficient() -> tuple[Template, AssetDB]:
    """Total source (3.0s) below the abuse floor -> engine MUST Reject (RULE 7)."""
    t = happy_template()
    a = AssetDB(assets=[Asset(clip_id="c", file_name="c.mp4", duration=3.0,
                              segments=[_seg("c0", 3.0, [1, 0, 0, 0, 0])])])
    return t, a


def scenario_forced_reuse() -> tuple[Template, AssetDB]:
    """One usable segment, two slots -> engine MUST reuse it (RULE 10, bookend)."""
    t = happy_template()
    a = AssetDB(assets=[Asset(clip_id="c", file_name="c.mp4", duration=30.0,
                              segments=[_seg("c0", 30.0, [1, 0, 0, 0, 0])])])
    return t, a


def scenario_obvious_winner() -> tuple[Template, AssetDB]:
    """Slot 1 wants vector [1,0,0,0,0]; one segment matches it, the other is
    orthogonal garbage. The matching segment MUST win slot 1 (forced by cosine).
    Total source (6.0s) clears the RULE 7 floor so we actually allocate."""
    t = Template(
        template_id="t_winner",
        total_duration=4.0,
        bpm=120,
        beat_timestamps=[0.0, 1.5, 4.0],
        cuts=[
            _cut(1, 0.0, 1.5, "strict", semantic_vector=[1, 0, 0, 0, 0],
                 visual=_vis("close_up", ("food",), "static")),
            _cut(2, 1.5, 2.5, "strict", semantic_vector=[0, 0, 0, 0, 1],
                 visual=_vis("wide", ("sky",), "static")),
        ],
    )
    a = AssetDB(
        assets=[
            Asset(clip_id="c", file_name="c.mp4", duration=10.0, segments=[
                _seg("match", 3.0, [1, 0, 0, 0, 0], shot="close_up", objects=("food",)),
                _seg("garbage", 3.0, [0, 0, 0, 0, 1], shot="wide", objects=("sky",)),
            ]),
        ]
    )
    return t, a


def scenario_offbeat_strict() -> tuple[Template, AssetDB]:
    """A strict template whose 2nd transition (1.5s) lands off every beat
    {0, 2, 4}. Agent A pins it there mechanically, but Agent B (RULE 12,
    +/- beat_tolerance) must reject -> control would pass to Fallback."""
    t = Template(
        template_id="t_offbeat",
        total_duration=4.0,
        bpm=120,
        beat_timestamps=[0.0, 2.0, 4.0],  # no beat near 1.5
        cuts=[
            _cut(1, 0.0, 1.5, "strict"),  # transition at 0.0 -> on beat
            _cut(2, 1.5, 2.5, "strict"),  # transition at 1.5 -> 0.5s off nearest beat
        ],
    )
    a = AssetDB(assets=[Asset(clip_id="c", file_name="c.mp4", duration=30.0,
                              segments=[_seg("c0", 30.0, [1, 0, 0, 0, 0])])])
    return t, a
