import enum
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import ENUM, JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id", UUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        UUID,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column(
        "user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        UUID,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):  # type: ignore
    __tablename__ = "roles"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    users = relationship("User", back_populates="role")
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id}, name={self.name})"


class Permission(Base):  # type: ignore
    __tablename__ = "permissions"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )
    users = relationship(
        "User",
        secondary=user_permissions,
        back_populates="custom_permissions",
    )

    def __repr__(self) -> str:
        return f"Permission(id={self.id}, code={self.code})"


class User(Base):  # type: ignore
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    role_id = Column(UUID, ForeignKey("roles.id"), nullable=True)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=True)

    role = relationship("Role", back_populates="users")
    sessions = relationship("Session", back_populates="user")
    logged_histories = relationship("LoggedHistory", back_populates="user")
    custom_permissions = relationship(
        "Permission",
        secondary=user_permissions,
        back_populates="users",
    )
    documents = relationship(
        "Document", back_populates="creator", foreign_keys="Document.created_by"
    )
    shared_documents = relationship("ShareDocument", back_populates="user")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username})"


class Session(Base):  # type: ignore
    __tablename__ = "sessions"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    token = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expired_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)

    user = relationship(User, back_populates="sessions")

    @property
    def expires_in(self) -> int:
        return int(self.expired_at.timestamp() - self.created_at.timestamp())

    def __repr__(self) -> str:
        return f"Session(id={self.id}, token={self.token}, user_id={self.user_id}, expires_in={self.expires_in}, is_active={self.is_active})"


class LoggedHistoryType(enum.Enum):
    LOGIN = "login"
    FAILED_LOGIN = "failed_login"


class LoggedHistory(Base):  # type: ignore
    __tablename__ = "logged_histories"

    id = Column(UUID, primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    ip = Column(String(255), nullable=True)
    date = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSON, nullable=True)
    type = Column(ENUM(LoggedHistoryType), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="logged_histories")

    def __repr__(self) -> str:
        return f"LoggedHistory(id={self.id}, user_id={self.user_id}, type={self.type})"
