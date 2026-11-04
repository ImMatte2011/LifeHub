import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.auth.router import router as auth_router
from app.core.models import Module, Role, RolePermission, Setting, User
from app.core.auth.service import hash_password, is_multi_user_enabled, write_audit
from app.database import get_db

router = APIRouter(prefix="/core")
router.include_router(auth_router)


class UserCreate(BaseModel):
    username: Annotated[str, StringConstraints(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")]
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)]
    email: str | None = None
    display_name: str | None = None
    role_id: int | None = None


class UserUpdate(BaseModel):
    email: str | None = None
    display_name: str | None = None
    role_id: int | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    permissions: list[dict[str, str]] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[dict[str, str]] | None = None


@router.get("/admin/users")
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    users = (await db.execute(select(User).order_by(User.username))).scalars()
    return [{"id": str(user.id), "username": user.username, "email": user.email,
             "display_name": user.display_name, "is_active": user.is_active,
             "is_system_admin": user.is_system_admin, "role_id": user.role_id} for user in users]


@router.post("/admin/users", status_code=201)
async def create_user(body: UserCreate, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    if not await is_multi_user_enabled(db):
        raise HTTPException(409, "Enable multi-user mode before creating additional accounts")
    if await db.scalar(select(User.id).where(User.username == body.username)):
        raise HTTPException(409, "Username already exists")
    if body.email and await db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(409, "Email already exists")
    if body.role_id is not None and not await db.get(Role, body.role_id):
        raise HTTPException(422, "Role not found")
    user = User(username=body.username, email=body.email, display_name=body.display_name,
                password_hash=hash_password(body.password), role_id=body.role_id, is_active=True)
    db.add(user); await db.flush()
    await write_audit(db, "admin.user.create", user_id=admin.id, resource_type="user", resource_id=user.id,
                      ip_address=request.client.host if request.client else None)
    return {"id": str(user.id), "username": user.username, "is_active": user.is_active, "role_id": user.role_id}


@router.patch("/admin/users/{user_id}")
async def update_user(user_id: uuid.UUID, body: UserUpdate, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    user = await db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    if body.is_active is False and user.is_system_admin and user.id == admin.id:
        raise HTTPException(409, "You cannot disable your own administrator account")
    changes = body.model_dump(exclude_unset=True)
    password = changes.pop("password", None)
    for key, value in changes.items(): setattr(user, key, value)
    if password:
        user.password_hash = hash_password(password)
    if not user.is_active:
        from app.core.models import Session
        sessions = (await db.execute(select(Session).where(Session.user_id == user.id))).scalars().all()
        for session in sessions: await db.delete(session)
    await write_audit(db, "admin.user.update", user_id=admin.id, resource_type="user", resource_id=user.id,
                      details={"is_active": user.is_active, "role_id": user.role_id},
                      ip_address=request.client.host if request.client else None)
    return {"id": str(user.id), "username": user.username, "is_active": user.is_active, "role_id": user.role_id}


@router.get("/admin/roles")
async def list_roles(db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)):
    roles = (await db.execute(select(Role).order_by(Role.name))).scalars().all()
    permissions = (await db.execute(select(RolePermission))).scalars().all()
    by_role: dict[int, list[dict[str, str]]] = {}
    for permission in permissions:
        by_role.setdefault(permission.role_id, []).append({"resource": permission.resource, "action": permission.action})
    return [{"id": role.id, "name": role.name, "description": role.description,
             "permissions": by_role.get(role.id, [])}
            for role in roles]


@router.post("/admin/roles", status_code=201)
async def create_role(body: RoleCreate, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    if await db.scalar(select(Role.id).where(Role.name == body.name)):
        raise HTTPException(409, "Role already exists")
    role = Role(name=body.name, description=body.description)
    db.add(role); await db.flush()
    for permission in body.permissions:
        db.add(RolePermission(role_id=role.id, resource=permission["resource"], action=permission["action"]))
    await write_audit(db, "admin.role.create", user_id=admin.id, resource_type="role",
                      details={"name": role.name}, ip_address=request.client.host if request.client else None)
    return {"id": role.id, "name": role.name}


@router.patch("/admin/roles/{role_id}")
async def update_role(role_id: int, body: RoleUpdate, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    role = await db.get(Role, role_id)
    if not role: raise HTTPException(404, "Role not found")
    changes = body.model_dump(exclude_unset=True)
    permissions = changes.pop("permissions", None)
    for key, value in changes.items(): setattr(role, key, value)
    if permissions is not None:
        current = (await db.execute(select(RolePermission).where(RolePermission.role_id == role_id))).scalars().all()
        for permission in current: await db.delete(permission)
        for permission in permissions:
            db.add(RolePermission(role_id=role.id, resource=permission["resource"], action=permission["action"]))
    await write_audit(db, "admin.role.update", user_id=admin.id, resource_type="role",
                      details={"name": role.name}, ip_address=request.client.host if request.client else None)
    return {"id": role.id, "name": role.name}


@router.get("/extensions")
async def get_extensions(request: Request) -> list[dict]:
    return request.app.state.extension_manager.status()


@router.get("/settings")
async def list_settings(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return {"items": [{"key": s.key, "value": s.value, "description": s.description} for s in (await db.execute(select(Setting).order_by(Setting.key))).scalars()]}


@router.put("/settings/{key}")
async def update_setting(key: str, body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_system_admin:
        from fastapi import HTTPException
        raise HTTPException(403, "Admin privileges required")
    setting = await db.get(Setting, key)
    if setting is None:
        raise HTTPException(404, "Setting not found")
    setting.value = body
    return {"key": key, "value": setting.value}


@router.get("/modules/active")
async def get_active_modules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    """
    Lista dei moduli attualmente abilitati.
    Usato dal frontend per costruire menu e route dinamicamente.
    """
    result = await db.execute(
        select(Module).where(Module.is_enabled == True).order_by(Module.name)  # noqa: E712
    )
    modules = result.scalars().all()
    statuses = {item["name"]: item for item in request.app.state.module_registry.status(request.app.state.extension_manager)}
    return [
        {
            "name": m.name,
            "display_name": m.display_name,
            "description": m.description,
            "version": m.version,
            "is_core": m.is_core,
        }
        for m in modules
        if statuses.get(m.name, {}).get("available", False)
    ]


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
