"""SQLAlchemy persistence models for incident review and memory."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    overview: Mapped[str] = mapped_column(Text, nullable=False)
    dimension_signatures: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    related_incidents: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    related_deployments: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    estimated_impact: Mapped[float | None] = mapped_column(Float)
    approval_rate_drop: Mapped[float | None] = mapped_column(Float)
    affected_transaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_read: Mapped[bool] = mapped_column(nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("severity IN ('urgent', 'high', 'medium', 'low')"),
        CheckConstraint("status IN ('open', 'closed', 'needs_action')"),
    )


class IncidentMemory(Base):
    __tablename__ = "incident_memory"

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), primary_key=True
    )
    searchable_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DeploymentLog(Base):
    __tablename__ = "deployment_logs"

    deploy_id: Mapped[str] = mapped_column(Text, primary_key=True)
    description_of_deploy: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions_affected: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
