"""Deterministic name matching and scoring helpers."""

from __future__ import annotations

import re
import string
from difflib import SequenceMatcher
from typing import Any

from screening_service.schemas import (
    CandidateMatch,
    ScoreComponents,
    ScreenRequest,
)

EXACT_MATCH_BOOST = 0.12
ALIAS_EXACT_MATCH_BOOST = 0.1
TOKEN_OVERLAP_WEIGHT = 0.08
COUNTRY_MATCH_ADJUSTMENT = 0.05
BIRTH_YEAR_MATCH_ADJUSTMENT = 0.05
BIRTH_YEAR_MISMATCH_ADJUSTMENT = -0.05

_PUNCTUATION_TABLE = str.maketrans("", "", string.punctuation)


def normalise_name(name: str) -> str:
    """normalise names for deterministic comparison."""

    normalised = name.lower().strip()
    normalised = normalised.translate(_PUNCTUATION_TABLE)
    normalised = re.sub(r"\s+", " ", normalised)
    return normalised


def calculate_token_overlap(left: str, right: str) -> float:
    """Return token overlap ratio between two normalised names."""

    left_tokens = set(left.split())
    right_tokens = set(right.split())

    if not left_tokens or not right_tokens:
        return 0.0

    overlap_count = len(left_tokens & right_tokens)
    return overlap_count / max(len(left_tokens), len(right_tokens))


def sequence_similarity(left: str, right: str) -> float:
    """Return a stdlib string similarity score."""

    return SequenceMatcher(None, left, right).ratio()


def score_watchlist_record(
    request: ScreenRequest,
    record: dict[str, Any],
) -> CandidateMatch:
    """Score one watchlist record against a screening request."""

    request_name = normalise_name(request.name)
    primary_name = record["primary_name"]
    primary_name_normalised = normalise_name(primary_name)

    best_name = primary_name
    best_name_type = "primary"
    best_similarity = sequence_similarity(
        request_name, 
        primary_name_normalised
    )

    for alias in record.get("aliases", []):
        alias_normalised = normalise_name(alias)
        alias_similarity = sequence_similarity(request_name, alias_normalised)
        if alias_similarity > best_similarity:
            best_name = alias
            best_name_type = "alias"
            best_similarity = alias_similarity

    matched_name_normalised = normalise_name(best_name)
    exact_match_boost = (
        EXACT_MATCH_BOOST
        if best_name_type == "primary" and request_name == matched_name_normalised
        else 0.0
    )
    alias_exact_match_boost = (
        ALIAS_EXACT_MATCH_BOOST
        if best_name_type == "alias" and request_name == matched_name_normalised
        else 0.0
    )

    token_overlap_boost = (
        calculate_token_overlap(request_name, matched_name_normalised)
        * TOKEN_OVERLAP_WEIGHT
    )

    country_adjustment = 0.0
    if request.country and request.country in record.get("countries", []):
        country_adjustment = COUNTRY_MATCH_ADJUSTMENT

    birth_year_adjustment = 0.0
    record_birth_year = record.get("birth_year")
    if request.birth_year is not None and record_birth_year is not None:
        if request.birth_year == record_birth_year:
            birth_year_adjustment = BIRTH_YEAR_MATCH_ADJUSTMENT
        else:
            birth_year_adjustment = BIRTH_YEAR_MISMATCH_ADJUSTMENT

    raw_score = (
        best_similarity
        + exact_match_boost
        + alias_exact_match_boost
        + token_overlap_boost
        + country_adjustment
        + birth_year_adjustment
    )
    final_score = max(0.0, min(raw_score, 1.0))

    score_components = ScoreComponents(
        base_name_similarity=best_similarity,
        exact_match_boost=exact_match_boost,
        alias_exact_match_boost=alias_exact_match_boost,
        token_overlap_boost=token_overlap_boost,
        country_adjustment=country_adjustment,
        birth_year_adjustment=birth_year_adjustment,
    )

    matched_on: list[str] = ["name_similarity"]
    if exact_match_boost > 0.0:
        matched_on.append("exact_primary_name_match")
    if alias_exact_match_boost > 0.0:
        matched_on.append("exact_alias_match")
    if token_overlap_boost > 0.0:
        matched_on.append("token_overlap")
    if country_adjustment > 0.0:
        matched_on.append("country_match")
    if birth_year_adjustment > 0.0:
        matched_on.append("birth_year_match")
    if birth_year_adjustment < 0.0:
        matched_on.append("birth_year_mismatch")

    explanation_parts = [
        f"Best {best_name_type} match was '{best_name}' with similarity {best_similarity:.2f}."
    ]
    if exact_match_boost > 0.0:
        explanation_parts.append("Exact primary-name match increased the score.")
    if alias_exact_match_boost > 0.0:
        explanation_parts.append("Exact alias match increased the score.")
    if token_overlap_boost > 0.0:
        explanation_parts.append("Shared tokens increased the score.")
    if country_adjustment > 0.0:
        explanation_parts.append("Country matched the watchlist metadata.")
    if birth_year_adjustment > 0.0:
        explanation_parts.append("Birth year matched the watchlist metadata.")
    if birth_year_adjustment < 0.0:
        explanation_parts.append("Birth year mismatch reduced the score.")

    return CandidateMatch(
        watchlist_id=record["watchlist_id"],
        primary_name=primary_name,
        matched_name=best_name,
        matched_name_type=best_name_type,
        entity_type=record["entity_type"],
        score=final_score,
        matched_on=matched_on,
        score_components=score_components,
        explanation=" ".join(explanation_parts),
    )
