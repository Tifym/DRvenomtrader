from sqlalchemy import String, JSON, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base

class SignalSetting(Base):
    """
    Stores dynamic configuration for each signal type and timeframe.
    parameters field contains the JSON configuration specific to the signal.
    """
    __tablename__ = "signal_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    signal_type: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=False  # ALFA, BETA, DELTA, GAMMA, GLOBAL
    )
    timeframe: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=False  # e.g., '1D', '1H', 'GLOBAL'
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
