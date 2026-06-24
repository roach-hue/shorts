"""Test the ORACLE itself: the invariants must pass good output and catch bad output.

This is the step that makes the harness trustworthy BEFORE the engine exists --
an oracle that never fails is worthless.
"""
from fallback_engine.config import Thresholds
from fallback_engine.invariants import (
    check_all,
    is_source_insufficient,
)
from fixtures import (
    bad_order_output,
    bad_sync_flag_output,
    good_output,
    happy_template,
    scenario_forced_reuse,
    scenario_source_insufficient,
)

CFG = Thresholds()


def test_oracle_passes_good_output():
    t = happy_template()
    assert check_all(t, None, good_output(t), CFG) == []


def test_oracle_catches_slot_reorder():
    t = happy_template()
    violations = check_all(t, None, bad_order_output(t), CFG)
    assert any("RULE4" in v for v in violations), violations


def test_oracle_catches_sync_flag_mismatch():
    t = happy_template()
    violations = check_all(t, None, bad_sync_flag_output(t), CFG)
    assert any("RULE13" in v for v in violations), violations


def test_source_insufficient_predicate():
    # RULE 7 gate works now (no engine needed).
    _, a_small = scenario_source_insufficient()
    assert is_source_insufficient(a_small, CFG) is True
    _, a_big = scenario_forced_reuse()
    assert is_source_insufficient(a_big, CFG) is False
