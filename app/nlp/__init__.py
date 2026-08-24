"""Deterministic natural-language command parsing.

The pipeline in :mod:`app.nlp.parser` is language-agnostic; everything
language-specific lives in :mod:`app.nlp.lexicons`.

This module deliberately re-exports nothing. ``app.nlp.parser`` depends on
``app.catalog``, which depends back on ``app.nlp.normalize``; importing the
parser here would make that a cycle. Import ``app.nlp.parser.parse`` directly.
"""
