"""
Dr. Venom Trader - SQLAlchemy ORM Models
Defines the core database schema for signals, candles, and alerts.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, Text, Enum as SAEnum,
    ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Symbol(Base):
    """Tracked trading symbols (e.g., BTCUSDT)."""
    __tablename__ = "symbols"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), default="binance")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    signals = relationship("SignalState", back_populates="symbol", cascade="all, delete-orphan")


class SignalState(Base):
    """
    Stores the current state of each signal for a symbol + timeframe.
    Updated in real-time by the signal engine.
    """
    __tablename__ = "signal_states"
    __table_args__ = (
        Index("ix_signal_lookup", "symbol_id", "signal_type", "timeframe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("symbols.id"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(
        String(10), nullable=False  # ALFA, BETA, DELTA, GAMMA
    )
    timeframe: Mapped[str] = mapped_column(
        String(10), nullable=False  # 1D, 4H, 1H, 15m, etc.
    )
    direction: Mapped[str] = mapped_column(
        String(10), nullable=True  # LONG, SHORT, NEUTRAL
    )
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string with extra data
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    symbol = relationship("Symbol", back_populates="signals")


class AlertLog(Base):
    """Log of all alerts sent (Telegram, Discord, browser)."""
    __tablename__ = "alert_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # telegram, discord, browser
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
