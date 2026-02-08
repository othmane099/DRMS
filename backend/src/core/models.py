from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base

# Association table for Document-Tag many-to-many relationship
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", UUID, ForeignKey("documents.id"), primary_key=True),
    Column("tag_id", UUID, ForeignKey("tags.id"), primary_key=True),
)

# Association table for Reminder-User many-to-many relationship
reminder_users = Table(
    "reminder_users",
    Base.metadata,
    Column("reminder_id", UUID, ForeignKey("reminders.id"), primary_key=True),
    Column("user_id", UUID, ForeignKey("users.id"), primary_key=True),
)


class Document(Base):  # type: ignore
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    category_id = Column(UUID, ForeignKey("categories.id"), nullable=False)
    subcategory_id = Column(UUID, ForeignKey("subcategories.id"), nullable=False)
    stage_id = Column(UUID, ForeignKey("stages.id"), nullable=False)
    assigned_to = Column(UUID, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    archive = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    category = relationship(
        "Category", back_populates="documents", foreign_keys=[category_id]
    )
    subcategory = relationship(
        "Subcategory", back_populates="documents", foreign_keys=[subcategory_id]
    )
    stage = relationship("Stage", foreign_keys=[stage_id])
    creator = relationship(
        "User", back_populates="documents", foreign_keys=[created_by]
    )
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    versions = relationship("VersionHistory", back_populates="document")
    histories = relationship("DocumentHistory", back_populates="document")
    comments = relationship("DocumentComment", back_populates="document")
    tags = relationship("Tag", secondary=document_tags, back_populates="documents")
    shares = relationship("ShareDocument", back_populates="document")
    reminders = relationship("Reminder", back_populates="document")


class VersionHistory(Base):  # type: ignore
    __tablename__ = "version_histories"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    document_id = Column(UUID, ForeignKey("documents.id"), nullable=False)
    document_file = Column(String(500), nullable=False)
    version_number = Column(Integer, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])


class DocumentHistory(Base):  # type: ignore
    __tablename__ = "document_histories"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    document_id = Column(
        UUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document = relationship("Document", back_populates="histories")
    creator = relationship("User", foreign_keys=[created_by])


class DocumentComment(Base):  # type: ignore
    __tablename__ = "document_comments"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    document_id = Column(UUID, ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    document = relationship("Document", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])


class ShareDocument(Base):  # type: ignore
    __tablename__ = "share_documents"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    document_id = Column(UUID, ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    user = relationship("User", back_populates="shared_documents")
    document = relationship("Document", back_populates="shares")


class Reminder(Base):  # type: ignore
    __tablename__ = "reminders"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    document_id = Column(
        UUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=False
    )
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    document = relationship("Document", back_populates="reminders")
    creator = relationship("User", foreign_keys=[created_by])
    assigned_users = relationship("User", secondary=reminder_users, backref="reminders")
