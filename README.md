# Risk-Aware Name Screening Service

A FastAPI-based MVP for explainable name screening, designed around typed schemas, testable matching logic, service-layer orchestration, API boundaries, and transparent scoring.

The current version screens a submitted name against a bundled synthetic watchlist, ranks candidate matches, and returns a `PASS` or `REVIEW` decision with score components and plain-English explanations.

The project is intentionally narrow at this stage: it uses deterministic matching and synthetic data rather than production AML or sanctions-screening infrastructure. The longer-term aim is to evolve it toward sanctions-style data ingestion and richer name-matching strategies while keeping the codebase clean, testable, and easy to extend.

## Overview

This project demonstrates the core mechanics of a screening workflow without hiding the logic behind external services or complex infrastructure. Given a name and optional metadata, the service validates the request, compares it against sample watchlist records, ranks the strongest candidates, and applies a simple review threshold.

This is not a production AML, sanctions, or adverse-media screening system. The current data is synthetic, the matching is deterministic, and the decisioning is intentionally narrow. The project is designed as an engineering and portfolio exercise that can be expanded toward richer data ingestion, stronger matching techniques, and more realistic screening scenarios.

## Why It Exists

This project is a practical exercise in building a small but well-structured screening service with data-science-style scoring logic exposed through an API. The domain is name screening, but the main engineering goals are broader:

- Define clear request and response schemas
- Keep matching, decisioning, orchestration, and API layers separate
- Make scoring behaviour explainable and testable
- Use type checking and automated tests to catch integration issues
- Expose the workflow through a simple FastAPI endpoint
- Leave room for future extensions such as sanctions-list ingestion and alternative matching strategies

## Current MVP Scope

- Screens one request at a time against a bundled sample watchlist
- Uses `difflib.SequenceMatcher` plus small deterministic boosts and penalties
- Returns up to 5 top candidates sorted by descending score
- Produces a `REVIEW` decision when the top score is `>= 0.80`, otherwise `PASS`
- Includes score components and a plain-English explanation for each returned candidate

## High-Level Architecture

- `src/screening_service/api.py`: FastAPI app exposing `POST /screen`
- `src/screening_service/service.py`: orchestrates watchlist loading, scoring, sorting, and top-5 truncation
- `src/screening_service/data_loader.py`: loads the bundled synthetic watchlist JSON
- `src/screening_service/matching.py`: normalises names, scores primary and alias matches, applies country and birth-year adjustments, and builds explanations
- `src/screening_service/decision.py`: applies the `PASS`/`REVIEW` threshold rule
- `src/screening_service/schemas.py`: Pydantic request and response models
- `src/screening_service/data/watchlist.sample.json`: synthetic sample watchlist data used by the MVP

## Project Case Study

This MVP models a common screening workflow at a high level: accept a submitted identity, compare it against watchlist-style records, rank the strongest candidates, and route sufficiently strong matches for review. The goal is not to simulate a full compliance platform, but to show the core mechanics of turning name comparison logic into a structured, testable service.

The project starts with a deterministic baseline rather than ML so the behaviour stays inspectable from the beginning. For this MVP, that matters more than introducing a more complex model before there is a clear evaluation surface. A deterministic scorer makes it easier to verify expected outcomes, reason about edge cases, and change matching rules without losing sight of why a result moved.

The code is split into schemas, matching, decisioning, service orchestration, and API layers to keep responsibilities narrow. Typed schemas define the contract at the boundary. Matching focuses on how candidate scores are built. Decisioning applies the review policy separately from similarity scoring. The service layer coordinates data loading, ranking, and response shaping. The API layer stays thin, which keeps the domain logic easier to test outside HTTP concerns.

Explainable score components are included so results are not just ranked, but understandable. That breakdown is useful for debugging, for validating scoring changes in tests, and for showing which factors influenced a candidate's final score.

The current threshold-based design makes a deliberate tradeoff: it is simple, predictable, and easy to tune, but it is also coarse. A single cutoff cannot capture more nuanced risk policies or richer match resolution. Even so, this structure provides a clean foundation for future sanctions-style ingestion, internal record normalisation, configurable scoring inputs, and stronger matching strategies without needing to redesign the API surface.

## Local Setup

Python `3.12` is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run Tests

```bash
python -m pytest
```

## Run Mypy

```bash
python -m mypy src tests
```

## Run the FastAPI App

```bash
python -m uvicorn screening_service.api:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the autogenerated Swagger UI.

## Sample Request

```bash
curl -X POST "http://127.0.0.1:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John A Smith",
    "country": "GB",
    "birth_year": 1980
  }'
```

## Example Response

```json
{
  "decision": "REVIEW",
  "decision_reason": "Top candidate wl-001 scored 1.00, meeting or exceeding the review threshold of 0.80.",
  "threshold": 0.8,
  "candidates": [
    {
      "watchlist_id": "wl-001",
      "primary_name": "John A Smith",
      "matched_name": "John A Smith",
      "matched_name_type": "primary",
      "entity_type": "person",
      "score": 1.0,
      "matched_on": ["name_similarity", "exact_primary_name_match", "token_overlap", "country_match", "birth_year_match"],
      "score_components": {
        "base_name_similarity": 1.0,
        "exact_match_boost": 0.12,
        "alias_exact_match_boost": 0.0,
        "token_overlap_boost": 0.08,
        "country_adjustment": 0.05,
        "birth_year_adjustment": 0.05
      },
      "explanation": "Best primary match was 'John A Smith' with similarity 1.00. Exact primary-name match increased the score. Shared tokens increased the score. Country matched the watchlist metadata. Birth year matched the watchlist metadata."
    }
  ]
}
```

## Response Fields

- `decision`: final outcome, either `PASS` or `REVIEW`
- `decision_reason`: short explanation of why that outcome was returned
- `threshold`: score threshold used for review escalation
- `candidates`: top scored watchlist candidates returned by the service
- `watchlist_id`: identifier of the matched watchlist record
- `primary_name`: canonical name stored on the watchlist record
- `matched_name`: primary name or alias that produced the best score
- `matched_name_type`: whether the best match came from the `primary` name or an `alias`
- `entity_type`: current watchlist record type such as `person` or `entity`
- `score`: final candidate score after boosts, penalties, and clamping to `0.0`-`1.0`
- `matched_on`: list of factors that contributed to the result
- `score_components`: numeric breakdown of similarity, boosts, and metadata adjustments
- `explanation`: plain-English summary of how the score was built

## Known Limitations

- Uses a tiny bundled synthetic watchlist, not real screening data
- Uses simple deterministic string similarity rather than production-grade matching
- No persistence, audit trail, authentication, or case management workflow
- No batch screening, async processing, or external data integrations
- Country and birth-year handling are minimal and only adjust scores in small fixed increments

## Future Improvements

- Add CI to run tests and type checks automatically
- Expand the synthetic watchlist and test scenarios to cover aliases, metadata conflicts, common names, and entity records
- Add sanctions-style data ingestion by parsing an external-style watchlist into the internal schema
- Improve metadata matching and false-positive controls, especially around date-of-birth, country, aliases, and entity type
- Introduce configurable thresholds and scoring weights once the scoring rules become more complex