import numpy as np


def normalize_vector(vector):
    """Normalize a vector to unit length (L2 norm).

    Args:
        vector (np.ndarray or list): Input vector

    Returns:
        np.ndarray: Normalized vector with length 1
    """
    vector = np.asarray(vector, dtype=np.float64)
    magnitude = np.linalg.norm(vector)
    if magnitude == 0:
        return vector  # Return original if zero vector
    return vector / magnitude


def cosine_similarity(vector1, vector2):
    """Calculate cosine similarity between two vectors.

    Args:
        vector1 (np.ndarray or list): First vector
        vector2 (np.ndarray or list): Second vector

    Returns:
        float: Cosine similarity between the vectors (range: -1 to 1)
    """
    vector1 = np.asarray(vector1, dtype=np.float64)
    vector2 = np.asarray(vector2, dtype=np.float64)

    if len(vector1) != len(vector2):
        raise ValueError("Vectors must have the same length")

    # Use NumPy's optimized dot product and norm functions
    dot_product = np.dot(vector1, vector2)
    magnitude1 = np.linalg.norm(vector1)
    magnitude2 = np.linalg.norm(vector2)

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0  # Return 0 if either vector is zero

    return dot_product / (magnitude1 * magnitude2)


def create_bigram_vector(texts):
    """Create a bigram frequency vector using optimized NumPy operations.

    This version uses pre-computed bigram indices and NumPy's bincount
    for maximum performance on large datasets.

    Args:
        texts (tuple): Tuple of strings to process

    Returns:
        np.ndarray: Vector of bigram frequencies
    """
    # Pre-compute bigram indices (0 for 'aa', 1 for 'ab', ..., 675 for 'zz')
    bigram_indices = {}
    idx = 0
    for i in range(ord("a"), ord("z") + 1):
        for j in range(ord("a"), ord("z") + 1):
            bigram = chr(i) + chr(j)
            bigram_indices[bigram] = idx
            idx += 1

    # Initialize frequency vector
    vector = np.zeros(26 * 26, dtype=np.int32)

    # Process all texts
    for text in texts:
        text_lower = text.lower()
        if len(text_lower) < 2:
            continue

        # Extract bigrams using NumPy sliding window view
        # Convert string to character array for efficient slicing
        chars = np.array(list(text_lower))

        # Create bigrams by combining consecutive characters
        bigrams = np.char.add(chars[:-1], chars[1:])

        # Filter only alphabetic bigrams
        mask = np.array([bg.isalpha() for bg in bigrams])
        valid_bigrams = bigrams[mask]

        # Count bigrams using bincount with pre-computed indices
        indices = []
        for bg in valid_bigrams:
            if bg in bigram_indices:
                indices.append(bigram_indices[bg])

        if indices:
            counts = np.bincount(indices, minlength=26 * 26)
            vector += counts

    return vector
