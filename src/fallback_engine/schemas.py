"""Data contracts for the Fallback Engine (contradictions (1)-(5) closed).

See decisions/schema_contradictions.md. Summary:
  (1) beat_timestamps kept (no audio file stored).
  (2) NO bgm field on the output contract (BGM is never written).
  (3) speed is a scalar float (speed_ramp deferred / out of MVP scope).
  (4) provided edit_instruction.json golden discarded; synthetic goldens used.
  (5) all time fields are SECONDS (float); +/-100ms tolerance lives in config (0.1s).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# shared
# --------------------------------------------------------------------------- #


class Visual(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shot_type: str
    objects: list[str] = Field(default_factory=list)
    motion: str = "static"


class SubtitleStyle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_highlighted: bool = False
    animation: Optional[str] = None


class Subtitle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    position: str = "center"
    in_: float = Field(alias="in")
    out: float
    style: SubtitleStyle = Field(default_factory=SubtitleStyle)


# --------------------------------------------------------------------------- #
# template.json (input)
# --------------------------------------------------------------------------- #


class Cut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cut_id: int
    in_: float = Field(alias="in")
    out: float
    duration: float
    slot_mode: Literal["strict", "flexible"]  # RULE 13: per-slot beat/narrative mode
    max_duration: float
    keep_audio: bool = True  # RULE 9
    visual: Visual
    # STEP 3b: required-visual embedding for Agent A cosine (RULE 6).
    # Empty list => semantic axis simply contributes 0 (backward compatible).
    semantic_vector: list[float] = Field(default_factory=list)
    audio: Optional[str] = None  # descriptive only; timing comes from beat_timestamps (1)
    subtitle: Optional[Subtitle] = None


class Template(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    template_id: str
    total_duration: float
    bpm: float = Field(alias="BPM")
    beat_timestamps: list[float] = Field(default_factory=list)  # SECONDS (5), kept (1)
    cuts: list[Cut]


# --------------------------------------------------------------------------- #
# asset_db.json (input)
# --------------------------------------------------------------------------- #


class Segment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    seg_id: str
    in_: float = Field(alias="in")
    out: float
    duration: float
    visual: Visual
    motion_score: float = Field(ge=0.0, le=1.0)
    semantic_vector: list[float] = Field(default_factory=list)  # dim-agnostic (toy 5-d or real 384-d)


class Asset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clip_id: str
    file_name: str
    duration: float
    audio_waveform: list[float] = Field(default_factory=list)
    segments: list[Segment]


class AssetDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assets: list[Asset]


# --------------------------------------------------------------------------- #
# edit_instruction.json (OUTPUT contract -- strict)
# --------------------------------------------------------------------------- #


class EditClip(BaseModel):
    # extra='forbid' enforces (2)(3): no bgm-era fields, no speed_ramp.
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    slot_id: int
    source_file: str
    seg_id: str
    in_: float = Field(alias="in")
    out: float
    timeline_position: float  # SECONDS on the output timeline
    speed: float = 1.0  # (3) scalar only
    keep_audio: bool = True
    fallback_used: bool = False  # RULE 12
    # True iff repositioned by a preceding flexible-mode Cascading Shift (RULE 8/13)
    re_sync_applied: bool = False
    subtitle: Optional[Subtitle] = None


class EditInstruction(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")  # (2) no bgm

    total_duration: float
    is_original_sync_broken: bool = False  # RULE 13
    clips: list[EditClip]


# --------------------------------------------------------------------------- #
# reject (RULE 7)
# --------------------------------------------------------------------------- #


class Reject(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    reason: str
