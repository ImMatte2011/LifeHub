"""
Task di avvio eseguiti una volta dopo le migrazioni.

- Crea ruolo admin se non esiste
- Crea utente admin se non esiste
- Sincronizza settings base dal config
- Sincronizza stato moduli da instance.yaml → core.modules
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth.service import hash_password
from app.core.models import Module, Role, Setting, User
from app.instance.loader import InstanceConfig

logger = logging.getLogger(__name__)

# Moduli conosciuti: name → (display_name, description)
_KNOWN_MODULES: dict[str, tuple[str, str]] = {
    "people": ("People", "Manage contacts and relationships"),
    "places": ("Places", "Manage locations and visits"),
    "events": ("Events", "Manage events and timeline"),
    "knowledge": ("Knowledge", "Manage knowledge items"),
}


async def _ensure_admin_role(db: AsyncSession) -> Role:
    result = await db.execute(select(Role).where(Role.name == "admin"))
    role = result.scalar_one_or_none()
    if not role:
        role = Role(name="admin", description="System administrator", is_system=True)
        db.add(role)
        await db.flush()
        logger.info("Created role: admin")
    return role


async def _ensure_admin_user(db: AsyncSession, role: Role) -> None:
    result = await db.execute(
        select(User).where(User.username == settings.admin_username)
    )
    if result.scalar_one_or_none():
        return

    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        display_name="Administrator",
        role_id=role.id,
        is_active=True,
        is_system_admin=True,
    )
    db.add(user)
    await db.flush()
    logger.info(f"Created admin user: {settings.admin_username}")


async def _sync_settings(db: AsyncSession, config: InstanceConfig) -> None:
    """
    Inserisce i settings di default se non esistenti.
    Non sovrascrive valori già presenti (modifiche manuali preservate).
    """
    defaults: list[tuple[str, dict, str]] = [
        ("instance_name", {"value": config.name}, "Instance display name"),
        ("instance_description", {"value": config.description}, "Instance description"),
        (
            "multi_user_enabled",
            {"enabled": False},
            "Whether multiple users can log in. Set to true to enable multi-user mode.",
        ),
    ]
    for key, value, description in defaults:
        result = await db.execute(select(Setting).where(Setting.key == key))
        if not result.scalar_one_or_none():
            db.add(Setting(key=key, value=value, description=description))
    await db.flush()


async def _sync_modules(db: AsyncSession, config: InstanceConfig) -> None:
    """
    Sincronizza core.modules con la configurazione dell'istanza.
    Crea il record se mancante, aggiorna is_enabled se già presente.
    """
    for name, (display_name, description) in _KNOWN_MODULES.items():
        result = await db.execute(select(Module).where(Module.name == name))
        module = result.scalar_one_or_none()
        is_enabled = config.modules.get(name, False)

        if not module:
            db.add(
                Module(
                    name=name,
                    display_name=display_name,
                    description=description,
                    is_enabled=is_enabled,
                    is_core=False,
                    version="0.1.0",
                )
            )
        else:
            module.is_enabled = is_enabled

    await db.flush()


async def run_startup(db: AsyncSession, config: InstanceConfig) -> None:
    logger.info("Running startup tasks...")
    role = await _ensure_admin_role(db)
    await _ensure_admin_user(db, role)
    await _sync_settings(db, config)
    await _sync_modules(db, config)
    await db.commit()
    logger.info("Startup complete")
