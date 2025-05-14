import hashlib
import os
from pathlib import Path
import chromadb
import tiktoken # ChromaDB's default embedding model (all-MiniLM-L6-v2) uses tiktoken
import re
import math
from collections import Counter

from aider.io import InputOutput
from aider.repo import GitRepo # For type hinting

# -----------------------------------------------------------------------------
# Configuration constants
# -----------------------------------------------------------------------------
CHROMA_PERSIST_DIR_NAME = ".aider_chroma_db"
COLLECTION_NAME_PREFIX = "aider_codebase_"
DEFAULT_CONTEXT_FILES = 6
EXPANDED_CONTEXT_FILES = 15
SIMILARITY_THRESHOLD_FOR_EXPANSION = 0.8  # Corresponds to ChromaDB distance < 0.2
MIN_FILES_FOR_EXPANDED_THRESHOLD = 6 # If at least this many files meet the threshold, expand context
INITIAL_QUERY_COUNT = 25 # Used for the *final* reranking query if not further constrained

# Hybrid Search Specific Constants
BM25_CANDIDATE_COUNT = 10
SEMANTIC_CANDIDATE_COUNT_INITIAL = 15
MAX_UNIQUE_CANDIDATES_FOR_RERANK = 20

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv", # Common virtualenv name
    "env",
    ".env", # Common virtualenv name
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "*.egg-info",
    ".aider_chroma_db", # Self-ignore
    ".cache", # General cache
}
# Common binary file extensions to ignore by default
IGNORED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', # Images
    '.mp3', '.wav', '.ogg', '.flac', # Audio
    '.mp4', '.avi', '.mov', '.mkv', # Video
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', # Documents (unless model supports)
    '.zip', '.tar', '.gz', '.rar', '.7z', # Archives
    '.exe', '.dll', '.so', '.dylib', '.app', # Executables/libraries
    '.pyc', '.pyo', # Python compiled
    '.class', # Java compiled
    '.o', '.a', '.obj', # Object files
    '.db', '.sqlite', '.sqlite3', # Databases
    '.DS_Store', # macOS
    '.ipynb', # Jupyter notebooks (often large JSON, better to convert to .py if needed for context)
}


# BM25 Implementation
def tokenize_for_bm25(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) # Remove basic punctuation
    # Consider adding stop word removal later if performance/relevance needs tuning
    return text.split()

class BM25:
    def __init__(self, documents, k1=1.5, b=0.75):
        """
        documents: list of lists of tokens, e.g. [["this","is","a","doc"], …]
        k1, b: BM25 hyperparameters
        """
        self.docs = documents
        self.N = len(documents)
        if self.N == 0: # Handle empty corpus
            self.avgdl = 0
            self.tfs = []
            self.idf = {}
            return

        self.avgdl = sum(len(doc) for doc in documents) / self.N
        self.k1 = k1
        self.b = b

        # term frequencies per document
        self.tfs = [Counter(doc) for doc in documents]
        # document frequencies
        df = {}
        for tf_doc in self.tfs: # Renamed tf to tf_doc to avoid conflict
            for term in tf_doc:
                df[term] = df.get(term, 0) + 1
        # inverse document frequencies (with added smoothing +1)
        self.idf = {
            term: math.log( (self.N - freq + 0.5)/(freq + 0.5) + 1 )
            for term, freq in df.items()
        }

    def score(self, query, index):
        """
        Score a single document (by index) for the given query (list of terms).
        """
        if self.N == 0: return 0.0 # Handle empty corpus

        score = 0.0
        doc_len = len(self.docs[index])
        for term in query:
            if term not in self.idf:
                continue
            freq = self.tfs[index][term]
            denom = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += self.idf[term] * (freq * (self.k1 + 1)) / denom
        return score

    def get_scores(self, query):
        """
        Compute BM25 scores of all documents for the given query.
        Returns a list of floats.
        """
        if self.N == 0: return [] # Handle empty corpus
        return [self.score(query, i) for i in range(self.N)]


class ChromaManager:
    def __init__(self, project_root: Path, io: InputOutput, verbose: bool = False):
        self.project_root = project_root
        self.io = io
        self.verbose = verbose
        self.chroma_persist_path = self.project_root / CHROMA_PERSIST_DIR_NAME

        # BM25 related attributes
        self.bm25_tokenized_corpus: list[list[str]] = []
        self.bm25_file_paths: list[str] = []
        self.bm25_retriever: BM25 | None = None

        try:
            self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_persist_path))
        except Exception as e:
            self.io.tool_error(f"Failed to initialize ChromaDB client: {e}")
            self.io.tool_error("Please ensure ChromaDB is installed correctly (`pip install chromadb`).")
            raise

        project_root_hash = hashlib.md5(str(self.project_root.resolve()).encode()).hexdigest()
        self.collection_name = f"{COLLECTION_NAME_PREFIX}{project_root_hash}"

        try:
            self.code_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
            )
            if self.code_collection.count() > 0:
                self._initialize_bm25_from_chroma_data()
        except Exception as e:
            self.io.tool_error(f"Failed to get or create ChromaDB collection '{self.collection_name}': {e}")
            raise

    def _initialize_bm25_from_chroma_data(self):
        if self.bm25_retriever and self.bm25_tokenized_corpus: # Avoid re-initialization if already done
            if self.verbose: self.io.tool_output("BM25 already initialized.", log_only=True)
            return

        self.io.tool_output("Attempting to initialize BM25 from existing ChromaDB data...", log_only=self.verbose)
        try:
            collection_count = self.code_collection.count()
            if collection_count == 0:
                self.io.tool_output("No documents in ChromaDB to build BM25 index from.", log_only=self.verbose)
                self.bm25_tokenized_corpus = []
                self.bm25_file_paths = []
                self.bm25_retriever = BM25(self.bm25_tokenized_corpus) # Init with empty
                return
            
            all_docs_data = self.code_collection.get(include=['documents', 'ids'])

            if not all_docs_data or not all_docs_data.get('ids'):
                self.io.tool_output("No documents in ChromaDB to build BM25 index from (after get).", log_only=self.verbose)
                self.bm25_tokenized_corpus = []
                self.bm25_file_paths = []
                self.bm25_retriever = BM25(self.bm25_tokenized_corpus)
                return

            temp_corpus = []
            temp_paths = []
            for i, doc_id in enumerate(all_docs_data['ids']):
                content = all_docs_data['documents'][i]
                tokens = tokenize_for_bm25(content)
                temp_corpus.append(tokens)
                temp_paths.append(doc_id)

            if temp_corpus:
                self.bm25_tokenized_corpus = temp_corpus
                self.bm25_file_paths = temp_paths
                self.bm25_retriever = BM25(self.bm25_tokenized_corpus)
                self.io.tool_output(f"BM25 retriever initialized with {len(self.bm25_tokenized_corpus)} documents from ChromaDB.", log_only=self.verbose)
            else:
                self.io.tool_output("BM25 corpus from ChromaDB is empty.", log_only=self.verbose)
                self.bm25_retriever = BM25([]) # Ensure it's an empty BM25

        except Exception as e:
            self.io.tool_error(f"Error initializing BM25 from ChromaDB data: {e}", log_only=True)
            self.bm25_tokenized_corpus = []
            self.bm25_file_paths = []
            self.bm25_retriever = BM25([])

    def is_ignored(self, path: Path, repo: GitRepo | None) -> bool:
        """Check if a path should be ignored."""
        # Check against IGNORED_DIRS
        if any(part in IGNORED_DIRS for part in path.parts):
            if self.verbose: self.io.tool_output(f"Ignoring {path} due to IGNORED_DIRS", log_only=True)
            return True

        # Check against IGNORED_EXTENSIONS
        if path.suffix.lower() in IGNORED_EXTENSIONS:
            if self.verbose: self.io.tool_output(f"Ignoring {path} due to IGNORED_EXTENSIONS", log_only=True)
            return True

        # Check .aiderignore if repo is available
        if repo and repo.ignored_file(path):
            if self.verbose: self.io.tool_output(f"Ignoring {path} due to .aiderignore", log_only=True)
            return True
        
        # Check .gitignore if repo is available
        if repo and repo.git_ignored_file(path):
            if self.verbose: self.io.tool_output(f"Ignoring {path} due to .gitignore", log_only=True)
            return True
            
        return False

    def index_codebase(self, repo: GitRepo | None):
        self.io.tool_output("Checking codebase index...")
        if self.code_collection.count() > 0:
            self.io.tool_output(f"Codebase index already exists with {self.code_collection.count()} documents.")
            return

        self.io.tool_output("Building codebase vector index (this may take a few minutes for large projects)...")
        
        docs_to_add = []
        ids_to_add = []
        metadatas_to_add = []
        files_indexed_count = 0

        for abs_path in self.project_root.rglob("*.*"):
            if not abs_path.is_file():
                continue

            if self.is_ignored(abs_path, repo):
                continue
            
            try:
                # Ensure path is relative to project_root for ID and metadata
                rel_path_str = str(abs_path.relative_to(self.project_root))
                
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                if not content.strip(): # Skip empty or whitespace-only files
                    if self.verbose: self.io.tool_output(f"Skipping empty file: {rel_path_str}", log_only=True)
                    continue

                docs_to_add.append(content)
                ids_to_add.append(rel_path_str) # Use relative path as ID
                metadatas_to_add.append({"path": rel_path_str})
                files_indexed_count += 1

                # Batch add to ChromaDB to avoid overwhelming it / for efficiency
                if len(docs_to_add) >= 100: # Batch size
                    self.code_collection.add(documents=docs_to_add, ids=ids_to_add, metadatas=metadatas_to_add)
                    if self.verbose: self.io.tool_output(f"Indexed batch of {len(docs_to_add)} files.", log_only=True)
                    docs_to_add, ids_to_add, metadatas_to_add = [], [], []

            except Exception as e:
                if self.verbose:
                    self.io.tool_warning(f"Could not read or process file {abs_path}: {e}")
                continue
        
        # Add any remaining documents
        if docs_to_add:
            self.code_collection.add(documents=docs_to_add, ids=ids_to_add, metadatas=metadatas_to_add)
            if self.verbose: self.io.tool_output(f"Indexed final batch of {len(docs_to_add)} files.", log_only=True)

        # ChromaDB's PersistentClient usually auto-persists, but an explicit call can be good.
        # However, `chromadb.PersistentClient` does not have a `persist` method.
        # Persistence is handled automatically on writes for PersistentClient.
        # self.chroma_client.persist() 

        self.io.tool_output(f"Codebase indexing complete. Indexed {files_indexed_count} files.")
        self.io.tool_output(f"Total documents in collection '{self.collection_name}': {self.code_collection.count()}")

        # (Re)Build BM25 index from the now populated/updated ChromaDB
        if self.code_collection.count() > 0:
            self.bm25_retriever = None # Force re-initialization
            self.bm25_tokenized_corpus = []
            self.bm25_file_paths = []
            self._initialize_bm25_from_chroma_data()
        else: # Chroma is empty, so BM25 should be too
            self.bm25_tokenized_corpus = []
            self.bm25_file_paths = []
            self.bm25_retriever = BM25([]) # Init with empty
            self.io.tool_output("BM25 index cleared as ChromaDB collection is empty.", log_only=self.verbose)


    def get_relevant_files_for_prompt(self, prompt_text: str) -> list[str]:
        if not prompt_text:
            return []
        if self.code_collection.count() == 0:
            if self.verbose: self.io.tool_output("Chroma collection is empty.", log_only=True)
            return []

        # --- Stage 1: Candidate Generation ---
        bm25_paths = []
        if self.bm25_retriever and self.bm25_tokenized_corpus:
            query_tokens = tokenize_for_bm25(prompt_text)
            all_bm25_scores = self.bm25_retriever.get_scores(query_tokens)
            
            scored_bm25_files = []
            for i, score in enumerate(all_bm25_scores):
                if score > 0: # Only consider positively scored documents by BM25
                    scored_bm25_files.append((score, self.bm25_file_paths[i]))
            
            scored_bm25_files.sort(key=lambda x: x[0], reverse=True)
            bm25_paths = [path for score, path in scored_bm25_files[:BM25_CANDIDATE_COUNT]]
            if self.verbose: self.io.tool_output(f"BM25 top {len(bm25_paths)} candidates: {bm25_paths}", log_only=True)

        semantic_paths_initial = []
        try:
            initial_semantic_results = self.code_collection.query(
                query_texts=[prompt_text],
                n_results=SEMANTIC_CANDIDATE_COUNT_INITIAL,
                include=['metadatas'] 
            )
            if initial_semantic_results and initial_semantic_results.get('metadatas') and initial_semantic_results['metadatas'][0]:
                semantic_paths_initial = [meta['path'] for meta in initial_semantic_results['metadatas'][0]]
            if self.verbose: self.io.tool_output(f"Initial semantic top {len(semantic_paths_initial)} candidates: {semantic_paths_initial}", log_only=True)
        except Exception as e:
            self.io.tool_error(f"Error in initial semantic query for hybrid search: {e}")

        combined_candidates = bm25_paths + [p for p in semantic_paths_initial if p not in bm25_paths]
        unique_candidates_for_rerank = combined_candidates[:MAX_UNIQUE_CANDIDATES_FOR_RERANK]

        if not unique_candidates_for_rerank:
            if self.verbose: self.io.tool_output("No candidates found from BM25 or initial semantic search.", log_only=True)
            return []
        if self.verbose: self.io.tool_output(f"Total {len(unique_candidates_for_rerank)} unique candidates for reranking: {unique_candidates_for_rerank}", log_only=True)

        # --- Stage 2: Semantic Reranking of Candidates ---
        files_with_scores = []
        try:
            where_filter = {"path": {"$in": unique_candidates_for_rerank}}
            num_rerank_query = min(len(unique_candidates_for_rerank), INITIAL_QUERY_COUNT)

            reranked_results = self.code_collection.query(
                query_texts=[prompt_text],
                n_results=num_rerank_query,
                where=where_filter,
                include=['metadatas', 'distances']
            )

            if reranked_results and reranked_results.get('ids') and reranked_results['ids'][0]:
                for i, path_id in enumerate(reranked_results['ids'][0]):
                    distance = reranked_results['distances'][0][i]
                    similarity = 1 - distance 
                    files_with_scores.append({'path': path_id, 'similarity': similarity})
            
            files_with_scores.sort(key=lambda x: x['similarity'], reverse=True)

        except Exception as e:
            self.io.tool_error(f"Error reranking candidates with ChromaDB: {e}")
            return [] 

        if not files_with_scores:
            if self.verbose: self.io.tool_output("No files after semantic reranking.", log_only=True)
            return []

        # --- Stage 3: Apply File Limit/Threshold Logic (existing logic) ---
        highly_similar_count = 0
        for file_info in files_with_scores:
            if file_info['similarity'] >= SIMILARITY_THRESHOLD_FOR_EXPANSION:
                highly_similar_count += 1
        
        num_to_return = DEFAULT_CONTEXT_FILES
        if highly_similar_count >= MIN_FILES_FOR_EXPANDED_THRESHOLD:
            num_to_return = EXPANDED_CONTEXT_FILES
            if self.verbose: self.io.tool_output(f"Found {highly_similar_count} highly similar files (threshold {SIMILARITY_THRESHOLD_FOR_EXPANSION}), expanding context to {num_to_return} files.", log_only=True)
        elif self.verbose:
                self.io.tool_output(f"Found {highly_similar_count} highly similar files, using default context of {num_to_return} files.", log_only=True)

        relevant_paths = [file_info['path'] for file_info in files_with_scores[:num_to_return]]
        
        if self.verbose:
            self.io.tool_output(f"Hybrid search returning {len(relevant_paths)} files for context:", log_only=True)
            for p_info in files_with_scores[:num_to_return]:
                self.io.tool_output(f"  - {p_info['path']} (similarity: {p_info['similarity']:.4f})", log_only=True)

        return relevant_paths

# Example usage (for testing this file directly, not part of Aider integration)
if __name__ == '__main__':
    # Create a dummy project structure for testing
    current_dir = Path(__file__).parent
    dummy_project_root = current_dir / "dummy_project_for_chroma_test"
    dummy_project_root.mkdir(exist_ok=True)

    (dummy_project_root / ".aider_chroma_db").mkdir(exist_ok=True) # Ensure persist dir exists for client

    (dummy_project_root / "file1.py").write_text("def hello():\n  print('Hello from file1')\n# Python related keywords")
    (dummy_project_root / "file2.js").write_text("function world() {\n  console.log('World from file2');\n// JavaScript related keywords\n}")
    (dummy_project_root / "notes.md").write_text("# Project Notes\nThis project is about testing ChromaDB integration.\nImportant: remember to test similarity.")
    (dummy_project_root / "ignored_dir").mkdir(exist_ok=True)
    (dummy_project_root / "ignored_dir" / "ignored_file.txt").write_text("This should be ignored.")
    (dummy_project_root / ".git").mkdir(exist_ok=True) # To test .git ignore
    (dummy_project_root / "image.png").write_text("binary_data") # To test extension ignore


    class MockIO:
        def tool_output(self, message, log_only=False, bold=False): print(message)
        def tool_warning(self, message): print(f"WARNING: {message}")
        def tool_error(self, message): print(f"ERROR: {message}")

    mock_io = MockIO()
    
    print(f"Testing ChromaManager with dummy project at: {dummy_project_root}")
    
    # Clean up previous DB if it exists, to ensure fresh indexing for test
    import shutil
    chroma_db_path = dummy_project_root / CHROMA_PERSIST_DIR_NAME
    if chroma_db_path.exists():
        print(f"Removing existing ChromaDB for test: {chroma_db_path}")
        shutil.rmtree(chroma_db_path)
        # Recreate the directory as PersistentClient expects it to exist
        chroma_db_path.mkdir()


    manager = ChromaManager(project_root=dummy_project_root, io=mock_io, verbose=True)
    manager.index_codebase(repo=None) # Passing None for repo in this standalone test

    print("\n--- Querying for 'Python hello function' ---")
    relevant_files = manager.get_relevant_files_for_prompt("Python hello function")
    print(f"Relevant files: {relevant_files}")

    print("\n--- Querying for 'JavaScript console log' ---")
    relevant_files_js = manager.get_relevant_files_for_prompt("JavaScript console log")
    print(f"Relevant files for JS: {relevant_files_js}")

    print("\n--- Querying for 'similarity project notes' ---") # Should pick up notes.md
    relevant_files_md = manager.get_relevant_files_for_prompt("similarity project notes")
    print(f"Relevant files for MD: {relevant_files_md}")
    
    # Clean up dummy project
    # print(f"\nCleaning up dummy project: {dummy_project_root}")
    # shutil.rmtree(dummy_project_root)
    print(f"\nTest complete. Dummy project and DB at {dummy_project_root} can be manually inspected or deleted.")
