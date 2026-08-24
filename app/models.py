"""Pydantic schemas shared by the NLP, catalog, recommendation and API layers.

These types are the contract between the browser client and the Python
"brain". Keeping them in one module means the OpenAPI schema published at
``/docs`` is always an accurate description of what the frontend may send.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Intent(str, Enum):
    """Every action the assistant knows how to take."""

    ADD_ITEM = "ADD_ITEM"
    REMOVE_ITEM = "REMOVE_ITEM"
    UPDATE_ITEM = "UPDATE_ITEM"
    COMPLETE_ITEM = "COMPLETE_ITEM"
    SEARCH_PRODUCT = "SEARCH_PRODUCT"
    SHOW_LIST = "SHOW_LIST"
    CLEAR_LIST = "CLEAR_LIST"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    UNKNOWN = "UNKNOWN"


#: Intents that must not run without an explicit confirmation step.
DESTRUCTIVE_INTENTS: frozenset[Intent] = frozenset({Intent.CLEAR_LIST})

#: Interpretations below this confidence are surfaced to the user as a
#: Largest quantity treated as credible.
MAX_SANE_QUANTITY = 1000

#: Interpretations below this confidence are surfaced to the user as a
#: question rather than executed silently. The server applies this itself and
#: reports ``needs_clarification``, so the threshold has one definition rather
#: than being duplicated in the frontend.
LOW_CONFIDENCE = 0.45


class Category(str, Enum):
    """Catalog taxonomy. ``OTHER`` is the fallback for unrecognised items."""

    PRODUCE = "Produce"
    DAIRY = "Dairy"
    BAKERY = "Bakery"
    MEAT_SEAFOOD = "Meat & Seafood"
    PANTRY = "Pantry"
    FROZEN = "Frozen"
    BEVERAGES = "Beverages"
    SNACKS = "Snacks"
    PERSONAL_CARE = "Personal Care"
    HOUSEHOLD = "Household"
    BABY = "Baby"
    OTHER = "Other"


class ParsedItem(BaseModel):
    """One item from a command, with its own quantity and modifiers.

    A single utterance can name several: "add 2 litres of milk and 3 eggs" is
    two items with different quantities, and each is parsed independently.
    """

    item: str
    canonical_item: str | None = None
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    brand: str | None = None
    attributes: list[str] = Field(default_factory=list)
    category: Category | None = None
    intent: Intent | None = None


class ParsedCommand(BaseModel):
    """Structured interpretation of a single utterance.

    Every field except ``intent``, ``confidence`` and ``transcript`` is
    optional: the parser reports only what it actually found, so the UI can be
    explicit about what was and was not understood.
    """

    intent: Intent = Intent.UNKNOWN
    transcript: str = ""
    normalized: str = ""
    #: The locale actually used to parse. Usually the one the UI asked for,
    #: but see ``detected_language``.
    language: str = "en-US"
    #: Set when the utterance turned out to be in a different language from the
    #: one selected - a Tamil sentence typed with the picker still on English.
    #: The UI uses this to switch the picker and say so.
    detected_language: str | None = None

    items: list[ParsedItem] = Field(default_factory=list)

    item: str | None = None
    #: ``item`` mapped onto the catalog's English vocabulary. Equal to ``item``
    #: for English. Search and categorization use this; the UI displays
    #: ``item``, so a Hindi speaker still sees their own words on the list.
    canonical_item: str | None = None
    quantity: float | None = None
    unit: str | None = None
    brand: str | None = None
    category: Category | None = None
    attributes: list[str] = Field(default_factory=list)

    #: Target of an UPDATE_ITEM swap, e.g. "change milk to almond milk".
    replacement: str | None = None
    canonical_replacement: str | None = None

    min_price: float | None = None
    max_price: float | None = None

    #: 0.0-1.0 confidence in the interpretation as a whole.
    confidence: float = 0.0
    #: Which layer produced this interpretation. "rules" is the deterministic
    #: parser; "llm" is the optional fallback, shown as a badge in the UI so
    #: the user can tell the difference.
    source: Literal["rules", "llm"] = "rules"
    #: True when the intent is destructive and needs confirmation first.
    requires_confirmation: bool = False
    #: True when confidence is too low to act on without asking the user.
    #: Derived from :data:`LOW_CONFIDENCE` so the UI needs no threshold of
    #: its own.
    needs_clarification: bool = False

    def summary(self) -> str:
        """Human-readable echo of the interpretation for the feedback line."""
        if len(self.items) > 1 and any(i.intent for i in self.items):
            parts: list[str] = []
            for item in self.items:
                intent_val = item.intent or self.intent
                action_word = {
                    Intent.ADD_ITEM: "Add",
                    Intent.REMOVE_ITEM: "Remove",
                    Intent.UPDATE_ITEM: "Change",
                    Intent.COMPLETE_ITEM: "Tick off",
                }.get(intent_val, intent_val.value)
                qty = f" {item.quantity:g}" if item.quantity is not None else ""
                unit = f" {item.unit}" if item.unit else ""
                parts.append(f"{action_word}{qty}{unit} {item.item}".strip())
            return ", ".join(parts)

        bits: list[str] = []
        if self.quantity is not None:
            qty = f"{self.quantity:g}"
            bits.append(f"{qty} {self.unit}" if self.unit else qty)
        if self.brand:
            bits.append(self.brand)
        bits.extend(self.attributes)
        if self.item:
            bits.append(self.item)
        detail = " ".join(bits)

        if self.min_price is not None and self.max_price is not None:
            detail += f" between ${self.min_price:g} and ${self.max_price:g}"
        elif self.max_price is not None:
            detail += f" under ${self.max_price:g}"
        elif self.min_price is not None:
            detail += f" over ${self.min_price:g}"

        if self.replacement:
            detail += f" -> {self.replacement}"
        return detail.strip()


class Product(BaseModel):
    """A catalog entry. Prices are USD; this is clearly-labelled sample data."""

    id: str
    name: str
    brand: str | None = None
    category: Category = Category.OTHER
    price: float
    unit: str = "each"
    tags: list[str] = Field(default_factory=list)
    #: Month numbers (1-12) when the product is in season; empty means
    #: year-round.
    seasonal_months: list[int] = Field(default_factory=list)
    #: Product ids that can stand in for this one.
    alternatives: list[str] = Field(default_factory=list)
    #: Products commonly bought together, driving complementary suggestions.
    complements: list[str] = Field(default_factory=list)
    in_stock: bool = True
    emoji: str = "\U0001f6d2"

    @field_validator("price")
    @classmethod
    def _price_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("price must be greater than zero")
        return value


class SearchQuery(BaseModel):
    """Normalized catalog query, from a ParsedCommand or from typed input."""

    text: str = ""
    brand: str | None = None
    category: Category | None = None
    attributes: list[str] = Field(default_factory=list)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    in_stock_only: bool = False
    limit: int = Field(default=12, ge=1, le=100)

    def describe(self) -> list[str]:
        """Filter chips shown to the user so the query is never a black box."""
        chips: list[str] = []
        if self.text:
            chips.append(f"Searching for: {self.text}")
        if self.brand:
            chips.append(f"Brand: {self.brand}")
        if self.category:
            chips.append(f"Category: {self.category.value}")
        for attribute in self.attributes:
            chips.append(f"Attribute: {attribute}")
        if self.min_price is not None and self.max_price is not None:
            chips.append(f"Price: ${self.min_price:g} - ${self.max_price:g}")
        elif self.max_price is not None:
            chips.append(f"Max price: ${self.max_price:g}")
        elif self.min_price is not None:
            chips.append(f"Min price: ${self.min_price:g}")
        return chips


class SearchHit(BaseModel):
    """One catalog match with its relevance score and in-stock substitutes."""

    product: Product
    score: float
    alternatives: list[Product] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: SearchQuery
    filters: list[str] = Field(default_factory=list)
    hits: list[SearchHit] = Field(default_factory=list)
    total: int = 0
    #: Populated when the query matched nothing, to offer a way forward.
    suggestions: list[Product] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    """One past purchase, sent by the client with each suggestions request.

    The server holds no user state: history travels with the request, so there
    is no account system, no database, and no personal data at rest.
    """

    name: str
    product_id: str | None = None
    #: How many days ago the item was added. 0 means today.
    days_ago: int = Field(default=0, ge=0)
    count: int = Field(default=1, ge=1)


SuggestionReason = Literal[
    "frequent", "recent", "seasonal", "complementary", "substitute", "staple"
]


class Suggestion(BaseModel):
    """A recommendation plus the explanation rendered on its card."""

    product: Product
    score: float
    reason: SuggestionReason
    #: User-facing sentence, e.g. "Bought 4 times in the last month".
    explanation: str


class SuggestionsRequest(BaseModel):
    history: list[HistoryEntry] = Field(default_factory=list)
    #: Names already on the list, so they are not suggested back to the user.
    current_items: list[str] = Field(default_factory=list)
    limit: int = Field(default=6, ge=1, le=24)
    #: Overrides "today" so seasonal behaviour is deterministic in tests.
    month: int | None = Field(default=None, ge=1, le=12)


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion] = Field(default_factory=list)
    month: int


class ParseRequest(BaseModel):
    transcript: str = Field(default="", max_length=500)
    language: str = "en-US"


class ParseResponse(BaseModel):
    command: ParsedCommand
    summary: str
    #: Present when the intent was SEARCH_PRODUCT, so voice search is one call.
    search: SearchResponse | None = None


class SubstitutesResponse(BaseModel):
    query: str
    product: Product | None = None
    alternatives: list[Product] = Field(default_factory=list)
