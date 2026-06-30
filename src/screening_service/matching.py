"""Deterministic name matching and scoring helpers."""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal, Any

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


@dataclass(frozen=True)
class NameMatch:
    name: str
    name_type: Literal["primary", "alias"]
    similarity: float


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


def find_best_name_match(
    request_name: str,
    primary_name: str,
    aliases: list[str],
) -> NameMatch:
    """Return the highest-similarity primary or alias name match."""

    primary_name_normalised = normalise_name(primary_name)
    best_match = NameMatch(
        name=primary_name,
        name_type="primary",
        similarity=sequence_similarity(request_name, primary_name_normalised),
    )

    for alias in aliases:
        alias_similarity = sequence_similarity(request_name, normalise_name(alias))
        if alias_similarity > best_match.similarity:
            best_match = NameMatch(
                name=alias,
                name_type="alias",
                similarity=alias_similarity,
            )

    return best_match


def calculate_country_adjustment(
    request_country: str | None,
    record_countries: list[str],
) -> float:
    """Return the country-based score adjustment."""

    if request_country and request_country.strip().upper() in {
        country.strip().upper() for country in record_countries
    }:
        return COUNTRY_MATCH_ADJUSTMENT
    return 0.0


def calculate_birth_year_adjustment(
    request_birth_year: int | None,
    record_birth_year: int | None,
) -> float:
    """Return the birth-year score adjustment."""

    if request_birth_year is not None and record_birth_year is not None:
        if request_birth_year == record_birth_year:
            return BIRTH_YEAR_MATCH_ADJUSTMENT
        return BIRTH_YEAR_MISMATCH_ADJUSTMENT
    return 0.0


def clamp_score(score: float) -> float:
    """Clamp a score to the inclusive [0.0, 1.0] range."""

    return max(0.0, min(score, 1.0))


def build_matched_on(score_components: ScoreComponents) -> list[str]:
    """Build the matched-on reasons list."""

    matched_on: list[str] = ["name_similarity"]
    if score_components.exact_match_boost > 0.0:
        matched_on.append("exact_primary_name_match")
    if score_components.alias_exact_match_boost > 0.0:
        matched_on.append("exact_alias_match")
    if score_components.token_overlap_boost > 0.0:
        matched_on.append("token_overlap")
    if score_components.country_adjustment > 0.0:
        matched_on.append("country_match")
    if score_components.birth_year_adjustment > 0.0:
        matched_on.append("birth_year_match")
    if score_components.birth_year_adjustment < 0.0:
        matched_on.append("birth_year_mismatch")
    return matched_on


def build_explanation(
    best_match: NameMatch,
    score_components: ScoreComponents,
) -> str:
    """Build the human-readable scoring explanation."""

    explanation_parts = [
        (
            f"Best {best_match.name_type} match was '{best_match.name}' "
            f"with similarity {best_match.similarity:.2f}."
        )
    ]
    if score_components.exact_match_boost > 0.0:
        explanation_parts.append("Exact primary-name match increased the score.")
    if score_components.alias_exact_match_boost > 0.0:
        explanation_parts.append("Exact alias match increased the score.")
    if score_components.token_overlap_boost > 0.0:
        explanation_parts.append("Shared tokens increased the score.")
    if score_components.country_adjustment > 0.0:
        explanation_parts.append("Country matched the watchlist metadata.")
    if score_components.birth_year_adjustment > 0.0:
        explanation_parts.append("Birth year matched the watchlist metadata.")
    if score_components.birth_year_adjustment < 0.0:
        explanation_parts.append("Birth year mismatch reduced the score.")
    return " ".join(explanation_parts)


def score_watchlist_record(
    request: ScreenRequest,
    record: dict[str, Any],
) -> CandidateMatch:
    """Score one watchlist record against a screening request."""

    request_name = normalise_name(request.name)
    primary_name = record["primary_name"]
    best_match = find_best_name_match(
        request_name,
        primary_name,
        record.get("aliases", []),
    )

    matched_name_normalised = normalise_name(best_match.name)
    exact_match_boost = (
        EXACT_MATCH_BOOST
        if best_match.name_type == "primary" and request_name == matched_name_normalised
        else 0.0
    )
    alias_exact_match_boost = (
        ALIAS_EXACT_MATCH_BOOST
        if best_match.name_type == "alias" and request_name == matched_name_normalised
        else 0.0
    )

    token_overlap_boost = (
        calculate_token_overlap(request_name, matched_name_normalised)
        * TOKEN_OVERLAP_WEIGHT
    )

    country_adjustment = calculate_country_adjustment(
        request.country,
        record.get("countries", []),
    )
    birth_year_adjustment = calculate_birth_year_adjustment(
        request.birth_year,
        record.get("birth_year"),
    )

    raw_score = (
        best_match.similarity
        + exact_match_boost
        + alias_exact_match_boost
        + token_overlap_boost
        + country_adjustment
        + birth_year_adjustment
    )
    final_score = clamp_score(raw_score)

    score_components = ScoreComponents(
        base_name_similarity=best_match.similarity,
        exact_match_boost=exact_match_boost,
        alias_exact_match_boost=alias_exact_match_boost,
        token_overlap_boost=token_overlap_boost,
        country_adjustment=country_adjustment,
        birth_year_adjustment=birth_year_adjustment,
    )

    matched_on = build_matched_on(score_components)
    explanation = build_explanation(
        best_match=best_match,
        score_components=score_components,
    )

    return CandidateMatch(
        watchlist_id=record["watchlist_id"],
        primary_name=primary_name,
        matched_name=best_match.name,
        matched_name_type=best_match.name_type,
        entity_type=record["entity_type"],
        score=final_score,
        matched_on=matched_on,
        score_components=score_components,
        explanation=explanation,
    )
