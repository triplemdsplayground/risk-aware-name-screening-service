"""Threshold-based decision helpers for screening results."""

from __future__ import annotations

from screening_service.schemas import CandidateMatch, ScreenResponse

REVIEW_THRESHOLD = 0.80


def decide_screening(
    candidates: list[CandidateMatch],
    threshold: float = REVIEW_THRESHOLD,
) -> ScreenResponse:
    """Return a PASS/REVIEW decision for the supplied candidates."""

    if not candidates:
        return ScreenResponse(
            decision="PASS",
            decision_reason=(
                f"No candidate matches were produced; top score did not meet the "
                f"review threshold of {threshold:.2f}."
            ),
            threshold=threshold,
            candidates=[],
        )

    top_candidate = max(candidates, key=lambda candidate: candidate.score)

    if top_candidate.score >= threshold:
        return ScreenResponse(
            decision="REVIEW",
            decision_reason=(
                f"Top candidate {top_candidate.watchlist_id} scored "
                f"{top_candidate.score:.2f}, meeting or exceeding the review "
                f"threshold of {threshold:.2f}."
            ),
            threshold=threshold,
            candidates=candidates,
        )

    return ScreenResponse(
        decision="PASS",
        decision_reason=(
            f"Top candidate {top_candidate.watchlist_id} scored "
            f"{top_candidate.score:.2f}, below the review threshold of "
            f"{threshold:.2f}."
        ),
        threshold=threshold,
        candidates=candidates,
    )
