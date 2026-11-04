from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _search(db: AsyncSession, query: str, limit: int, sql: str, fuzzy: bool = False) -> list[dict]:
    result = await db.execute(text(sql), {"query": query, "limit": limit})
    return [dict(row) for row in result.mappings().all()]


async def search_people(db, query, limit, fuzzy=False):
    rank = "GREATEST(ts_rank(p.search_vector, websearch_to_tsquery('simple', :query)), similarity(p.display_name, :query))" if fuzzy else "ts_rank(p.search_vector, websearch_to_tsquery('simple', :query))"
    fuzzy_clause = "OR similarity(p.display_name, :query) > 0.18" if fuzzy else ""
    return await _search(db, query, limit, f"""SELECT p.id::text AS id, 'people' AS module, NULL::text AS entity_type, p.display_name AS title,
      coalesce(p.notes, '') AS summary, {rank} AS rank
      FROM people.persons p WHERE p.search_vector @@ websearch_to_tsquery('simple', :query)
      OR p.display_name ILIKE '%' || :query || '%' {fuzzy_clause} ORDER BY rank DESC, p.display_name LIMIT :limit""", fuzzy)


async def search_places(db, query, limit, fuzzy=False):
    rank = "GREATEST(ts_rank(p.search_vector, websearch_to_tsquery('simple', :query)), similarity(p.name, :query))" if fuzzy else "ts_rank(p.search_vector, websearch_to_tsquery('simple', :query))"
    fuzzy_clause = "OR similarity(p.name, :query) > 0.18" if fuzzy else ""
    return await _search(db, query, limit, f"""SELECT p.id::text AS id, 'places' AS module, NULL::text AS entity_type, p.name AS title,
      coalesce(p.description, '') AS summary, {rank} AS rank
      FROM places.places p WHERE p.search_vector @@ websearch_to_tsquery('simple', :query)
      OR p.name ILIKE '%' || :query || '%' {fuzzy_clause} ORDER BY rank DESC, p.name LIMIT :limit""", fuzzy)


async def search_events(db, query, limit, fuzzy=False):
    rank = "GREATEST(ts_rank(e.search_vector, websearch_to_tsquery('simple', :query)), similarity(e.title, :query))" if fuzzy else "ts_rank(e.search_vector, websearch_to_tsquery('simple', :query))"
    fuzzy_clause = "OR similarity(e.title, :query) > 0.18" if fuzzy else ""
    return await _search(db, query, limit, f"""SELECT e.id::text AS id, 'events' AS module, NULL::text AS entity_type, e.title,
      coalesce(e.description, '') AS summary, {rank} AS rank
      FROM events.events e WHERE e.search_vector @@ websearch_to_tsquery('simple', :query)
      OR e.title ILIKE '%' || :query || '%' {fuzzy_clause} ORDER BY rank DESC, e.starts_at DESC LIMIT :limit""", fuzzy)


async def search_knowledge(db, query, limit, fuzzy=False):
    rank = "GREATEST(ts_rank(k.search_vector, websearch_to_tsquery('simple', :query)), similarity(k.title, :query))" if fuzzy else "ts_rank(k.search_vector, websearch_to_tsquery('simple', :query))"
    fuzzy_clause = "OR similarity(k.title, :query) > 0.18" if fuzzy else ""
    return await _search(db, query, limit, f"""SELECT k.id::text AS id, 'knowledge' AS module, et.name AS entity_type, k.title,
      coalesce(k.description, '') AS summary, {rank} AS rank
      FROM knowledge.items k JOIN meta.entity_types et ON et.id = k.entity_type_id WHERE k.search_vector @@ websearch_to_tsquery('simple', :query)
      OR k.title ILIKE '%' || :query || '%' {fuzzy_clause} ORDER BY rank DESC, k.title LIMIT :limit""", fuzzy)
