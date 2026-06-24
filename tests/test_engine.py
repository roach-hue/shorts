"""Engine behaviour tests.

TRUNK (this task): forced reuse + source-insufficient reject must pass.
BRANCH (next task): obvious-winner needs a semantic_vector on Cut (a schema/contract
decision) -> skipped until that decision is made. See CLAUDE.md rule 3/4.
"""
import pytest

from fallback_engine.config import Thresholds
from fallback_engine.engine import assemble
from fallback_engine.invariants import check_all
from fallback_engine.schemas import EditInstruction, Reject
from fixtures import (
    scenario_forced_reuse,
    scenario_obvious_winner,
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
    assert isinstance(result, Reject)  # RULE 7
    assert result.code == "SOURCE_INSUFFICIENT"


@pytest.mark.skip(reason="STEP 3b (next task): needs a Cut.semantic_vector decision for Agent A cosine")
def test_obvious_winner_lands_in_slot_one():
    t, a = scenario_obvious_winner()
    result = assemble(t, a, CFG)
    assert isinstance(result, EditInstruction)
    assert result.clips[0].seg_id == "match"  # answer forced by construction
