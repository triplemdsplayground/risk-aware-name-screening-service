"""Service-layer orchestration for screening requests."""

from __future__ import annotations

from screening_service.data_loader import load_sample_watchlist
from screening_service.decision import make_screening_decision
from screening_service.matching import score_watchlist_record
from screening_service.schemas import ScreenRequest, ScreenResponse

TOP_CANDIDATE_LIMIT = 5


def screen_request(request: ScreenRequest) -> ScreenResponse:
    """Screen a request against the bundled sample watchlist."""

    watchlist = load_sample_watchlist()
    candidates = [score_watchlist_record(request, record) for record in watchlist]
    top_candidates = sorted(
        candidates,
        key=lambda candidate: candidate.score,
        reverse=True,
    )[:TOP_CANDIDATE_LIMIT]
    return make_screening_decision(top_candidates)
