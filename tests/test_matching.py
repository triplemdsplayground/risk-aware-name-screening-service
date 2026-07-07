from screening_service.data_loader import WatchlistEntry
from screening_service.matching import (
    BIRTH_YEAR_MISMATCH_ADJUSTMENT,
    BIRTH_YEAR_MATCH_ADJUSTMENT,
    COUNTRY_MATCH_ADJUSTMENT,
    calculate_token_overlap,
    normalise_name,
    score_watchlist_record,
)
from screening_service.schemas import ScreenRequest




def make_record(
    *,
    watchlist_id: str = "wl-test",
    primary_name: str = "John A Smith",
    entity_type: str = "person",
    aliases: list[str] | None = None,
    countries: list[str] | None = None,
    birth_year: int | None = 1980,
    risk_notes: str = "Synthetic test record.",
) -> WatchlistEntry:
    return {
        "watchlist_id": watchlist_id,
        "primary_name": primary_name,
        "entity_type": entity_type,
        "aliases": (
            aliases if aliases is not None else ["John Smith", "J A Smith"]
        ),
        "countries": countries if countries is not None else ["GB"],
        "birth_year": birth_year,
        "risk_notes": risk_notes,
    }


def test_normalise_name_lowercases_and_trims() -> None:
    assert normalise_name("  John A Smith  ") == "john a smith"


def test_normalise_name_removes_punctuation() -> None:
    assert normalise_name("Smith, J^oh&n A.") == "smith john a"


def test_normalise_name_collapses_whitespace() -> None:
    assert normalise_name("John   A\t Smith") == "john a smith"


def test_calculate_token_overlap_returns_ratio() -> None:
    assert calculate_token_overlap("john a smith", "john smith") == 2 / 3


def test_exact_primary_name_match() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith"),
        make_record(),
    )

    assert candidate.matched_name == "John A Smith"
    assert candidate.matched_name_type == "primary"
    assert candidate.score_components.exact_match_boost > 0.0
    assert candidate.score_components.alias_exact_match_boost == 0.0


def test_exact_alias_match() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John Smith"),
        make_record(),
    )

    assert candidate.matched_name == "John Smith"
    assert candidate.matched_name_type == "alias"
    assert candidate.score_components.alias_exact_match_boost > 0.0
    assert candidate.score_components.exact_match_boost == 0.0


def test_near_match_uses_similarity() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="Jon Smyth"),
        make_record(primary_name="John Smith", aliases=[]),
    )

    assert candidate.score_components.base_name_similarity > 0.7
    assert candidate.score_components.exact_match_boost == 0.0
    assert candidate.score > 0.0


def test_country_match_adjustment() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith", country="GB"),
        make_record(),
    )

    assert candidate.score_components.country_adjustment == COUNTRY_MATCH_ADJUSTMENT
    assert "country_match" in candidate.matched_on


def test_country_match_adjustment_normalises_country_input() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith", country=" gb "),
        make_record(countries=["GB"]),
    )

    assert candidate.score_components.country_adjustment == COUNTRY_MATCH_ADJUSTMENT
    assert "country_match" in candidate.matched_on


def test_birth_year_match_adjustment() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith", birth_year=1980),
        make_record(),
    )

    assert candidate.score_components.birth_year_adjustment == BIRTH_YEAR_MATCH_ADJUSTMENT
    assert "birth_year_match" in candidate.matched_on


def test_birth_year_mismatch_penalty() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith", birth_year=1981),
        make_record(),
    )

    assert candidate.score_components.birth_year_adjustment == BIRTH_YEAR_MISMATCH_ADJUSTMENT
    assert "birth_year_mismatch" in candidate.matched_on


def test_final_score_never_exceeds_one() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith", country="GB", birth_year=1980),
        make_record(),
    )

    assert candidate.score == 1.0


def test_final_score_never_goes_below_zero() -> None:
    candidate = score_watchlist_record(
        ScreenRequest(name="X", birth_year=1981),
        make_record(primary_name="ZZZZZZZZZZ", aliases=[]),
    )

    assert candidate.score >= 0.0


def test_matched_name_type_primary_vs_alias() -> None:
    primary_candidate = score_watchlist_record(
        ScreenRequest(name="John A Smith"),
        make_record(),
    )
    alias_candidate = score_watchlist_record(
        ScreenRequest(name="J A Smith"),
        make_record(),
    )

    assert primary_candidate.matched_name_type == "primary"
    assert alias_candidate.matched_name_type == "alias"
