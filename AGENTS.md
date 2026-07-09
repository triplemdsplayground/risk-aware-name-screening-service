# Project Guide For Coding Agents

## Summary

This repository contains a deterministic MVP risk-aware name screening service built in Python with FastAPI and Pydantic. It screens one request against a bundled synthetic sample watchlist and returns a `PASS` or `REVIEW` decision with scored candidate matches and explanations.

This is a baseline project, not a production AML or sanctions screening system.

## First Step

- Inspect the existing files before making changes.
- Treat the current codebase, tests, and `pyproject.toml` as the source of truth.
- Do not assume missing infrastructure, features, or patterns if they are not present in the repo.

## Current Architecture

- `src/screening_service/api.py`: FastAPI app and `POST /screen` endpoint
- `src/screening_service/service.py`: orchestration, ranking, and top-5 truncation
- `src/screening_service/matching.py`: deterministic name scoring and explanation building
- `src/screening_service/decision.py`: threshold-based `PASS`/`REVIEW` decisioning
- `src/screening_service/data_loader.py`: bundled synthetic watchlist loading
- `src/screening_service/schemas.py`: Pydantic request and response models
- `src/screening_service/data/watchlist.sample.json`: synthetic sample watchlist data
- `tests/`: unit and API tests covering current behaviour

## Development Commands

Use Python `3.12`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m mypy src tests
python -m uvicorn screening_service.api:app --reload
```

## Testing And Type Checking

- Run `python -m pytest` after substantive changes.
- Run `python -m mypy src tests` when touching typed Python code.
- Do not weaken types, tests, or schemas simply to silence a tool. If mypy exposes a real type mismatch, prefer fixing the annotation or test construction clearly.

## Engineering Boundaries

- Prefer the smallest correct change.
- Keep logic in the existing layers unless there is a clear reason to refactor.
- Do not overbuild, add speculative abstractions, or perform broad rewrites.
- Do not add CI, Docker, databases, external services, or new infrastructure unless explicitly requested.
- Preserve the MVP positioning: deterministic logic, synthetic data, and explainable scoring.

## Change Discipline

- Follow existing naming, typing, and test patterns.
- Update documentation or tests only when they are directly affected by the requested change.
- If the repo state and the request conflict, stop and use the current files to ground the decision.
