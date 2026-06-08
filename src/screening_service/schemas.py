"""Pydantic schemas for the screening API contracts."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ScreenRequest(BaseModel):
    name: str
    country: str | None = None
    birth_year: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be empty or whitespace-only")
        return trimmed

    @field_validator("birth_year")
    @classmethod
    def validate_birth_year(cls, value: int | None) -> int | None:
        if value is None:
            return value

        current_year = date.today().year
        if value < 1900 or value > current_year:
            raise ValueError(
                f"birth_year must be between 1900 and {current_year}"
            )
        return value


class ScoreComponents(BaseModel):
    base_name_similarity: float = Field(ge=0.0, le=1.0)
    exact_match_boost: float
    alias_exact_match_boost: float
    token_overlap_boost: float
    country_adjustment: float
    birth_year_adjustment: float


class CandidateMatch(BaseModel):
    watchlist_id: str
    primary_name: str
    matched_name: str
    matched_name_type: Literal["primary", "alias"]
    entity_type: str
    score: float = Field(ge=0.0, le=1.0)
    matched_on: list[str] = Field(default_factory=list)
    score_components: ScoreComponents
    explanation: str


class ScreenResponse(BaseModel):
    decision: Literal["PASS", "REVIEW"]
    decision_reason: str
    threshold: float = Field(ge=0.0, le=1.0)
    candidates: list[CandidateMatch] = Field(default_factory=list)
