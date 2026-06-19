import logging
from typing import Protocol

from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

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
        qdrant_url: str,
    ) -> None:
        self._embeddings = embeddings
        self._splitter = splitter
        self._qdrant_url = qdrant_url

    def _collection_name(self, version_id: str) -> str:
        return f"doc_{version_id.replace('-', '')}"

    async def build_vectorstore(self, version_id: str, file_path: str) -> None:
        text = await extract_text(file_path)
        if not text:
            logger.info(
                "build_vectorstore: no extractable text for version %s", version_id
            )
            return

        docs = self._splitter.create_documents([text])
        collection = self._collection_name(version_id)
        QdrantVectorStore.from_documents(
            docs,
            self._embeddings,
            url=self._qdrant_url,
            collection_name=collection,
            force_recreate=True,
        )
        logger.info(
            "build_vectorstore: indexed %d chunks for version %s", len(docs), version_id
        )

    async def retrieve_context(self, version_id: str, query: str) -> str:
        collection = self._collection_name(version_id)
        client = QdrantClient(url=self._qdrant_url)
        try:
            exists = client.collection_exists(collection)
        except Exception:
            return ""
        if not exists:
            return ""

        store = QdrantVectorStore(
            client=client,
            collection_name=collection,
            embedding=self._embeddings,
        )
        results = store.similarity_search(query, k=_TOP_K)
        return "\n\n".join(doc.page_content for doc in results)