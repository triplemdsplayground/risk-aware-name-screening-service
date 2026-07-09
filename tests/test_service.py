from screening_service.schemas import (
    CandidateMatch,
    ScoreComponents,
    ScreenRequest,
    ScreenResponse,
)
from screening_service.service import TOP_CANDIDATE_LIMIT, screen_request


def make_candidate(score: float, watchlist_id: str) -> CandidateMatch:
    return CandidateMatch(
        watchlist_id=watchlist_id,
        primary_name=f"Name {watchlist_id}",
        matched_name=f"Name {watchlist_id}",
        matched_name_type="primary",
        entity_type="person",
        score=score,
        matched_on=["name_similarity"],
        score_components=ScoreComponents(
            base_name_similarity=score,
            exact_match_boost=0.0,
            alias_exact_match_boost=0.0,
            token_overlap_boost=0.0,
            country_adjustment=0.0,
            birth_year_adjustment=0.0,
        ),
        explanation="Synthetic candidate for service tests.",
    )


def test_screen_request_returns_screen_response() -> None:
    response = screen_request(ScreenRequest(name="John A Smith"))

    assert isinstance(response, ScreenResponse)


def test_candidates_are_sorted_by_descending_score(monkeypatch) -> None:
    watchlist = [
        {"watchlist_id": "wl-1"},
        {"watchlist_id": "wl-2"},
        {"watchlist_id": "wl-3"},
    ]
    score_by_id = {
        "wl-1": 0.25,
        "wl-2": 0.90,
        "wl-3": 0.60,
    }

    monkeypatch.setattr(
        "screening_service.service.load_sample_watchlist",
        lambda: watchlist,
    )

    def fake_score_watchlist_record(
        request: ScreenRequest,
        record: dict[str, str],
    ) -> CandidateMatch:
        watchlist_id = record["watchlist_id"]
        return make_candidate(score_by_id[watchlist_id], watchlist_id)

    monkeypatch.setattr(
        "screening_service.service.score_watchlist_record",
        fake_score_watchlist_record,
    )

    response = screen_request(ScreenRequest(name="Any Name"))

    assert [candidate.watchlist_id for candidate in response.candidates] == [
        "wl-2",
        "wl-3",
        "wl-1",
    ]


def test_only_top_five_candidates_are_returned_when_more_exist(
    monkeypatch
) -> None:
    watchlist = [{"watchlist_id": f"wl-{index}"} for index in range(6)]

    monkeypatch.setattr(
        "screening_service.service.load_sample_watchlist",
        lambda: watchlist
    )

    def fake_score_watchlist_record(
        request: ScreenRequest,
        record: dict[str, str]
    ) -> CandidateMatch:
        index = int(record["watchlist_id"].split("-")[1])
        return make_candidate(float(index) / 10, record["watchlist_id"])

    monkeypatch.setattr(
        "screening_service.service.score_watchlist_record",
        fake_score_watchlist_record,
    )

    response = screen_request(ScreenRequest(name="Any Name"))

    assert len(response.candidates) == TOP_CANDIDATE_LIMIT
    assert [candidate.watchlist_id for candidate in response.candidates] == [
        "wl-5",
        "wl-4",
        "wl-3",
        "wl-2",
        "wl-1",
    ]


def test_strong_match_returns_review() -> None:
    response = screen_request(ScreenRequest(
        name="John A Smith",
        country="GB",
        birth_year=1980
    ))

    assert response.decision == "REVIEW"
    assert response.candidates[0].watchlist_id == "wl-001"


def test_weak_request_returns_pass() -> None:
    response = screen_request(ScreenRequest(
        name="Completely Different Person",
        country="ZZ",
        birth_year=1999
    ))

    assert response.decision == "PASS"
    assert response.candidates
    assert response.candidates[0].score < response.threshold
