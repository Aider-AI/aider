"""Forest (union-find cluster store) and ContextWindow (hot zone + cold forest).

Ported from gemini-cli's contextWindow.ts, adapted for aider's message model.
"""

import math


def _cosine_similarity(a, b):
    """Cosine similarity between two sparse dict vectors. Returns 0.0 if either is zero."""
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
        total = size_new + size_old
        emb_a = self._embedding.get(new_root, {})
        emb_b = self._embedding.get(old_root, {})
        if emb_a or emb_b:
            all_keys = set(emb_a.keys()) | set(emb_b.keys())
            self._embedding[new_root] = {
                k: (emb_a.get(k, 0.0) * size_new + emb_b.get(k, 0.0) * size_old) / total
                for k in all_keys
            }

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
            root_emb = self._embedding.get(root, {})
            if not root_emb:
                continue
            sim = _cosine_similarity(embedding, root_emb)
            if sim > best_sim:
                best_sim = sim
                best_root = root

        if best_root is None:
            return None
        return (best_root, best_sim)

    def roots(self):
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


class ContextWindow:
    """Hot zone + cold forest. Manages graduation and eviction."""

    def __init__(self, embedder, summarizer, graduate_at=26,
                 max_cold_clusters=10, merge_threshold=0.15):
        self._embedder = embedder
        self._forest = Forest(summarizer=summarizer)
        self._hot = []  # list of (content, embedding) tuples
        self._graduated_index = 0  # index into _hot: items before this have graduated
        self._graduate_at = graduate_at
        self._max_cold_clusters = max_cold_clusters
        self._merge_threshold = merge_threshold
        self._next_id = 0

    def _gen_id(self):
        mid = f"msg_{self._next_id}"
        self._next_id += 1
        return mid

    def append(self, content):
        """Embed and push to hot zone. Graduate as needed."""
        embedding = self._embedder.embed(content)
        self._hot.append((content, embedding))
        self._maybe_graduate()

    def _maybe_graduate(self):
        """Graduate oldest hot messages to cold forest when hot zone overflows."""
        graduated_count = 0
        while len(self._hot) - self._graduated_index > self._graduate_at:
            content, embedding = self._hot[self._graduated_index]
            self._graduated_index += 1
            graduated_count += 1

            # Find nearest BEFORE inserting so we don't match self
            merge_target = self._forest.nearest_root(embedding)

            msg_id = self._gen_id()
            self._forest.insert(msg_id, content, embedding)

            # Merge with nearest cluster if above threshold
            if merge_target is not None:
                nearest_root, similarity = merge_target
                if similarity >= self._merge_threshold:
                    self._forest.union(msg_id, nearest_root)

            # Force merge closest pair if too many clusters
            self._force_merge_if_needed()
        
        # Trim graduated entries after the loop completes
        if graduated_count > 0:
            self._trim_graduated()

    def _force_merge_if_needed(self):
        """Force merge closest pair when cluster count exceeds max."""
        while self._forest.cluster_count() > self._max_cold_clusters:
            roots = self._forest.roots()
            if len(roots) < 2:
                break

            # Find closest pair
            best_sim = -1.0
            best_pair = None
            for i in range(len(roots)):
                for j in range(i + 1, len(roots)):
                    emb_i = self._forest._embedding.get(roots[i], {})
                    emb_j = self._forest._embedding.get(roots[j], {})
                    if emb_i and emb_j:
                        sim = _cosine_similarity(emb_i, emb_j)
                        if sim > best_sim:
                            best_sim = sim
                            best_pair = (roots[i], roots[j])

            if best_pair:
                self._forest.union(best_pair[0], best_pair[1])
            else:
                break

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
        for content, _embedding in self._hot[self._graduated_index:]:
            parts.append(content)

        return parts

    def resolve_dirty(self):
        """Delegate to forest to summarize all dirty clusters."""
        self._forest.resolve_dirty()
