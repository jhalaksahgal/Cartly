"""Optional LLM fallback.

No test here makes a network call. The point of these is the contract around
the model, not the model itself: it must stay off without a key, must never
override the rules, and must survive every way a remote API can misbehave.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Intent
from app.nlp import llm


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def no_key_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with the fallback disabled unless it opts in."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


def _groq_reply(payload: dict) -> httpx.Response:
    """Build a response shaped like Groq's chat-completions endpoint."""
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(payload)}}]},
    )


def _stub_post(monkeypatch: pytest.MonkeyPatch, result):
    """Replace httpx.post with something that returns or raises `result`."""

    def fake_post(*args, **kwargs):
        if isinstance(result, Exception):
            raise result
        # A Response built standalone has no request attached, and both
        # raise_for_status() and .request itself raise without one.
        result.request = httpx.Request("POST", "https://api.groq.com")
        return result

    monkeypatch.setattr(llm.httpx, "post", fake_post)


# --------------------------------------------------------------------------
# Enablement
# --------------------------------------------------------------------------


def test_disabled_without_a_key() -> None:
    assert llm.is_enabled() is False
    assert llm.interpret("some strange phrasing") is None


def test_blank_key_counts_as_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "   ")
    assert llm.is_enabled() is False


def test_enabled_with_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert llm.is_enabled() is True


def test_health_reports_status_but_never_the_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "super-secret-value")
    body = client.get("/api/health").json()
    assert body["llm_fallback"] is True
    assert "super-secret-value" not in json.dumps(body)


# --------------------------------------------------------------------------
# The rules always win
# --------------------------------------------------------------------------


def test_rules_take_precedence_over_the_model(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A command the parser understands must never reach the model."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def explode(*args, **kwargs):
        raise AssertionError("the model was called for a command the rules handled")

    monkeypatch.setattr(llm.httpx, "post", explode)

    body = client.post("/api/parse", json={"transcript": "add 2 litres of milk"}).json()
    assert body["command"]["intent"] == "ADD_ITEM"
    assert body["command"]["source"] == "rules"


def test_rule_parsed_commands_are_labelled_rules(client: TestClient) -> None:
    body = client.post("/api/parse", json={"transcript": "add milk"}).json()
    assert body["command"]["source"] == "rules"


# --------------------------------------------------------------------------
# Successful interpretation
# --------------------------------------------------------------------------


def test_model_result_fills_an_unknown(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply(
            {
                "intent": "ADD_ITEM",
                "item": "sourdough",
                "quantity": 2,
                "unit": "loaves",
                "brand": None,
                "attributes": [],
                "replacement": None,
                "min_price": None,
                "max_price": None,
            }
        ),
    )

    body = client.post(
        "/api/parse",
        json={"transcript": "the bread situation in this house is dire"},
    ).json()
    command = body["command"]
    assert command["intent"] == "ADD_ITEM"
    assert command["item"] == "sourdough"
    assert command["quantity"] == 2
    # "loaves" is normalized onto the catalog's singular unit vocabulary.
    assert command["unit"] == "loaf"
    assert command["source"] == "llm"


def test_model_results_always_ask_before_acting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model only runs when the rules failed, so it is never trusted."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply({"intent": "ADD_ITEM", "item": "quinoa", "attributes": []}),
    )
    command = llm.interpret("the fridge is looking pretty bare")
    assert command is not None
    assert command.confidence < 0.45


def test_model_result_is_categorised_by_us_not_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply(
            {"intent": "ADD_ITEM", "item": "milk", "category": "Nonsense",
             "attributes": []}
        ),
    )
    command = llm.interpret("the fridge is looking pretty bare")
    assert command is not None
    assert command.category.value == "Dairy"


def test_model_search_still_runs_the_catalog_query(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply(
            {
                "intent": "SEARCH_PRODUCT",
                "item": "toothpaste",
                "max_price": 5,
                "attributes": [],
            }
        ),
    )
    body = client.post(
        "/api/parse", json={"transcript": "my teeth need something cheap"}
    ).json()
    assert body["command"]["intent"] == "SEARCH_PRODUCT"
    assert body["search"]["total"] > 0


# --------------------------------------------------------------------------
# Every failure mode degrades to None
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure",
    [
        httpx.TimeoutException("timed out"),
        httpx.ConnectError("no route to host"),
        httpx.HTTPStatusError(
            "rate limited",
            request=httpx.Request("POST", "https://api.groq.com"),
            response=httpx.Response(429),
        ),
        RuntimeError("something entirely unexpected"),
    ],
)
def test_transport_failures_return_none(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    """Including error types we did not anticipate - the contract is absolute."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(monkeypatch, failure)
    assert llm.interpret("anything") is None


@pytest.mark.parametrize(
    "body",
    [
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"nonsense": True}),
        httpx.Response(200, text="not json at all"),
        httpx.Response(200, json={"choices": [{"message": {"content": "{oops"}}]}),
        httpx.Response(401, json={"error": "bad key"}),
        httpx.Response(500, text="upstream exploded"),
    ],
)
def test_malformed_responses_return_none(
    monkeypatch: pytest.MonkeyPatch, body: httpx.Response
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(monkeypatch, body)
    assert llm.interpret("anything") is None


@pytest.mark.parametrize(
    "payload",
    [
        {"intent": "UNKNOWN"},
        {"intent": "DROP_TABLE_USERS", "item": "milk"},
        {"intent": 42, "item": "milk"},
        {"item": "milk"},
        {"intent": "ADD_ITEM"},
        {"intent": "ADD_ITEM", "item": None},
        {"intent": "ADD_ITEM", "item": "   "},
    ],
)
def test_unusable_payloads_are_rejected(
    monkeypatch: pytest.MonkeyPatch, payload: dict
) -> None:
    """A model that answers off-schema is treated as no answer at all."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(monkeypatch, _groq_reply(payload))
    assert llm.interpret("anything") is None


@pytest.mark.parametrize(
    "quantity",
    ["not a number", float("inf"), float("nan"), -5, 10**9, True, {"a": 1}],
)
def test_absurd_numbers_are_dropped_not_stored(
    monkeypatch: pytest.MonkeyPatch, quantity: object
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply({"intent": "ADD_ITEM", "item": "milk", "quantity": quantity,
                     "attributes": []}),
    )
    command = llm.interpret("anything")
    assert command is not None
    assert command.quantity is None or 0 <= command.quantity <= 100_000


def test_inverted_price_range_is_corrected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply(
            {"intent": "SEARCH_PRODUCT", "item": "cheese",
             "min_price": 20, "max_price": 5, "attributes": []}
        ),
    )
    command = llm.interpret("anything")
    assert command is not None
    assert command.min_price == 5
    assert command.max_price == 20


def test_overlong_strings_are_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(
        monkeypatch,
        _groq_reply({"intent": "ADD_ITEM", "item": "x" * 5000, "attributes": []}),
    )
    command = llm.interpret("anything")
    assert command is not None
    assert len(command.item) <= 80


def test_failure_leaves_the_original_unknown_intact(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The user sees the normal "didn't understand" path, not an error."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    _stub_post(monkeypatch, httpx.TimeoutException("slow"))

    response = client.post("/api/parse", json={"transcript": "zzz qqq vvv"})
    assert response.status_code == 200
    command = response.json()["command"]
    assert command["intent"] == Intent.UNKNOWN.value
    assert command["source"] == "rules"
