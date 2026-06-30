from screening_service.decision import REVIEW_THRESHOLD, make_screening_decision
from screening_service.schemas import CandidateMatch, ScoreComponents


def make_candidate(score: float, watchlist_id: str = "wl-001") -> CandidateMatch:
    return CandidateMatch(
        watchlist_id=watchlist_id,
        primary_name="John A Smith",
        matched_name="John A Smith",
        matched_name_type="primary",
        entity_type="person",
        score=score,
        matched_on=["name_similarity"],
        score_components=ScoreComponents(
            base_name_similarity=min(score, 1.0),
            exact_match_boost=0.0,
            alias_exact_match_boost=0.0,
            token_overlap_boost=0.0,
            country_adjustment=0.0,
            birth_year_adjustment=0.0,
        ),
        explanation="Synthetic candidate for decision tests.",
    )


def test_review_when_top_score_above_threshold() -> None:
    response = make_screening_decision(
        [
            make_candidate(0.91, watchlist_id="wl-high"),
            make_candidate(0.62, watchlist_id="wl-low"),
        ]
    )

    assert response.decision == "REVIEW"
    assert response.threshold == REVIEW_THRESHOLD


def test_review_when_top_score_equals_threshold() -> None:
    response = make_screening_decision([make_candidate(REVIEW_THRESHOLD)])

    assert response.decision == "REVIEW"


def test_pass_when_top_score_below_threshold() -> None:
    response = make_screening_decision([make_candidate(REVIEW_THRESHOLD - 0.01)])

    assert response.decision == "PASS"


def test_pass_when_candidate_list_is_empty() -> None:
    response = make_screening_decision([])

    assert response.decision == "PASS"
    assert response.candidates == []
    assert "No candidate matches were produced" in response.decision_reason


def test_decision_reason_references_threshold_and_top_score() -> None:
    response = make_screening_decision(
        [
            make_candidate(0.40, watchlist_id="wl-lower"),
            make_candidate(0.79, watchlist_id="wl-top"),
        ]
    )

    assert "0.79" in response.decision_reason
    assert f"{REVIEW_THRESHOLD:.2f}" in response.decision_reason
    assert "wl-top" in response.decision_reason
