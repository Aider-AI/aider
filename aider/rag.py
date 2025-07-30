from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from langchain_voyageai import VoyageAIEmbeddings
from aider.io import InputOutput
from chromadb import Embeddings, chromadb, Where
from typing import cast
from os import environ, getcwd
from posixpath import join as pathjoin
from zlib import crc32


class RagManager:
    def __init__(self, io: InputOutput):
        if environ.get("VOYAGE_API_KEY") is None:
            raise EnvironmentError("Voyage.ai api key environment variable not set.")

        self._io = io
        self._voyage_embeddings = VoyageAIEmbeddings(model="voyage-3.5")
        self._chromadb_client = chromadb.PersistentClient(
            path=pathjoin(getcwd(), ".aider.chroma"))
        self._chromadb_collection = self._chromadb_client.get_or_create_collection(
            name="aider-rag", embedding_function=None)

    def _get_chunk_ids(self, chunks: list[Document]):
        return [f"{doc.metadata['file_name']}#{i}" for i, doc in enumerate(chunks)]

    def _store_embeddings(self, chunks: list[Document], embeddings: list[list[float]]):
        return self._chromadb_collection.upsert(
            ids=self._get_chunk_ids(chunks),
            documents=[doc.page_content for doc in chunks],
            metadatas=[doc.metadata for doc in chunks],
            embeddings=cast(Embeddings, embeddings)
        )

    def _retrieve_embeddings(self, embeddings: list[list[float]], file_names: list[str]):
        return self._chromadb_collection.query(query_embeddings=cast(Embeddings, embeddings), where=cast(Where, {"file_name": {"$in": file_names}}))

    def _get_stored_crc32_hash(self, fname: str):
        first_chunk_id = f"{fname}#0"
        stored_chunk_metadatas = self._chromadb_collection.get(
            ids=first_chunk_id, include=["metadatas"]).get("metadatas")

        if stored_chunk_metadatas is None or len(stored_chunk_metadatas) == 0:
            return None
        return cast(int, stored_chunk_metadatas[0].get("crc32_hash"))

    def chunk_files(self, file_names: list[str]):
        all_chunks: list[list[Document]] = []
        for fname in file_names:
            content = self._io.read_text(fname)
            if not content:
                self._io.tool_output(f"File {fname} is empty.")
                continue

            file_crc32_hash = crc32(content.encode('utf-8'))
            stored_crc32_hash = self._get_stored_crc32_hash(fname)
            if file_crc32_hash == stored_crc32_hash:
                continue

            self._io.tool_output(f"Chunking {fname}")
            chunker = SemanticChunker(self._voyage_embeddings)
            file_chunks = chunker.create_documents(
                [content], [{"file_name": fname, "crc32_hash": file_crc32_hash}])
            all_chunks.append(file_chunks)

        return all_chunks

    def embed_store_chunks(self, all_chunks: list[list[Document]]):
        for file_chunks in all_chunks:
            fname = file_chunks[0].metadata["file_name"]
            self._io.tool_output(f"Embedding and storing {fname}")
            file_chunk_ids = self._get_chunk_ids(file_chunks)

            self._chromadb_collection.delete(ids=file_chunk_ids)

            texts = [doc.page_content for doc in file_chunks]
            embeddings = self._voyage_embeddings.embed_documents(texts)
            self._store_embeddings(file_chunks, embeddings)
        return None

    def embed_retrieve_query(self, query: str, file_names: list[str]):
        embedded_query = self._voyage_embeddings.embed_query(query)
        retrieved_results = self._retrieve_embeddings([embedded_query], file_names)

        return retrieved_results
