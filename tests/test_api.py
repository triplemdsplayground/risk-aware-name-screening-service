from fastapi.testclient import TestClient

from screening_service.api import app

client = TestClient(app)


def test_screen_endpoint_returns_success_for_valid_request() -> None:
    response = client.post(
        "/screen",
        json={
            "name": "John A Smith",
            "country": "GB",
            "birth_year": 1980,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REVIEW"
    assert "threshold" in body
    assert "candidates" in body

def test_screen_endpoint_rejects_whitespace_only_name() -> None:
    response = client.post(
        "/screen",
        json={
            "name": "   ",
        },
    )

    assert response.status_code == 422
