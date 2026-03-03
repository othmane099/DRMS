import logging
from pathlib import Path
from typing import Protocol

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.documents.text_extractor import extract_text

logger = logging.getLogger(__name__)

_TOP_K = 5


class RagService(Protocol):
    async def build_vectorstore(self, version_id: str, file_path: str) -> None: ...

    async def retrieve_context(self, version_id: str, query: str) -> str: ...


class RagServiceImpl(RagService):
    def __init__(
        self,
        embeddings: OllamaEmbeddings,
        splitter: RecursiveCharacterTextSplitter,
        chroma_dir: str,
    ) -> None:
        self._embeddings = embeddings
        self._splitter = splitter
        self._chroma_dir = Path(chroma_dir)

    def _collection_name(self, version_id: str) -> str:
        return f"doc_{version_id.replace('-', '')}"

    async def build_vectorstore(self, version_id: str, file_path: str) -> None:
        """Extract, chunk, embed, and persist a ChromaDB collection for this version."""
        text = await extract_text(file_path)
        if not text:
            logger.info(
                "build_vectorstore: no extractable text for version %s", version_id
            )
            return

        docs = self._splitter.create_documents([text])

        collection = self._collection_name(version_id)
        persist_dir = str(self._chroma_dir / collection)
        store = Chroma(
            collection_name=collection,
            embedding_function=self._embeddings,
            persist_directory=persist_dir,
        )
        store.add_documents(docs)
        logger.info(
            "build_vectorstore: indexed %d chunks for version %s", len(docs), version_id
        )

    async def retrieve_context(self, version_id: str, query: str) -> str:
        """Return top-k relevant chunks as a single context string."""
        collection = self._collection_name(version_id)
        persist_dir = self._chroma_dir / collection
        if not persist_dir.exists():
            return ""

        store = Chroma(
            collection_name=collection,
            embedding_function=self._embeddings,
            persist_directory=str(persist_dir),
        )
        if store._collection.count() == 0:
            return ""

        results = store.similarity_search(query, k=_TOP_K)
        return "\n\n".join(doc.page_content for doc in results)
