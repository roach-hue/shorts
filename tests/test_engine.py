"""Engine behaviour tests.

Forced-by-construction scenarios covering RULE 7 (reject), RULE 10 (reuse), RULE 6
(semantic cosine), RULE 12 (Agent B 1-Hit + Fallback), and the non-stop guarantee.
"""
from fallback_engine.config import Thresholds
from fallback_engine.engine import agent_b_validate, assemble
from fallback_engine.invariants import check_all
from fallback_engine.schemas import EditInstruction, Reject
from fixtures import (
    scenario_forced_reuse,
    scenario_obvious_winner,
    scenario_offbeat_strict,
    scenario_source_insufficient,
)

CFG = Thresholds()


def test_forced_reuse_output_is_valid_and_repeats_segment():
    t, a = scenario_forced_reuse()
    result = assemble(t, a, CFG)
    assert isinstance(result, EditInstruction)
    assert check_all(t, a, result, CFG) == []
    seg_ids = [c.seg_id for c in result.clips]
    assert len(set(seg_ids)) < len(seg_ids)  # RULE 10: reuse forced (bookend)


def test_source_insufficient_rejects():
    t, a = scenario_source_insufficient()
    result = assemble(t, a, CFG)
    assert isinstance(result, Reject)  # RULE 7 -- the only reject (input gate)
    assert result.code == "SOURCE_INSUFFICIENT"


def test_obvious_winner_lands_in_slot_one():
    t, a = scenario_obvious_winner()
    result = assemble(t, a, CFG)
    assert isinstance(result, EditInstruction)
    assert check_all(t, a, result, CFG) == []
    assert result.clips[0].seg_id == "match"  # forced by cosine (semantic axis)


def test_agent_b_passes_on_beat_assembly():
    t, a = scenario_obvious_winner()
    result = assemble(t, a, CFG)
    assert agent_b_validate(t, result, CFG) == []          # no rhythm violations
    assert not any(c.fallback_used for c in result.clips)  # success path, not fallback


def test_offbeat_triggers_fallback():
    t, a = scenario_offbeat_strict()
    result = assemble(t, a, CFG)
    assert isinstance(result, EditInstruction)             # never dead-ends
    assert all(c.fallback_used for c in result.clips)      # RULE 12 reject -> Fallback
    assert check_all(t, a, result, CFG) == []              # still structurally valid


def test_sufficient_source_never_rejects():
    # Non-stop: with sufficient source the engine always returns a result.
    for scenario in (scenario_forced_reuse, scenario_obvious_winner, scenario_offbeat_strict):
        t, a = scenario()
        assert isinstance(assemble(t, a, CFG), EditInstruction)
