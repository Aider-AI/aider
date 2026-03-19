"""TF-IDF embedder. Pure Python, no external dependencies.

Produces sparse dict vectors {term: tfidf_weight} for cosine similarity.
Vocabulary grows incrementally as new documents are embedded.
"""

import math
import re

# Common English stopwords to filter out during tokenization.
# These high-frequency words (articles, prepositions, pronouns, etc.) carry little
# semantic meaning and would dominate TF-IDF scores if included. Removing them:
# - Reduces vocabulary size and memory usage
# - Improves embedding quality by focusing on content-bearing terms
# - Prevents common words from overwhelming similarity calculations
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "were", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "so", "if", "then", "than", "that", "this", "these",
    "those", "i", "you", "he", "she", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "what",
    "which", "who", "whom", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "just", "about", "also", "very", "often",
    "ok", "up", "out", "into",
})

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text):
    """Lowercase, split on non-alphanumeric, filter stopwords.
    
    Processing pipeline:
    1. Lowercase the entire text
    2. Extract alphanumeric tokens using regex (splits on punctuation/whitespace)
    3. Filter out stopwords using set membership test (O(1) lookup in frozenset)
    
    Example: "The quick brown fox jumps over the lazy dog"
             → ["quick", "brown", "fox", "jumps", "lazy", "dog"]
             (removed: "the", "over")
    """
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


class TFIDFEmbedder:
    """Incremental TF-IDF embedder producing sparse dict vectors."""

    def __init__(self):
        self._doc_count = 0
        self._doc_freq = {}  # term → number of documents containing term

    @property
    def vocab_size(self):
        return len(self._doc_freq)

    @property
    def doc_count(self):
        return self._doc_count

    def embed(self, text):
        """Return sparse dict {term: tfidf_weight} for the given text."""
        tokens = _tokenize(text)
        if not tokens:
            return {}

        # Update document frequency
        self._doc_count += 1
        seen_terms = set(tokens)
        for term in seen_terms:
            self._doc_freq[term] = self._doc_freq.get(term, 0) + 1

        # Compute TF (term frequency within this document)
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        # Normalize TF by document length
        doc_len = len(tokens)

        # Compute TF-IDF
        result = {}
        for term, count in tf.items():
            tf_val = count / doc_len
            # IDF: log(N / df) where N = total docs, df = docs containing term
            df = self._doc_freq.get(term, 1)
            idf = math.log(1.0 + self._doc_count / df) if df > 0 else 0.0
            weight = tf_val * idf
            if weight > 0:
                result[term] = weight

        return result
