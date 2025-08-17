"""SQLAlchemy model for a show."""
from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.dialects.mysql import JSON

from tvbingefriend_show_service.models.base import Base


class Show(Base):
    """SQLAlchemy model for a show."""
    __tablename__ = "shows"

    # Attributes
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    url: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str | None] = mapped_column(String(255))
    genres: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(255))
    runtime: Mapped[int | None] = mapped_column(Integer)
    averageRuntime: Mapped[int | None] = mapped_column(Integer)
    premiered: Mapped[str | None] = mapped_column(String(255))
    ended: Mapped[str | None] = mapped_column(String(255))
    officialSite: Mapped[str | None] = mapped_column(String(255))
    schedule: Mapped[dict | None] = mapped_column(JSON)
    rating: Mapped[dict | None] = mapped_column(JSON)
    weight: Mapped[int | None] = mapped_column(Integer)
    network: Mapped[dict | None] = mapped_column(JSON)
    webchannel: Mapped[dict | None] = mapped_column(JSON)
    dvdCountry: Mapped[dict | None] = mapped_column(JSON)
    externals: Mapped[dict | None] = mapped_column(JSON)
    image: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)
    updated: Mapped[int | None] = mapped_column(Integer)
    _links: Mapped[dict | None] = mapped_column(JSON)
