from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text
# Support both package mode (server.*) and flat mode (files at root)
try:
  from .db import Base
except Exception:
  from db import Base


class Appointment(Base):
  __tablename__ = "appointments"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  staff_id: Mapped[str] = mapped_column(String(64), index=True)
  start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
  duration_min: Mapped[int] = mapped_column(Integer, default=30)
  name: Mapped[str] = mapped_column(String(120))
  email: Mapped[str] = mapped_column(String(200))
  phone: Mapped[str] = mapped_column(String(64), default="")
  notes: Mapped[str] = mapped_column(Text, default="")
  created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)




