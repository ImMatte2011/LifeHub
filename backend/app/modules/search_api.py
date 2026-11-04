import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.models import RolePermission, User
from app.database import get_db
from app.domain.models import EntityTag, Link, LinkType

router = APIRouter(tags=["search"])


@router.get("/search")
async def search_all(
    request: Request,
    q: str,
    module: str | None = None,
    tag_id: uuid.UUID | None = None,
    link_type: str | None = None,
    entity_type: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    if len(q.strip()) < 2:
        return []
    registry = request.app.state.module_registry
    if module:
        if module not in registry.modules or not registry.modules[module].enabled:
            raise HTTPException(status_code=404, detail="Module is not active")
        if not await _can_search(db, user, module):
            raise HTTPException(status_code=403, detail=f"Missing permission: {module}.read")
        providers = [registry.modules[module]]
    else:
        providers = [item for item in registry.modules.values() if item.enabled and await _can_search(db, user, item.name)]

    fuzzy = request.app.state.extension_manager.is_available("pg_trgm")
    limit = min(max(limit, 1), 100)
    results = []
    for provider in providers:
        results.extend(await provider.search(db, q.strip(), limit, fuzzy=fuzzy))
    if entity_type:
        results = [item for item in results if item.get("module") == "knowledge" and item.get("entity_type") == entity_type]

    ids = [uuid.UUID(item["id"]) for item in results]
    if ids and tag_id:
        tagged = set((await db.scalars(select(EntityTag.entity_id).where(
            EntityTag.tag_id == tag_id, EntityTag.entity_id.in_(ids)
        ))).all())
        results = [item for item in results if uuid.UUID(item["id"]) in tagged]
        ids = [uuid.UUID(item["id"]) for item in results]
    if ids and link_type:
        linked = (await db.execute(
            select(Link.source_id, Link.target_id)
            .join(LinkType, LinkType.id == Link.link_type_id)
            .where(LinkType.name == link_type, (Link.source_id.in_(ids)) | (Link.target_id.in_(ids)))
        )).all()
        linked_ids = {entity_id for pair in linked for entity_id in pair}
        results = [item for item in results if uuid.UUID(item["id"]) in linked_ids]

    results.sort(key=lambda item: item.get("rank", 0), reverse=True)
    return results[:limit]


async def _can_search(db: AsyncSession, user: User, module: str) -> bool:
    if user.is_system_admin:
        return True
    if user.role_id is None:
        return False
    return await db.scalar(select(RolePermission.id).where(
        RolePermission.role_id == user.role_id,
        RolePermission.resource.in_([module, "*"]),
        RolePermission.action.in_(["read", "*"]),
    )) is not None
