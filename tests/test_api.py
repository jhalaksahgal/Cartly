"""HTTP API contract, including the failure paths the UI depends on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------------------------------
# Health and metadata
# --------------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["products"] > 30
    assert set(body["languages"]) == {"en", "hi", "ta", "es"}


def test_platform_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_languages_include_examples(client: TestClient) -> None:
    body = client.get("/api/languages").json()
    assert len(body["languages"]) == 4
    for language in body["languages"]:
        assert language["examples"], f"{language['code']} has no examples"


def test_meta_lists_brands_and_categories(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert "Colgate" in body["brands"]
    assert "Dairy" in body["categories"]


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_parse_add(client: TestClient) -> None:
    response = client.post(
        "/api/parse", json={"transcript": "I need 2 litres of milk", "language": "en-US"}
    )
    assert response.status_code == 200
    command = response.json()["command"]
    assert command["intent"] == "ADD_ITEM"
    assert command["item"] == "milk"
    assert command["quantity"] == 2
    assert command["unit"] == "litre"
    assert command["category"] == "Dairy"


def test_parse_search_includes_results_in_one_round_trip(client: TestClient) -> None:
    body = client.post(
        "/api/parse", json={"transcript": "Find toothpaste under $5", "language": "en-US"}
    ).json()
    assert body["command"]["intent"] == "SEARCH_PRODUCT"
    assert body["search"] is not None
    assert body["search"]["total"] > 0
    assert all(hit["product"]["price"] <= 5 for hit in body["search"]["hits"])


def test_parse_non_search_has_no_search_payload(client: TestClient) -> None:
    body = client.post("/api/parse", json={"transcript": "add milk"}).json()
    assert body["search"] is None


def test_parse_hindi(client: TestClient) -> None:
    body = client.post(
        "/api/parse", json={"transcript": "मुझे दो लीटर दूध चाहिए", "language": "hi-IN"}
    ).json()
    command = body["command"]
    assert command["intent"] == "ADD_ITEM"
    assert command["item"] == "दूध"
    assert command["canonical_item"] == "milk"
    assert command["quantity"] == 2


def test_parse_spanish_search_returns_results(client: TestClient) -> None:
    body = client.post(
        "/api/parse",
        json={"transcript": "Busca pasta de dientes menos de $5", "language": "es-ES"},
    ).json()
    assert body["command"]["intent"] == "SEARCH_PRODUCT"
    assert body["search"]["total"] > 0


def test_parse_empty_transcript_is_unknown_not_an_error(client: TestClient) -> None:
    response = client.post("/api/parse", json={"transcript": ""})
    assert response.status_code == 200
    assert response.json()["command"]["intent"] == "UNKNOWN"


def test_parse_rejects_oversized_input(client: TestClient) -> None:
    response = client.post("/api/parse", json={"transcript": "a" * 5000})
    assert response.status_code == 422


def test_parse_unknown_language_falls_back(client: TestClient) -> None:
    """An unsupported speech locale must not 500."""
    response = client.post(
        "/api/parse", json={"transcript": "add milk", "language": "fr-FR"}
    )
    assert response.status_code == 200
    assert response.json()["command"]["intent"] == "ADD_ITEM"


def test_parse_reports_clarification_decision(client: TestClient) -> None:
    """The threshold lives on the server; the client just reads the flag."""
    unsure = client.post("/api/parse", json={"transcript": "milk"}).json()["command"]
    assert unsure["needs_clarification"] is True

    sure = client.post(
        "/api/parse", json={"transcript": "add 2 litres of milk"}
    ).json()["command"]
    assert sure["needs_clarification"] is False


def test_parse_clear_list_flags_confirmation(client: TestClient) -> None:
    command = client.post("/api/parse", json={"transcript": "clear my list"}).json()[
        "command"
    ]
    assert command["intent"] == "CLEAR_LIST"
    assert command["requires_confirmation"] is True


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


def test_search_endpoint(client: TestClient) -> None:
    body = client.get("/api/search", params={"q": "toothpaste", "max_price": 5}).json()
    assert body["total"] > 0
    assert all(hit["product"]["price"] <= 5 for hit in body["hits"])


def test_search_brand_filter(client: TestClient) -> None:
    body = client.get("/api/search", params={"brand": "Colgate"}).json()
    assert all(hit["product"]["brand"] == "Colgate" for hit in body["hits"])


def test_search_swaps_inverted_price_range(client: TestClient) -> None:
    """A user saying "between 10 and 5" means the same as "between 5 and 10"."""
    body = client.get(
        "/api/search", params={"q": "milk", "min_price": 10, "max_price": 3}
    ).json()
    assert body["query"]["min_price"] == 3
    assert body["query"]["max_price"] == 10


def test_search_rejects_negative_price(client: TestClient) -> None:
    assert client.get("/api/search", params={"max_price": -5}).status_code == 422


def test_search_no_results_returns_fallbacks(client: TestClient) -> None:
    body = client.get("/api/search", params={"q": "toothpaste", "max_price": 0.5}).json()
    assert body["total"] == 0
    assert body["suggestions"]


# --------------------------------------------------------------------------
# Suggestions and substitutes
# --------------------------------------------------------------------------


def test_suggestions_with_history(client: TestClient) -> None:
    body = client.post(
        "/api/suggestions",
        json={
            "history": [{"name": "milk", "days_ago": 2, "count": 4}],
            "current_items": [],
            "month": 8,
        },
    ).json()
    assert body["month"] == 8
    assert body["suggestions"]
    assert all(s["explanation"] for s in body["suggestions"])


def test_suggestions_with_no_history_still_returns_staples(client: TestClient) -> None:
    body = client.post(
        "/api/suggestions", json={"history": [], "current_items": []}
    ).json()
    assert len(body["suggestions"]) > 0


def test_suggestions_reject_invalid_month(client: TestClient) -> None:
    response = client.post(
        "/api/suggestions", json={"history": [], "current_items": [], "month": 13}
    )
    assert response.status_code == 422


def test_substitutes(client: TestClient) -> None:
    body = client.get("/api/substitutes", params={"name": "whole milk 1l"}).json()
    assert body["product"]["in_stock"] is False
    assert any("Almond" in alt["name"] for alt in body["alternatives"])


def test_substitutes_for_unknown_product(client: TestClient) -> None:
    body = client.get("/api/substitutes", params={"name": "qwertyuiop"}).json()
    assert body["product"] is None
    assert body["alternatives"] == []


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------


def test_products_listing_and_category_filter(client: TestClient) -> None:
    everything = client.get("/api/products", params={"limit": 200}).json()
    assert len(everything) > 30
    dairy = client.get("/api/products", params={"category": "Dairy"}).json()
    assert all(product["category"] == "Dairy" for product in dairy)


def test_product_detail_404(client: TestClient) -> None:
    response = client.get("/api/products/not-a-real-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


# --------------------------------------------------------------------------
# Static frontend
# --------------------------------------------------------------------------


def test_frontend_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Cartly" in response.text


@pytest.mark.parametrize(
    "path", ["/styles.css", "/js/app.js", "/js/store.js", "/js/speech.js",
             "/js/api.js", "/js/ui.js", "/js/format.js"]
)
def test_static_assets_are_served(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 200
