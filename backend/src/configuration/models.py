from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base


class Stage(Base):  # type: ignore
    __tablename__ = "stages"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    title = Column(String(255), nullable=False, unique=True)
    color = Column(String(7), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


class Category(Base):  # type: ignore
    __tablename__ = "categories"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    title = Column(String(255), nullable=False, unique=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    subcategories = relationship("Subcategory", back_populates="category")
    documents = relationship("Document", back_populates="category")


class Subcategory(Base):  # type: ignore
    __tablename__ = "subcategories"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    title = Column(String(255), nullable=False, unique=True)
    category_id = Column(UUID, ForeignKey("categories.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    category = relationship("Category", back_populates="subcategories")
    documents = relationship("Document", back_populates="subcategory")


class Tag(Base):  # type: ignore
    __tablename__ = "tags"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    title = Column(String(255), nullable=False, unique=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    documents = relationship(
        "Document", secondary="document_tags", back_populates="tags"
    )
