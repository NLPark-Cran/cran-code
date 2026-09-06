"""SQLAlchemy ORM models for Cran Code collaboration platform."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cran_code.web.db.connection import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class TeamMemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class ProjectMemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class ActivityType(str, enum.Enum):
    message_sent = "message_sent"
    file_edited = "file_edited"
    file_deleted = "file_deleted"
    file_uploaded = "file_uploaded"
    file_downloaded = "file_downloaded"
    command_run = "command_run"
    session_created = "session_created"
    session_forked = "session_forked"
    commit_pushed = "commit_pushed"
    review_submitted = "review_submitted"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    env_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Per-user environment/preference template, injected into a session's first prompt."""
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.user,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owned_teams: Mapped[list["Team"]] = relationship(
        "Team", back_populates="owner", foreign_keys="Team.owner_id"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="user"
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="user"
    )
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """IANA display timezone for team usage statistics (None = UTC)."""
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_teams", foreign_keys=[owner_id]
    )
    members: Mapped[list["TeamMember"]] = relationship("TeamMember", back_populates="team")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[TeamMemberRole] = mapped_column(
        Enum(TeamMemberRole, native_enum=False),
        default=TeamMemberRole.member,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="team_memberships")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
        {"sqlite_autoincrement": False},
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_dir: Mapped[str | None] = mapped_column(String(500), nullable=True)
    git_repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    team: Mapped["Team"] = relationship("Team", back_populates="projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project"
    )
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="project")

    __table_args__ = (
        UniqueConstraint("team_id", "slug", name="uq_project_team_slug"),
        {"sqlite_autoincrement": False},
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(ProjectMemberRole, native_enum=False),
        default=ProjectMemberRole.member,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        {"sqlite_autoincrement": False},
    )


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, native_enum=False),
        nullable=False,
    )
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="activities")
    user: Mapped["User | None"] = relationship("User", back_populates="activities")


class UserProviderKey(Base):
    """Per-user API key for an LLM provider (highest resolution priority)."""

    __tablename__ = "user_provider_keys"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "provider_key", name="uq_user_provider_key"),
    )


class TeamProviderKey(Base):
    """Per-team API key for an LLM provider (shared by team members)."""

    __tablename__ = "team_provider_keys"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("team_id", "provider_key", name="uq_team_provider_key"),
    )


class ProviderPolicy(Base):
    """Sharing policy for a provider's global (config.toml) API key.

    ``shared_mode`` is ``"all"`` (any authenticated user may use the global
    key) or ``"restricted"`` (only global admins or users/teams with a
    :class:`ProviderGrant`). A missing row means ``"all"``.
    """

    __tablename__ = "provider_policies"

    provider_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    shared_mode: Mapped[str] = mapped_column(String(20), default="all", nullable=False)


class ProviderGrant(Base):
    """Access grant (with optional token quota) for a restricted provider."""

    __tablename__ = "provider_grants"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "user" | "team"
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    quota_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Token quota for ``source='shared'`` usage; ``None`` means unlimited."""
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "provider_key", "subject_type", "subject_id", name="uq_provider_grant"
        ),
    )


class UsageRecord(Base):
    """Token usage record for a single model call."""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # personal|team|shared
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )
