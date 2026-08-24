"""Explainable, heuristic product recommendations."""

from app.recommend.engine import recommend, substitutes_for_name

__all__ = ["recommend", "substitutes_for_name"]
