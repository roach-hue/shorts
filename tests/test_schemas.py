"""Schemas load real example data, and the closed contract rejects the old golden.

Proves contradictions (2)(3)(4): the provided edit_instruction.json (bgm + speed_ramp)
is no longer a valid output and is therefore discarded as a golden.
"""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fallback_engine.schemas import AssetDB, EditInstruction, Template

DOCS = Path(__file__).resolve().parents[1] / "docs" / "schemas"


def _load(name: str) -> dict:
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def test_template_example_loads():
    t = Template.model_validate(_load("template.json"))
    assert t.beat_timestamps  # (1) kept
    assert len(t.cuts) == 2
    assert t.cuts[0].slot_mode in ("strict", "flexible")
    assert t.cuts[0].in_ == 0.0  # alias 'in' -> in_


def test_asset_db_example_loads():
    a = AssetDB.model_validate(_load("asset_db.json"))
    assert len(a.assets) == 2
    assert a.assets[0].segments[0].semantic_vector


def test_old_edit_instruction_is_rejected():
    # (2)(3)(4): provided golden has a bgm block + speed_ramp arrays; the closed
    # output contract forbids them, so it cannot be used as a golden any more.
    with pytest.raises(ValidationError):
        EditInstruction.model_validate(_load("edit_instruction.json"))
