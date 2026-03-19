"""Forest (union-find cluster store) and ContextWindow (hot zone + cold forest).

Ported from gemini-cli's contextWindow.ts, adapted for aider's message model.
"""

# TODO: refactor needed

import math


def _cosine_similarity(a, b):
    """Cosine similarity between two sparse dict vectors. Returns 0.0 if either is zero.
    
    Computes the cosine of the angle between two vectors using the formula:
        similarity = (a · b) / (||a|| * ||b||)
    
    Where:
        - a · b is the dot product: sum of (a[i] * b[i]) for all dimensions
        - ||a|| is the L2 norm (magnitude) of vector a: sqrt(sum of a[i]²)
        - ||b|| is the L2 norm (magnitude) of vector b: sqrt(sum of b[i]²)
    
    The result ranges from -1 (opposite) to 1 (identical direction), with 0 meaning
    orthogonal (no similarity). For sparse vectors represented as dicts, only the
    intersection of keys contributes to the dot product.
    
    Returns 0.0 if either vector has zero magnitude (avoiding division by zero).
    """
    keys = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class Forest:
    """Union-find cluster store. Clusters hold content, embeddings, and summaries.

    Each node has a parent pointer. Roots represent clusters.
    Union merges two roots; resolve_dirty summarizes merged clusters via LLM.
    """

    def __init__(self, summarizer):
        self._summarizer = summarizer
        self._parent = {}      # node_id → parent_id (root points to self)
        self._content = {}     # node_id → raw content string
        self._embedding = {}   # node_id → embedding vector
        self._summary = {}     # root_id → cached summary (None if dirty/singleton)
        self._dirty = set()    # set of dirty root ids
        self._dirty_inputs = {}  # root_id → list of texts to summarize
        self._children = {}    # root_id → set of child node ids (for tracking)
        self._root_order = []  # insertion-order tracking for stable roots()

    def _find(self, node_id):
        """Find root with path compression."""
        path = []
        current = node_id
        while self._parent[current] != current:
            path.append(current)
            current = self._parent[current]
        for p in path:
            self._parent[p] = current
        return current

    def insert(self, msg_id, content, embedding):
        """Create a singleton cluster."""
        self._parent[msg_id] = msg_id
        self._content[msg_id] = content
        self._embedding[msg_id] = embedding
        self._children[msg_id] = {msg_id}
        self._root_order.append(msg_id)
        # Singletons are not dirty — compact returns raw content

    def union(self, id_a, id_b):
        """Merge two clusters. Synchronous, no LLM call. Marks result dirty.

        Uses weighted centroid averaging: centroids weighted by cluster size.
        """
        root_a = self._find(id_a)
        root_b = self._find(id_b)
        if root_a == root_b:
            return root_a

        # Merge smaller into larger (union by size)
        size_a = len(self._children.get(root_a, set()))
        size_b = len(self._children.get(root_b, set()))

        if size_a >= size_b:
            new_root, old_root = root_a, root_b
            size_new, size_old = size_a, size_b
        else:
            new_root, old_root = root_b, root_a
            size_new, size_old = size_b, size_a

        self._parent[old_root] = new_root

        # Merge children tracking
        if new_root not in self._children:
            self._children[new_root] = set()
        if old_root in self._children:
            self._children[new_root].update(self._children[old_root])
            del self._children[old_root]

        # Collect dirty inputs: previous summary or raw content from each side
        inputs = []
        # From new_root side
        if new_root in self._summary and self._summary[new_root] is not None:
            inputs.append(self._summary[new_root])
        elif new_root in self._dirty_inputs and self._dirty_inputs[new_root]:
            inputs.extend(self._dirty_inputs[new_root])
        else:
            inputs.append(self._content.get(new_root, ""))

        # From old_root side
        if old_root in self._summary and self._summary[old_root] is not None:
            inputs.append(self._summary[old_root])
        elif old_root in self._dirty_inputs and self._dirty_inputs[old_root]:
            inputs.extend(self._dirty_inputs[old_root])
        else:
            inputs.append(self._content.get(old_root, ""))

        self._dirty_inputs[new_root] = inputs

        # Mark dirty, clear old summary
        self._dirty.add(new_root)
        self._dirty.discard(old_root)
        self._summary.pop(old_root, None)
        self._dirty_inputs.pop(old_root, None)

        # Weighted centroid averaging (weight by cluster size)
        # 
        # When merging two clusters, we compute a new centroid embedding that represents
        # the combined cluster. Each cluster's centroid is weighted by its size (member count).
        #
        # Formula for each dimension k:
        #   new_centroid[k] = (centroid_A[k] * size_A + centroid_B[k] * size_B) / (size_A + size_B)
        #
        # Example: Merging cluster A (5 members, centroid=[0.8, 0.2]) with 
        #          cluster B (3 members, centroid=[0.2, 0.6]):
        #   new_centroid[0] = (0.8 * 5 + 0.2 * 3) / 8 = 4.6 / 8 = 0.575
        #   new_centroid[1] = (0.2 * 5 + 0.6 * 3) / 8 = 2.8 / 8 = 0.350
        #
        # Why weight by size?
        # - Larger clusters represent more messages, so they should have more influence
        # - Prevents a single outlier message from drastically shifting a large cluster's centroid
        # - Maintains semantic coherence: the merged centroid stays closer to the "center of mass"
        #   of all individual messages across both clusters
        #
        # This is analogous to computing the center of mass in physics, where each cluster's
        # centroid acts as a point mass with weight equal to its member count.
        total = size_new + size_old
        emb_a = self._embedding.get(new_root, {})
        emb_b = self._embedding.get(old_root, {})
        if emb_a and emb_b:
            all_keys = set(emb_a.keys()) | set(emb_b.keys())
            self._embedding[new_root] = {
                k: (emb_a.get(k, 0.0) * size_new + emb_b.get(k, 0.0) * size_old) / total
                for k in all_keys
            }
        elif emb_b:
            # Preserve the non-empty embedding
            self._embedding[new_root] = emb_b

        # Update root order: remove old_root, keep new_root's position
        if old_root in self._root_order:
            self._root_order.remove(old_root)

        # Release raw content and embeddings for non-root members.
        # After merge, only the root's centroid and summary matter.
        for member in self._children.get(new_root, set()):
            if member != new_root:
                self._content.pop(member, None)
                self._embedding.pop(member, None)

        return new_root

    def resolve_dirty(self):
        """Summarize all dirty roots via the summarizer. Blocking."""
        for root_id in list(self._dirty):
            inputs = self._dirty_inputs.get(root_id, [])
            if inputs:
                summary = self._summarizer.summarize(inputs)
                self._summary[root_id] = summary
                self._dirty_inputs[root_id] = []
            self._dirty.discard(root_id)

    def compact(self, node_id):
        """Return cached summary for a root, or raw content for a singleton."""
        root = self._find(node_id)
        if root in self._summary and self._summary[root] is not None:
            return self._summary[root]
        return self._content.get(root, "")

    def nearest_root(self, embedding):
        """Find the closest root by cosine similarity. Returns (root_id, similarity) or None."""
        current_roots = self.roots()
        if not current_roots:
            return None

        best_root = None
        best_sim = -1.0

        for root in current_roots:
            root_emb = self._embedding.get(root, [])
            if not root_emb:
                continue
            sim = _cosine_similarity(embedding, root_emb)
            if sim > best_sim:
                best_sim = sim
                best_root = root

        if best_root is None:
            return None
        return (best_root, best_sim)

    def roots(self) -> list[str]:
        """Return roots in stable insertion order."""
        seen = set()
        ordered = []
        for node_id in self._root_order:
            root = self._find(node_id)
            if root not in seen:
                seen.add(root)
                ordered.append(root)
        return ordered

    def cluster_count(self):
        return len(self.roots())

    def remove_cluster(self, root_id):
        """Remove a cluster by root id. Returns list of removed node ids."""
        root = self._find(root_id)
        members = list(self._children.get(root, {root}))

        for node_id in members:
            self._parent.pop(node_id, None)
            self._content.pop(node_id, None)
            self._embedding.pop(node_id, None)

        self._summary.pop(root, None)
        self._dirty.discard(root)
        self._dirty_inputs.pop(root, None)
        self._children.pop(root, None)
        self._root_order = [node_id for node_id in self._root_order if node_id not in members]

        return members


class ContextWindow:
    """Hot zone + cold forest. Manages graduation and eviction."""

    def __init__(self, embedder, summarizer, graduate_at=26,
                 max_cold_clusters=10,
                 # Cosine similarity threshold for auto-merging clusters (0.15 = ~81° angle)
                 # Range: -1 (opposite) to 1 (identical). 0.15 allows moderately related content to merge.
                 merge_threshold=0.15):
        self._embedder = embedder
        self._forest = Forest(summarizer=summarizer)
        self._hot = []  # list of (content, embedding) tuples
        self._graduated_index = 0  # index into _hot: items before this have graduated
        self._graduate_at = graduate_at
        self._max_cold_clusters = max_cold_clusters
        self._merge_threshold = merge_threshold
        self._next_id = 0

    def _next_msg_id(self):
        mid = f"msg_{self._next_id}"
        self._next_id += 1
        return mid

    def append(self, content):
        """Embed and push to hot zone. Graduate as needed."""
        embedding = self._embedder.embed(content)
        self._hot.append((content, embedding))
        self._maybe_graduate()
        self._trim_graduated()

    def _maybe_graduate(self):
        """Graduate oldest hot messages to cold forest when hot zone overflows."""
        while len(self._hot) - self._graduated_index > self._graduate_at:
            content, embedding = self._hot[self._graduated_index]
            self._graduated_index += 1

            # Find nearest BEFORE inserting so we don't match self
            merge_target = self._forest.nearest_root(embedding)

            msg_id = self._next_msg_id()
            self._forest.insert(msg_id, content, embedding)

            # Merge with nearest cluster if above threshold
            if merge_target is not None:
                nearest_root, similarity = merge_target
                if similarity >= self._merge_threshold:
                    self._forest.union(msg_id, nearest_root)

            # Force merge closest pair if too many clusters
            self._force_merge_if_needed()

    def _force_merge_if_needed(self):
        """Force merge closest pair when cluster count exceeds max.
        
        Unlike normal graduation (which only merges if similarity >= merge_threshold),
        this method performs FORCED merges to enforce the max_cold_clusters limit.
        
        Algorithm:
        1. Find all pairs of cluster roots
        2. Compute cosine similarity for each pair
        3. Merge the pair with highest similarity (even if below merge_threshold)
        4. Repeat until cluster_count <= max_cold_clusters
        
        This is a greedy approach that may merge semantically unrelated clusters
        when the cold forest is full. The alternative would be evicting old clusters,
        but merging preserves all information (albeit with potential quality loss).
        """
        while self._forest.cluster_count() > self._max_cold_clusters:
            roots = self._forest.roots()
            if len(roots) < 2:
                break

            # Find closest pair via exhaustive O(n²) search
            # For n=10 clusters, this is only 45 comparisons - acceptable overhead
            best_sim = -1.0
            best_pair = None
            for i in range(len(roots)):
                for j in range(i + 1, len(roots)):
                    emb_i = self._forest._embedding.get(roots[i], [])
                    emb_j = self._forest._embedding.get(roots[j], [])
                    if emb_i and emb_j:
                        sim = _cosine_similarity(emb_i, emb_j)
                        if sim > best_sim:
                            best_sim = sim
                            best_pair = (roots[i], roots[j])

            if best_pair:
                # Merge the closest pair (ignoring merge_threshold)
                self._forest.union(best_pair[0], best_pair[1])
            else:
                # No valid pairs found (shouldn't happen unless embeddings are missing)
                break

    def force_graduate(self, keep_hot=4):
        """Force-graduate hot messages until only keep_hot remain.

        Used when too_big fires before graduate_at is reached — breaks the
        deadlock between token-based summarization and count-based graduation.
        """
        while self.hot_count > keep_hot:
            content, embedding = self._hot[self._graduated_index]
            self._graduated_index += 1

            merge_target = self._forest.nearest_root(embedding)

            msg_id = self._next_msg_id()
            self._forest.insert(msg_id, content, embedding)

            if merge_target is not None:
                nearest_root, similarity = merge_target
                if similarity >= self._merge_threshold:
                    self._forest.union(msg_id, nearest_root)

            self._force_merge_if_needed()
        self._trim_graduated()

    def _trim_graduated(self):
        """Release graduated entries from _hot to bound memory."""
        if self._graduated_index > 0:
            self._hot = self._hot[self._graduated_index:]
            self._graduated_index = 0

    @property
    def hot_count(self):
        """Number of messages currently in the hot zone (not yet graduated)."""
        return len(self._hot) - self._graduated_index

    @property
    def cold_count(self):
        """Number of clusters in the cold forest."""
        return self._forest.cluster_count()

    def hot_messages(self):
        """Return the current hot-zone messages in order."""
        return [content for content, _embedding in self._hot[self._graduated_index:]]

    def render(self):
        """Return cold summaries + hot contents as a flat list of strings."""
        if not self._hot and self._forest.cluster_count() == 0:
            return []

        parts = []

        # Cold cluster summaries (rendered in stable insertion order)
        for root in self._forest.roots():
            summary = self._forest.compact(root)
            if summary:
                parts.append(summary)

        # Hot zone contents (in order)
        parts.extend(self.hot_messages())

        return parts

    def resolve_dirty(self):
        """Delegate to forest to summarize all dirty clusters."""
        self._forest.resolve_dirty()
