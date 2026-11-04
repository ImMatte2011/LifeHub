import uuid
from datetime import date
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, File as UploadFileField, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.models import Entity, RolePermission, User
from app.database import get_db
from app.domain.models import Building, Contact, EntityFile, File as StoredFile, EntityTag, Event, KnowledgeItem, Link, LinkType, Person, Place, PropertyDefinition, EntityType, Relationship, Tag, Visit, Participant
from app.config import settings

async def enforce_module_permission(request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    parts = request.url.path.strip("/").split("/")
    resource = parts[1] if len(parts) > 1 and parts[0] == "api" else "shared"
    if resource in {"entities", "tags", "links"}: resource = "shared"
    if resource not in {"people", "places", "events", "knowledge", "buildings", "shared"} or user.is_system_admin:
        return
    action = {"GET": "read", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}.get(request.method, "read")
    permission = await db.scalar(select(RolePermission.id).where(
        RolePermission.role_id == user.role_id,
        RolePermission.resource.in_([resource, "*"]),
        RolePermission.action.in_([action, "*"]),
    )) if user.role_id else None
    if permission is None:
        raise HTTPException(403, f"Missing permission: {resource}.{action}")


router = APIRouter(tags=["modules"], dependencies=[Depends(enforce_module_permission)])


class PersonIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    first_name: str | None = None
    last_name: str | None = None
    birthday: datetime | None = None
    notes: str | None = None


class ContactIn(BaseModel):
    kind: str
    value: str
    label: str | None = None
    is_primary: bool = False


class RelationshipIn(BaseModel):
    related_person_id: uuid.UUID
    relationship_type: str
    notes: str | None = None


class PlaceIn(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_a_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        return self


class EventIn(BaseModel):
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    place_id: uuid.UUID | None = None


class KnowledgeIn(BaseModel):
    entity_type: str
    title: str
    description: str | None = None
    notes: str | None = None
    properties: dict = Field(default_factory=dict)


class TagIn(BaseModel):
    name: str
    color: str | None = None


class LinkIn(BaseModel):
    source_id: uuid.UUID
    target_id: uuid.UUID
    type: str = "related"
    notes: str | None = None


class BuildingIn(BaseModel):
    name: str
    address: str | None = None


async def enabled(request: Request, name: str, extension: str | None = None):
    registry = request.app.state.module_registry
    module = registry.modules.get(name)
    if not module or not module.enabled:
        raise HTTPException(404, "Module is disabled")
    if extension and not request.app.state.extension_manager.is_available(extension):
        raise HTTPException(503, f"Required capability '{extension}' is unavailable")


async def add_entity(db, user, kind):
    entity = Entity(id=uuid.uuid4(), entity_type=kind, created_by=user.id)
    db.add(entity)
    await db.flush()
    return entity.id


@router.get("/people")
async def list_people(request: Request, q: str | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    query = select(Person).join(Entity, Entity.id == Person.id).where(Entity.deleted_at.is_(None)).order_by(Person.display_name)
    if q:
        query = query.where(Person.display_name.ilike(f"%{q}%"))
    return [person_data(p) for p in (await db.execute(query)).scalars()]


def person_data(p):
    return {"id": str(p.id), "display_name": p.display_name, "first_name": p.first_name, "last_name": p.last_name,
            "birthday": p.birthday, "notes": p.notes}


@router.post("/people", status_code=201)
async def create_person(body: PersonIn, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await enabled(request, "people")
    entity_id = await add_entity(db, user, "person")
    person = Person(id=entity_id, **body.model_dump())
    db.add(person); await db.flush()
    return person_data(person)


@router.get("/people/{person_id}")
async def get_person(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    person = await db.get(Person, person_id)
    if not person: raise HTTPException(404, "Person not found")
    contacts = (await db.execute(select(Contact).where(Contact.person_id == person_id))).scalars().all()
    rels = (await db.execute(select(Relationship).where(Relationship.person_id == person_id))).scalars().all()
    return {**person_data(person), "contacts": [contact_data(c) for c in contacts], "relationships": [relationship_data(r) for r in rels], **(await shared_for(db, person_id))}


@router.put("/people/{person_id}")
async def update_person(person_id: uuid.UUID, body: PersonIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    person = await db.get(Person, person_id)
    if not person: raise HTTPException(404, "Person not found")
    for key, value in body.model_dump().items(): setattr(person, key, value)
    return person_data(person)


@router.delete("/people/{person_id}", status_code=204)
async def delete_person(person_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    entity = await db.get(Entity, person_id)
    if not entity: raise HTTPException(404, "Person not found")
    entity.deleted_at = datetime.now().astimezone()


def contact_data(c): return {"id": str(c.id), "kind": c.kind, "value": c.value, "label": c.label, "is_primary": c.is_primary}
def relationship_data(r): return {"id": str(r.id), "related_person_id": str(r.related_person_id), "relationship_type": r.relationship_type, "notes": r.notes}


@router.post("/people/{person_id}/contacts", status_code=201)
async def add_contact(person_id: uuid.UUID, body: ContactIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    if not await db.get(Person, person_id): raise HTTPException(404, "Person not found")
    item = Contact(person_id=person_id, **body.model_dump()); db.add(item); await db.flush(); return contact_data(item)


@router.post("/people/{person_id}/relationships", status_code=201)
async def add_relationship(person_id: uuid.UUID, body: RelationshipIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "people")
    if person_id == body.related_person_id: raise HTTPException(422, "A person cannot be related to themself")
    if not await db.get(Person, person_id) or not await db.get(Person, body.related_person_id): raise HTTPException(404, "Person not found")
    item = Relationship(person_id=person_id, **body.model_dump()); db.add(item); await db.flush(); return relationship_data(item)


@router.get("/places")
async def list_places(request: Request, q: str | None = None, lat: float | None = None, lon: float | None = None, radius_m: float | None = Query(default=None, gt=0), bbox: str | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "places")
    ext = request.app.state.extension_manager
    if any(x is not None for x in (lat, lon, radius_m, bbox)) and not ext.is_available("maps"):
        raise HTTPException(503, "Map capability is unavailable")
    if radius_m and (lat is None or lon is None): raise HTTPException(422, "lat and lon are required with radius_m")
    query = select(Place).join(Entity, Entity.id == Place.id).where(Entity.deleted_at.is_(None))
    if q: query = query.where(Place.name.ilike(f"%{q}%"))
    if bbox:
        try: west, south, east, north = map(float, bbox.split(","))
        except ValueError: raise HTTPException(422, "bbox must be west,south,east,north")
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90) or south > north:
            raise HTTPException(422, "bbox coordinates are out of range")
        if request.app.state.extension_manager.is_available("maps"):
            spatial_filter = text("places.places.geom && ST_SetSRID(ST_MakeEnvelope(:west, :south, :east, :north), 4326)::geography").bindparams(west=west, south=south, east=east, north=north)
            query = query.where(spatial_filter)
        else:
            query = query.where(Place.longitude.between(west, east), Place.latitude.between(south, north))
    places = list((await db.execute(query.order_by(Place.name))).scalars())
    output = [place_data(p) for p in places]
    if radius_m:
        result = await db.execute(text("""SELECT p.id::text AS id, p.name, p.description, p.address, p.latitude, p.longitude,
            ST_Distance(p.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance_m
            FROM places.places p JOIN core.entities e ON e.id = p.id
            WHERE e.deleted_at IS NULL AND p.geom IS NOT NULL
              AND ST_DWithin(p.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius)
            ORDER BY distance_m"""), {"lat": lat, "lon": lon, "radius": radius_m})
        return [dict(row) for row in result.mappings().all()]
    return output


def place_data(p): return {"id": str(p.id), "name": p.name, "description": p.description, "address": p.address, "latitude": p.latitude, "longitude": p.longitude}


@router.post("/places", status_code=201)
async def create_place(body: PlaceIn, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await enabled(request, "places")
    if body.latitude is not None and body.longitude is not None: await enabled(request, "places", "maps")
    entity_id = await add_entity(db, user, "place")
    place = Place(id=entity_id, **body.model_dump()); db.add(place); await db.flush()
    if body.latitude is not None and body.longitude is not None and request.app.state.extension_manager.is_available("maps"):
        await db.execute(text("UPDATE places.places SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography WHERE id = :id"), {"lon": body.longitude, "lat": body.latitude, "id": entity_id})
    return place_data(place)


@router.put("/places/{place_id}")
async def update_place(place_id: uuid.UUID, body: PlaceIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "places")
    place = await db.get(Place, place_id)
    if not place: raise HTTPException(404, "Place not found")
    if body.latitude is not None and body.longitude is not None: await enabled(request, "places", "maps")
    for key, value in body.model_dump().items(): setattr(place, key, value)
    await db.flush()
    if request.app.state.extension_manager.is_available("maps"):
        await db.execute(text("UPDATE places.places SET geom = CASE WHEN :lat IS NULL OR :lon IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography END WHERE id = :id"), {"lat": body.latitude, "lon": body.longitude, "id": place_id})
    return place_data(place)


@router.delete("/places/{place_id}", status_code=204)
async def delete_place(place_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "places")
    entity = await db.get(Entity, place_id)
    if not entity: raise HTTPException(404, "Place not found")
    entity.deleted_at = datetime.now().astimezone()


@router.get("/places/{place_id}")
async def get_place(place_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "places")
    place = await db.get(Place, place_id)
    if not place: raise HTTPException(404, "Place not found")
    visits = (await db.execute(select(Visit).where(Visit.place_id == place_id).order_by(Visit.visited_at.desc()))).scalars()
    return {**place_data(place), "visits": [{"id": str(v.id), "visited_at": v.visited_at, "notes": v.notes} for v in visits], **(await shared_for(db, place_id))}


@router.post("/places/{place_id}/visits", status_code=201)
async def add_visit(place_id: uuid.UUID, notes: str | None = None, request: Request = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "places")
    if not await db.get(Place, place_id): raise HTTPException(404, "Place not found")
    visit = Visit(place_id=place_id, notes=notes); db.add(visit); await db.flush(); return {"id": str(visit.id), "place_id": str(place_id), "visited_at": visit.visited_at, "notes": notes}


@router.get("/events")
async def list_events(request: Request, start: datetime | None = None, end: datetime | None = None, person_id: uuid.UUID | None = None, place_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "events")
    query = select(Event).join(Entity, Entity.id == Event.id).where(Entity.deleted_at.is_(None))
    if start: query = query.where(Event.starts_at >= start)
    if end: query = query.where(Event.starts_at < end)
    if place_id: query = query.where(Event.place_id == place_id)
    if person_id: query = query.join(Participant, Participant.event_id == Event.id).where(Participant.person_id == person_id)
    return [event_data(e) for e in (await db.execute(query.order_by(Event.starts_at))).scalars().unique()]


def event_data(e): return {"id": str(e.id), "title": e.title, "description": e.description, "starts_at": e.starts_at, "ends_at": e.ends_at, "place_id": str(e.place_id) if e.place_id else None}


@router.post("/events", status_code=201)
async def create_event(body: EventIn, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await enabled(request, "events")
    if body.ends_at and body.ends_at <= body.starts_at: raise HTTPException(422, "ends_at must be later than starts_at")
    entity_id = await add_entity(db, user, "event")
    event = Event(id=entity_id, **body.model_dump()); db.add(event); await db.flush(); return event_data(event)


@router.put("/events/{event_id}")
async def update_event(event_id: uuid.UUID, body: EventIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "events")
    if body.ends_at and body.ends_at <= body.starts_at: raise HTTPException(422, "ends_at must be later than starts_at")
    event = await db.get(Event, event_id)
    if not event: raise HTTPException(404, "Event not found")
    for key, value in body.model_dump().items(): setattr(event, key, value)
    return event_data(event)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "events")
    entity = await db.get(Entity, event_id)
    if not entity: raise HTTPException(404, "Event not found")
    entity.deleted_at = datetime.now().astimezone()


@router.post("/events/{event_id}/participants", status_code=201)
async def add_participant(event_id: uuid.UUID, person_id: uuid.UUID, role: str | None = None, request: Request = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "events")
    if not await db.get(Event, event_id) or not await db.get(Person, person_id): raise HTTPException(404, "Event or person not found")
    participant = Participant(event_id=event_id, person_id=person_id, role=role); db.add(participant); await db.flush(); return {"event_id": str(event_id), "person_id": str(person_id), "role": role}


def _validate_properties(definitions, values):
    known = {d.name: d for d in definitions}
    unknown = set(values) - set(known)
    if unknown: raise HTTPException(422, f"Unknown properties: {', '.join(sorted(unknown))}")
    errors = []
    for name, definition in known.items():
        value = values.get(name)
        if definition.required and value is None: errors.append(f"{name} is required"); continue
        if value is None: continue
        valid = {"string": isinstance(value, str), "text": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool), "number": isinstance(value, (int, float)) and not isinstance(value, bool), "boolean": isinstance(value, bool), "date": isinstance(value, str) and _valid_date(value), "enum": value in (definition.enum_values or [])}.get(definition.data_type, True)
        if not valid: errors.append(f"{name} must be {definition.data_type}")
    if errors: raise HTTPException(422, {"properties": errors})


def _valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


@router.get("/knowledge/types")
async def knowledge_types(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "knowledge")
    types = (await db.execute(select(EntityType).where(EntityType.module == "knowledge").order_by(EntityType.name))).scalars()
    return [{"name": t.name, "label": t.label, "properties": await property_data(db, t.id)} for t in types]


async def property_data(db, type_id):
    defs = (await db.execute(select(PropertyDefinition).where(PropertyDefinition.entity_type_id == type_id).order_by(PropertyDefinition.sort_order))).scalars()
    return [{"name": d.name, "label": d.label, "data_type": d.data_type, "required": d.required, "order": d.sort_order, "enum_values": d.enum_values, "group_id": d.group_id} for d in defs]


@router.get("/knowledge")
async def list_knowledge(request: Request, entity_type: str | None = None, q: str | None = None, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "knowledge")
    query = select(KnowledgeItem).join(Entity, Entity.id == KnowledgeItem.id).where(Entity.deleted_at.is_(None))
    if entity_type: query = query.join(EntityType, EntityType.id == KnowledgeItem.entity_type_id).where(EntityType.name == entity_type)
    if q: query = query.where(KnowledgeItem.title.ilike(f"%{q}%"))
    return [knowledge_data(k) for k in (await db.execute(query.order_by(KnowledgeItem.title))).scalars()]


def knowledge_data(k): return {"id": str(k.id), "entity_type_id": k.entity_type_id, "title": k.title, "description": k.description, "notes": k.notes, "properties": k.properties}


@router.post("/knowledge", status_code=201)
async def create_knowledge(body: KnowledgeIn, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await enabled(request, "knowledge")
    entity_type = (await db.execute(select(EntityType).where(EntityType.name == body.entity_type, EntityType.module == "knowledge"))).scalar_one_or_none()
    if not entity_type: raise HTTPException(422, "Unknown knowledge type")
    definitions = (await db.execute(select(PropertyDefinition).where(PropertyDefinition.entity_type_id == entity_type.id))).scalars().all()
    _validate_properties(definitions, body.properties)
    entity_id = await add_entity(db, user, f"knowledge:{entity_type.name}")
    item = KnowledgeItem(id=entity_id, entity_type_id=entity_type.id, title=body.title, description=body.description, notes=body.notes, properties=body.properties)
    db.add(item); await db.flush(); return knowledge_data(item)


@router.put("/knowledge/{item_id}")
async def update_knowledge(item_id: uuid.UUID, body: KnowledgeIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "knowledge")
    item = await db.get(KnowledgeItem, item_id)
    if not item: raise HTTPException(404, "Knowledge item not found")
    entity_type = (await db.execute(select(EntityType).where(EntityType.name == body.entity_type, EntityType.module == "knowledge"))).scalar_one_or_none()
    if not entity_type: raise HTTPException(422, "Unknown knowledge type")
    definitions = (await db.execute(select(PropertyDefinition).where(PropertyDefinition.entity_type_id == entity_type.id))).scalars().all(); _validate_properties(definitions, body.properties)
    item.entity_type_id = entity_type.id; item.title = body.title; item.description = body.description; item.notes = body.notes; item.properties = body.properties
    return knowledge_data(item)


@router.delete("/knowledge/{item_id}", status_code=204)
async def delete_knowledge(item_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "knowledge")
    entity = await db.get(Entity, item_id)
    if not entity: raise HTTPException(404, "Knowledge item not found")
    entity.deleted_at = datetime.now().astimezone()


@router.post("/tags", status_code=201)
async def create_tag(body: TagIn, request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    tag = (await db.execute(select(Tag).where(Tag.name == body.name))).scalar_one_or_none()
    if tag: return {"id": str(tag.id), "name": tag.name, "color": tag.color}
    tag = Tag(**body.model_dump()); db.add(tag); await db.flush(); return {"id": str(tag.id), "name": tag.name, "color": tag.color}


async def shared_for(db, entity_id):
    tags = (await db.execute(select(Tag).join(EntityTag, EntityTag.tag_id == Tag.id).where(EntityTag.entity_id == entity_id))).scalars()
    links = (await db.execute(select(Link, LinkType).join(LinkType, LinkType.id == Link.link_type_id).where((Link.source_id == entity_id) | (Link.target_id == entity_id)))).all()
    return {"tags": [{"id": str(t.id), "name": t.name, "color": t.color} for t in tags],
            "links": [{"id": str(l.id), "source_id": str(l.source_id), "target_id": str(l.target_id), "type": t.name, "label": t.label, "notes": l.notes} for l,t in links]}


@router.post("/entities/{entity_id}/tags/{tag_id}", status_code=204)
async def attach_tag(entity_id: uuid.UUID, tag_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if not await db.get(Entity, entity_id) or not await db.get(Tag, tag_id): raise HTTPException(404, "Entity or tag not found")
    if not await db.get(EntityTag, (entity_id, tag_id)): db.add(EntityTag(entity_id=entity_id, tag_id=tag_id))


@router.post("/links", status_code=201)
async def create_link(body: LinkIn, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    source, target = await db.get(Entity, body.source_id), await db.get(Entity, body.target_id)
    if not source or not target: raise HTTPException(404, "Entity not found")
    link_type = (await db.execute(select(LinkType).where(LinkType.name == body.type))).scalar_one_or_none()
    if not link_type: raise HTTPException(422, "Unknown link type")
    link = Link(source_id=body.source_id, target_id=body.target_id, link_type_id=link_type.id, notes=body.notes); db.add(link); await db.flush()
    return {"id": str(link.id), "source_id": str(link.source_id), "target_id": str(link.target_id), "type": body.type}


@router.post("/entities/{entity_id}/files", status_code=201)
async def upload_file(entity_id: uuid.UUID, upload: UploadFile = UploadFileField(...), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if not await db.get(Entity, entity_id): raise HTTPException(404, "Entity not found")
    root = Path(settings.file_storage_path).resolve()
    file_id = uuid.uuid4()
    relative = Path(str(file_id)[:2]) / str(file_id)
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > 25 * 1024 * 1024: raise HTTPException(413, "File exceeds 25 MB limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    safe_filename = Path((upload.filename or "upload").replace("\\", "/")).name
    stored = StoredFile(id=file_id, storage_key=relative.as_posix(), filename=safe_filename,
                        mime_type=upload.content_type, size_bytes=size)
    db.add(stored); db.add(EntityFile(entity_id=entity_id, file_id=file_id)); await db.flush()
    return {"id": str(file_id), "filename": stored.filename, "mime_type": stored.mime_type, "size_bytes": size}


@router.get("/entities/{entity_id}/files")
async def list_entity_files(entity_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if not await db.get(Entity, entity_id): raise HTTPException(404, "Entity not found")
    result = await db.execute(select(StoredFile).join(EntityFile, EntityFile.file_id == StoredFile.id).where(EntityFile.entity_id == entity_id).order_by(StoredFile.created_at.desc()))
    return [{"id": str(item.id), "filename": item.filename, "mime_type": item.mime_type, "size_bytes": item.size_bytes} for item in result.scalars()]


@router.get("/files/{file_id}")
async def download_file(file_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    item = await db.get(StoredFile, file_id)
    if not item: raise HTTPException(404, "File not found")
    root = Path(settings.file_storage_path).resolve()
    path = (root / item.storage_key).resolve()
    if root not in path.parents or not path.is_file(): raise HTTPException(404, "File not found")
    return FileResponse(path, media_type=item.mime_type or "application/octet-stream", filename=item.filename)


@router.get("/buildings")
async def list_buildings(request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    await enabled(request, "buildings")
    result = await db.execute(select(Building).join(Entity, Entity.id == Building.id).where(Entity.deleted_at.is_(None)).order_by(Building.name))
    return [{"id": str(item.id), "name": item.name, "address": item.address} for item in result.scalars()]


@router.post("/buildings", status_code=201)
async def create_building(body: BuildingIn, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await enabled(request, "buildings", "maps")
    entity_id = await add_entity(db, user, "building")
    item = Building(id=entity_id, **body.model_dump()); db.add(item); await db.flush()
    return {"id": str(item.id), "name": item.name, "address": item.address}
