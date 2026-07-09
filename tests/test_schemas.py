from datetime import date

import pytest
from pydantic import ValidationError

from screening_service.schemas import (
    CandidateMatch,
    ScoreComponents,
    ScreenRequest,
    ScreenResponse,
)


def build_score_components() -> ScoreComponents:
    return ScoreComponents(
        base_name_similarity=0.81,
        exact_match_boost=0.1,
        alias_exact_match_boost=0.0,
        token_overlap_boost=0.05,
        country_adjustment=0.03,
        birth_year_adjustment=-0.02,
    )


def build_candidate_match() -> CandidateMatch:
    return CandidateMatch(
        watchlist_id="wl-001",
        primary_name="John A Smith",
        matched_name="John Smith",
        matched_name_type="alias",
        entity_type="person",
        score=0.94,
        matched_on=["name_similarity", "alias_exact_match"],
        score_components=build_score_components(),
        explanation="Strong alias match with similar primary name.",
    )


def test_screen_request_valid() -> None:
    request = ScreenRequest(name="John A Smith")

    assert request.name == "John A Smith"
    assert request.country is None
    assert request.birth_year is None


def test_screen_request_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ScreenRequest(name="")


def test_screen_request_rejects_whitespace_only_name() -> None:
    with pytest.raises(ValidationError):
        ScreenRequest(name="   ")


def test_screen_request_accepts_optional_country_and_birth_year() -> None:
    request = ScreenRequest(
        name=" Maria Elena Garcia ",
        country="MX",
        birth_year=1975,
    )

    assert request.name == "Maria Elena Garcia"
    assert request.country == "MX"
    assert request.birth_year == 1975


def test_screen_request_rejects_invalid_birth_year() -> None:
    with pytest.raises(ValidationError):
        ScreenRequest(name="John A Smith", birth_year=1899)

    with pytest.raises(ValidationError):
        ScreenRequest(name="John A Smith", birth_year=date.today().year + 1)


def test_candidate_match_accepts_score_components() -> None:
    candidate = build_candidate_match()

    assert candidate.score_components.base_name_similarity == 0.81
    assert candidate.matched_name_type == "alias"


def test_screen_response_accepts_candidates() -> None:
    candidate = build_candidate_match()
    response = ScreenResponse(
        decision="REVIEW",
        decision_reason="Top candidate exceeded threshold.",
        threshold=0.8,
        candidates=[candidate],
    )

    assert response.decision == "REVIEW"
    assert response.threshold == 0.8
    assert len(response.candidates) == 1
    assert response.candidates[0].watchlist_id == "wl-001"


def test_screen_response_rejects_invalid_decision() -> None:
    screen_response_json = {
        "decision": "ESCALATE",
        "decision_reason": "Unsupported decision.",
        "threshold": 0.8,
        "candidates": []
    }
    with pytest.raises(ValidationError):
        ScreenResponse.model_validate(screen_response_json)


def test_candidate_match_rejects_invalid_matched_name_type() -> None:
    candidate_match_json = {
            "watchlist_id": "wl-001",
            "primary_name": "John A Smith",
            "matched_name": "John Smith",
            "matched_name_type": "nickname",
            "entity_type": "person",
            "score": 0.94,
            "matched_on": ["name_similarity"],
            "score_components": build_score_components(),
            "explanation": "Invalid matched name type."
    }
    with pytest.raises(ValidationError):
        CandidateMatch.model_validate(candidate_match_json)


def test_candidate_match_rejects_invalid_score() -> None:
    with pytest.raises(ValidationError):
        CandidateMatch(
            watchlist_id="wl-001",
            primary_name="John A Smith",
            matched_name="John Smith",
            matched_name_type="alias",
            entity_type="person",
            score=1.01,
            matched_on=["name_similarity"],
            score_components=build_score_components(),
            explanation="Score above bounds.",
        )


def test_screen_response_rejects_invalid_threshold() -> None:
    with pytest.raises(ValidationError):
        ScreenResponse(
            decision="REVIEW",
            decision_reason="Threshold above bounds.",
            threshold=1.1,
            candidates=[build_candidate_match()],
        )


def test_score_components_rejects_invalid_base_name_similarity() -> None:
    with pytest.raises(ValidationError):
        ScoreComponents(
            base_name_similarity=-0.01,
            exact_match_boost=0.1,
            alias_exact_match_boost=0.0,
            token_overlap_boost=0.05,
            country_adjustment=0.03,
            birth_year_adjustment=-0.02,
        )
