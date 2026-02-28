import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from core.documents.text_extractor import extract_text

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1_000
_CHUNK_OVERLAP = 150
_TOP_K = 5


def _collection_name(version_id: str) -> str:
    return f"doc_{version_id.replace('-', '')}"


def _embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_EMBED_MODEL)


async def build_vectorstore(version_id: str, file_path: str) -> None:
    """Extract, chunk, embed, and persist a ChromaDB collection for this version."""
    text = await extract_text(file_path)
    if not text:
        logger.info("build_vectorstore: no extractable text for version %s", version_id)
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP
    )
    docs = splitter.create_documents([text])

    persist_dir = str(Path(settings.CHROMA_DIR) / _collection_name(version_id))
    store = Chroma(
        collection_name=_collection_name(version_id),
        embedding_function=_embeddings(),
        persist_directory=persist_dir,
    )
    store.add_documents(docs)
    logger.info(
        "build_vectorstore: indexed %d chunks for version %s", len(docs), version_id
    )


async def retrieve_context(version_id: str, query: str) -> str:
    """Return top-k relevant chunks as a single context string."""
    persist_dir = str(Path(settings.CHROMA_DIR) / _collection_name(version_id))
    if not Path(persist_dir).exists():
        return ""

    store = Chroma(
        collection_name=_collection_name(version_id),
        embedding_function=_embeddings(),
        persist_directory=persist_dir,
    )
    if store._collection.count() == 0:
        return ""

    results = store.similarity_search(query, k=_TOP_K)
    return "\n\n".join(doc.page_content for doc in results)
