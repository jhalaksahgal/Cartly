"""Optional LLM fallback for utterances the deterministic parser cannot read.

This is deliberately a *fallback*, not the main path. The rule-based parser in
:mod:`app.nlp.parser` handles every phrasing the product needs and is fully
reproducible, which is what makes its test suite meaningful. Putting a model in
front of it would trade that reproducibility for coverage the app does not
need.

Behind it, though, there is a real gap: genuinely novel phrasing returns
``UNKNOWN``. This module fills that gap and nothing else.

Design rules, in priority order:

1. **Absent by default.** With no ``GROQ_API_KEY`` the app behaves exactly as
   it did before - same code path, same latency, same results.
2. **Never raises.** Timeout, bad key, rate limit, malformed JSON, garbage
   field values: every failure returns ``None`` and the caller keeps the
   original ``UNKNOWN``. A degraded LLM must never degrade the app.
3. **Never trusted blindly.** Results come back below the clarification
   threshold, so the UI asks "did you mean...?" rather than acting. The model
   only runs when the rules already failed, which is exactly when confidence
   should be low.
4. **No secret ever leaves this module.** The key is read from the environment
   and used; it is never logged, echoed, or returned in a response.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

from app.catalog.categorize import categorize
from app.models import Category, Intent, ParsedCommand
from app.nlp.lexicons import get_lexicon
from app.nlp.normalize import normalize
from app.nlp.translate import canonicalize

logger = logging.getLogger(__name__)

_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_DEFAULT_TIMEOUT = 4.0

#: LLM interpretations land below ``LOW_CONFIDENCE`` on purpose, so the UI
#: confirms before acting. See rule 3 in the module docstring.
_LLM_CONFIDENCE = 0.4

#: Intents the model is allowed to return. Anything else is rejected.
_ALLOWED_INTENTS = {
    "ADD_ITEM", "REMOVE_ITEM", "UPDATE_ITEM", "COMPLETE_ITEM",
    "SEARCH_PRODUCT", "SHOW_LIST", "CLEAR_LIST", "UNKNOWN",
}

_SYSTEM_PROMPT = """\
You convert grocery shopping commands into JSON. The user may write in any \
language. Reply with ONLY a JSON object, no prose.

Schema:
{
  "intent": "ADD_ITEM" | "REMOVE_ITEM" | "UPDATE_ITEM" | "COMPLETE_ITEM" |
            "SEARCH_PRODUCT" | "SHOW_LIST" | "CLEAR_LIST" | "UNKNOWN",
  "item": string | null,          // the product, in the user's own language
  "quantity": number | null,
  "unit": string | null,          // singular English unit: litre, kg, bottle...
  "brand": string | null,
  "attributes": string[],         // English tags: organic, frozen, gluten-free
  "replacement": string | null,   // for UPDATE_ITEM: what it becomes
  "min_price": number | null,
  "max_price": number | null
}

Rules:
- Use UNKNOWN if it is not a shopping command. Do not guess wildly.
- "item" keeps the user's own wording; do not translate it.
- A number that belongs to a price is min_price/max_price, never quantity.
- Omit nothing: include every key, using null where it does not apply.\
"""


def is_enabled() -> bool:
    """True when an API key is configured. Checked before every call."""
    return bool(os.environ.get("GROQ_API_KEY", "").strip())


def _model() -> str:
    return os.environ.get("GROQ_MODEL", "").strip() or _DEFAULT_MODEL


def _timeout() -> float:
    try:
        return float(os.environ.get("GROQ_TIMEOUT", "") or _DEFAULT_TIMEOUT)
    except ValueError:
        return _DEFAULT_TIMEOUT


def _as_number(value: object) -> float | None:
    """Coerce a model-supplied number, rejecting anything unusable."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    # Reject NaN/inf and absurd magnitudes rather than storing them.
    if number != number or number in (float("inf"), float("-inf")):
        return None
    if not 0 <= number <= 100_000:
        return None
    return number


def _as_text(value: object, *, limit: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())[:limit].strip()
    return cleaned or None


def _build_command(
    payload: dict[str, object], transcript: str, language: str
) -> ParsedCommand | None:
    """Validate a model response into a ParsedCommand, or reject it."""
    raw_intent = payload.get("intent")
    if not isinstance(raw_intent, str) or raw_intent not in _ALLOWED_INTENTS:
        return None
    intent = Intent(raw_intent)
    if intent is Intent.UNKNOWN:
        return None

    lexicon = get_lexicon(language)

    item = _as_text(payload.get("item"))
    unit = _as_text(payload.get("unit"), limit=20)
    if unit:
        # The model may answer "litres"; the catalog speaks in "litre".
        unit = lexicon.units.get(unit.lower(), unit.lower())

    attributes_raw = payload.get("attributes")
    attributes: list[str] = []
    if isinstance(attributes_raw, list):
        for entry in attributes_raw[:5]:
            tag = _as_text(entry, limit=24)
            if tag and tag.lower() not in attributes:
                attributes.append(tag.lower())

    min_price = _as_number(payload.get("min_price"))
    max_price = _as_number(payload.get("max_price"))
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    command = ParsedCommand(
        intent=intent,
        transcript=transcript,
        normalized=normalize(transcript),
        language=language,
        item=item,
        quantity=_as_number(payload.get("quantity")),
        unit=unit,
        brand=_as_text(payload.get("brand"), limit=40),
        attributes=attributes,
        replacement=_as_text(payload.get("replacement")),
        min_price=min_price,
        max_price=max_price,
        confidence=_LLM_CONFIDENCE,
        source="llm",
    )

    # Categorization and canonicalization are ours, not the model's - it does
    # not know our taxonomy and should not be inventing categories.
    command.canonical_item = canonicalize(command.item, lexicon)
    command.canonical_replacement = canonicalize(command.replacement, lexicon)
    if command.canonical_item:
        category = categorize(command.canonical_item)
        command.category = category if category is not Category.OTHER else None

    # An add/remove/update with nothing to act on is not a usable result.
    if intent not in (Intent.SHOW_LIST, Intent.CLEAR_LIST) and not (
        command.item or command.brand or command.attributes
    ):
        return None

    return command


def interpret(transcript: str, language: str = "en-US") -> ParsedCommand | None:
    """Ask the model to interpret ``transcript``.

    Returns ``None`` whenever the fallback is disabled, the call fails, or the
    response cannot be validated. Callers keep their original result in that
    case; there is no error to handle.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or not transcript.strip():
        return None

    try:
        response = httpx.post(
            _API_URL,
            timeout=_timeout(),
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": _model(),
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Language: {language}\nCommand: {transcript}",
                    },
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        payload = json.loads(content)
    except httpx.TimeoutException:
        logger.warning("LLM fallback timed out after %.1fs", _timeout())
        return None
    except httpx.HTTPStatusError as exc:
        # Status only - the response body can echo request details.
        logger.warning("LLM fallback returned HTTP %s", exc.response.status_code)
        return None
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
        logger.warning("LLM fallback failed: %s", type(exc).__name__)
        return None
    except Exception:
        # Deliberately broad. This is an optional enhancement on a path the
        # user did not ask for; no failure of it may ever surface as an error
        # in the core flow. Logged with a traceback so it is still diagnosable.
        logger.exception("LLM fallback raised an unexpected error")
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return _build_command(payload, transcript, language)
    except Exception:
        logger.exception("LLM fallback produced an unusable response")
        return None
