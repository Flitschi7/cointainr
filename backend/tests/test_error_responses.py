"""
Error responses keep their shape but never expose raw exception text.

Outside development, `original_error` (pydantic dumps with server file paths,
SQL or provider messages, echoed request input) stays in the server log only.
"""

from app.core.config import settings

ASSETS = "/api/v1/assets/"


def assert_no_internals(response):
    assert "original_error" not in response.text
    assert ".py" not in response.text
    assert "app/" not in response.text and "app\\\\" not in response.text


async def test_validation_error_hides_original_error(client):
    response = await client.post(
        ASSETS, json={"type": "cash", "name": "Bank", "quantity": "lots"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"] is True
    assert body["message"] == "Request validation failed"
    assert body["category"] == "validation_error"
    assert body["status_code"] == 422
    errors = body["details"]["validation_errors"]
    assert [e["loc"] for e in errors] == [["body", "quantity"]]
    assert all(e["msg"] and e["type"] for e in errors)
    assert "lots" not in response.text
    assert_no_internals(response)


async def test_not_found_error_hides_original_error(client):
    response = await client.put(f"{ASSETS}999", json={"quantity": 1})

    assert response.status_code == 404
    body = response.json()
    assert body["error"] is True
    assert body["category"] == "not_found_error"
    assert body["status_code"] == 404
    assert body["message"]
    assert_no_internals(response)


async def test_development_still_shows_original_error(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    response = await client.put(f"{ASSETS}999", json={"quantity": 1})

    assert response.status_code == 404
    assert "original_error" in response.json()["details"]
