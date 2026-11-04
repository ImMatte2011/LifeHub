"""Meta, shared services and extensible domain modules."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def upgrade():
    for schema in ("meta", "shared", "people", "places", "events", "knowledge", "buildings"):
        op.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    op.create_table("entity_types", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("module", sa.String(100), nullable=False), sa.Column("label", sa.String(255), nullable=False), schema="meta")
    op.create_table("property_groups", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("label", sa.String(255), nullable=False), schema="meta")
    op.create_table("property_definitions", sa.Column("id", sa.Integer, primary_key=True), sa.Column("entity_type_id", sa.Integer, sa.ForeignKey("meta.entity_types.id", ondelete="CASCADE"), nullable=False), sa.Column("group_id", sa.Integer, sa.ForeignKey("meta.property_groups.id")), sa.Column("name", sa.String(100), nullable=False), sa.Column("label", sa.String(255), nullable=False), sa.Column("data_type", sa.String(50), nullable=False), sa.Column("required", sa.Boolean, nullable=False, server_default=sa.false()), sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"), sa.Column("enum_values", JSONB), sa.UniqueConstraint("entity_type_id", "name"), schema="meta")

    op.create_table("tags", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("color", sa.String(7)), schema="shared")
    op.create_table("entity_tags", sa.Column("entity_id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("tag_id", UUID, sa.ForeignKey("shared.tags.id", ondelete="CASCADE"), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), schema="shared")
    op.create_table("link_types", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), sa.Column("label", sa.String(255), nullable=False), sa.Column("inverse_label", sa.String(255)), schema="shared")
    op.create_table("links", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("source_id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), nullable=False), sa.Column("target_id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), nullable=False), sa.Column("link_type_id", sa.Integer, sa.ForeignKey("shared.link_types.id"), nullable=False), sa.Column("notes", sa.Text), schema="shared")
    op.create_table("files", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("storage_key", sa.String(500), nullable=False, unique=True), sa.Column("filename", sa.String(255), nullable=False), sa.Column("mime_type", sa.String(255)), sa.Column("size_bytes", sa.Integer, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), schema="shared")
    op.create_table("entity_files", sa.Column("entity_id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("file_id", UUID, sa.ForeignKey("shared.files.id", ondelete="CASCADE"), primary_key=True), sa.Column("caption", sa.Text), schema="shared")

    op.create_table("persons", sa.Column("id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("first_name", sa.String(100)), sa.Column("last_name", sa.String(100)), sa.Column("birthday", sa.DateTime(timezone=True)), sa.Column("notes", sa.Text), sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed("to_tsvector('simple', coalesce(display_name,'') || ' ' || coalesce(notes,''))", persisted=True)), schema="people")
    op.create_index("ix_people_persons_search", "persons", ["search_vector"], schema="people", postgresql_using="gin")
    op.create_table("contacts", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("person_id", UUID, sa.ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False), sa.Column("kind", sa.String(50), nullable=False), sa.Column("value", sa.String(500), nullable=False), sa.Column("label", sa.String(100)), sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()), schema="people")
    op.create_table("relationships", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("person_id", UUID, sa.ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False), sa.Column("related_person_id", UUID, sa.ForeignKey("people.persons.id", ondelete="CASCADE"), nullable=False), sa.Column("relationship_type", sa.String(100), nullable=False), sa.Column("notes", sa.Text), sa.CheckConstraint("person_id <> related_person_id"), schema="people")

    op.create_table("places", sa.Column("id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text), sa.Column("address", sa.Text), sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float), sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed("to_tsvector('simple', coalesce(name,'') || ' ' || coalesce(description,''))", persisted=True)), schema="places")
    op.create_index("ix_places_places_search", "places", ["search_vector"], schema="places", postgresql_using="gin")
    op.create_index("ix_places_coordinates", "places", ["latitude", "longitude"], schema="places")
    op.create_table("visits", sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("place_id", UUID, sa.ForeignKey("places.places.id", ondelete="CASCADE"), nullable=False), sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("notes", sa.Text), sa.Column("person_id", UUID, sa.ForeignKey("people.persons.id")), schema="places")

    op.create_table("events", sa.Column("id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("place_id", UUID, sa.ForeignKey("places.places.id", ondelete="SET NULL")), sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))", persisted=True)), schema="events")
    op.create_index("ix_events_events_search", "events", ["search_vector"], schema="events", postgresql_using="gin")
    op.create_index("ix_events_timeline", "events", ["starts_at"], schema="events")
    op.create_table("participants", sa.Column("event_id", UUID, sa.ForeignKey("events.events.id", ondelete="CASCADE"), primary_key=True), sa.Column("person_id", UUID, sa.ForeignKey("people.persons.id", ondelete="CASCADE"), primary_key=True), sa.Column("role", sa.String(100)), sa.Column("response", sa.String(50)), schema="events")

    op.create_table("items", sa.Column("id", UUID, sa.ForeignKey("core.entities.id", ondelete="CASCADE"), primary_key=True), sa.Column("entity_type_id", sa.Integer, sa.ForeignKey("meta.entity_types.id"), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text), sa.Column("notes", sa.Text), sa.Column("properties", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("search_vector", postgresql.TSVECTOR, sa.Computed("to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(notes,''))", persisted=True)), schema="knowledge")
    op.create_index("ix_knowledge_items_search", "items", ["search_vector"], schema="knowledge", postgresql_using="gin")

    op.execute("CREATE TABLE buildings.buildings (id uuid PRIMARY KEY REFERENCES core.entities(id) ON DELETE CASCADE, name varchar(255) NOT NULL, address text)")


def downgrade():
    for schema in ("buildings", "knowledge", "events", "places", "people", "shared", "meta"):
        op.execute(sa.text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
