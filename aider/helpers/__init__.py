"""Utility functions for aider."""

from .similarity import cosine_similarity, create_bigram_vector, normalize_vector

__all__ = [
    "cosine_similarity",
    "create_bigram_vector",
    "normalize_vector",
]
