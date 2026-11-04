import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class EntityType(Base):
    __tablename__ = "entity_types"; __table_args__ = {"schema": "meta"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class PropertyGroup(Base):
    __tablename__ = "property_groups"; __table_args__ = {"schema": "meta"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class PropertyDefinition(Base):
    __tablename__ = "property_definitions"; __table_args__ = (UniqueConstraint("entity_type_id", "name"), {"schema": "meta"})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type_id: Mapped[int] = mapped_column(ForeignKey("meta.entity_types.id", ondelete="CASCADE"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("meta.property_groups.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enum_values: Mapped[list | None] = mapped_column(JSONB)


class Tag(Base):
    __tablename__ = "tags"; __table_args__ = {"schema": "shared"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))


class EntityTag(Base):
    __tablename__ = "entity_tags"; __table_args__ = {"schema": "shared"}
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shared.tags.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LinkType(Base):
    __tablename__ = "link_types"; __table_args__ = {"schema": "shared"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    inverse_label: Mapped[str | None] = mapped_column(String(255))


class Link(Base):
    __tablename__ = "links"; __table_args__ = {"schema": "shared"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.entities.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.entities.id", ondelete="CASCADE"), nullable=False)
    link_type_id: Mapped[int] = mapped_column(ForeignKey("shared.link_types.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class File(Base):
    __tablename__ = "files"; __table_args__ = {"schema": "shared"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityFile(Base):
    __tablename__ = "entity_files"; __table_args__ = {"schema": "shared"}
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shared.files.id", ondelete="CASCADE"), primary_key=True)
    caption: Mapped[str | None] = mapped_column(Text)


class Person(Base):
    __tablename__ = "persons"; __table_args__ = {"schema": "people"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100)); last_name: Mapped[str | None] = mapped_column(String(100))
    birthday: Mapped[datetime | None] = mapped_column(DateTime(timezone=True)); notes: Mapped[str | None] = mapped_column(Text)
    search_vector = mapped_column(TSVECTOR, __import__("sqlalchemy").Computed("to_tsvector('simple', coalesce(display_name,'') || ' ' || coalesce(notes,''))", persisted=True), nullable=True)


class Contact(Base):
    __tablename__ = "contacts"; __table_args__ = {"schema": "people"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False); value: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100)); is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Relationship(Base):
    __tablename__ = "relationships"; __table_args__ = {"schema": "people"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False)
    related_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False); notes: Mapped[str | None] = mapped_column(Text)


class Place(Base):
    __tablename__ = "places"; __table_args__ = {"schema": "places"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False); description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text); latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    search_vector = mapped_column(TSVECTOR, __import__("sqlalchemy").Computed("to_tsvector('simple', coalesce(name,'') || ' ' || coalesce(description,''))", persisted=True), nullable=True)


class Visit(Base):
    __tablename__ = "visits"; __table_args__ = {"schema": "places"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.places.id", ondelete="CASCADE"), nullable=False)
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text); person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("people.persons.id"))


class Event(Base):
    __tablename__ = "events"; __table_args__ = {"schema": "events"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False); description: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False); ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    place_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("places.places.id", ondelete="SET NULL"))
    search_vector = mapped_column(TSVECTOR, __import__("sqlalchemy").Computed("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))", persisted=True), nullable=True)


class Participant(Base):
    __tablename__ = "participants"; __table_args__ = {"schema": "events"}
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.events.id", ondelete="CASCADE"), primary_key=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("people.persons.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(100)); response: Mapped[str | None] = mapped_column(String(50))


class KnowledgeItem(Base):
    __tablename__ = "items"; __table_args__ = {"schema": "knowledge"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    entity_type_id: Mapped[int] = mapped_column(ForeignKey("meta.entity_types.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False); description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text); properties: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    search_vector = mapped_column(TSVECTOR, __import__("sqlalchemy").Computed("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(notes,''))", persisted=True), nullable=True)


class Building(Base):
    __tablename__ = "buildings"; __table_args__ = {"schema": "buildings"}
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
