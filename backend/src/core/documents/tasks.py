import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from celery_app import celery_app
from config import settings
from core.documents.text_extractor import extract_text
from unit_of_work.uow import UnitOfWorkImpl

logger = logging.getLogger(__name__)


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task
def run_document_summary(
    version_id: str, document_name: str, document_file: str
) -> None:
    asyncio.run(_run_document_summary(version_id, document_name, document_file))


async def _run_document_summary(
    version_id: str, document_name: str, document_file: str
) -> None:
    from core.documents.agents import DocumentAgentServiceImpl

    logger.info(
        "Summary task started (version_id=%s, document=%r)", version_id, document_name
    )
    try:
        text = await extract_text(document_file)
        if not text:
            logger.info(
                "Summary task: skipped — no extractable text (version_id=%s, file=%s)",
                version_id,
                document_file,
            )
            return

        logger.debug(
            "Summary task: generating summary (%d chars) for %r",
            len(text),
            document_name,
        )
        agent_service = DocumentAgentServiceImpl()
        summary = await agent_service.generate_summary(text, document_name)

        uow = UnitOfWorkImpl(session_factory=_make_session_factory())
        async with uow:
            await uow.document_repository.update_version_summary(
                UUID(version_id), summary
            )
            await uow.commit()

        logger.info(
            "Summary task completed (version_id=%s, document=%r, summary_len=%d)",
            version_id,
            document_name,
            len(summary),
        )
    except Exception:
        logger.exception(
            "Summary task failed (version_id=%s, document=%r)", version_id, document_name
        )


@celery_app.task
def run_document_embedding(version_id: str, document_file: str) -> None:
    asyncio.run(_run_document_embedding(version_id, document_file))


async def _run_document_embedding(version_id: str, document_file: str) -> None:
    from langchain_ollama import OllamaEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from core.documents.rag import RagServiceImpl

    logger.info("Embedding task started (version_id=%s)", version_id)
    try:
        embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_EMBED_MODEL
        )
        splitter = RecursiveCharacterTextSplitter(chunk_size=1_000, chunk_overlap=150)
        rag_service = RagServiceImpl(
            embeddings=embeddings,
            splitter=splitter,
            chroma_dir=settings.CHROMA_DIR,
        )
        await rag_service.build_vectorstore(version_id, document_file)
        logger.info("Embedding task completed (version_id=%s)", version_id)
    except Exception:
        logger.exception("Embedding task failed (version_id=%s)", version_id)