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
from app.domain.models import EntityType, LinkType, PropertyDefinition
from app.instance.loader import InstanceConfig

logger = logging.getLogger(__name__)

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


async def _sync_modules(db: AsyncSession, registry, extension_manager) -> None:
    """
    Sincronizza core.modules con la configurazione dell'istanza.
    Crea il record se mancante, aggiorna is_enabled se già presente.
    """
    for module_spec in registry.modules.values():
        name = module_spec.name
        result = await db.execute(select(Module).where(Module.name == name))
        module = result.scalar_one_or_none()
        is_enabled = module_spec.enabled and all(extension_manager.is_available(ext) for ext in module_spec.requires)

        if not module:
            db.add(
                Module(
                    name=name,
                    display_name=module_spec.display_name,
                    description=module_spec.description,
                    is_enabled=is_enabled,
                    is_core=False,
                    version="0.1.0",
                )
            )
        else:
            module.is_enabled = is_enabled
            module.display_name = module_spec.display_name
            module.description = module_spec.description


async def _seed_metadata(db: AsyncSession) -> None:
    definitions = {
        "book": ("Book", [("author", "Author", "string", True, None), ("isbn", "ISBN", "string", False, None), ("status", "Reading status", "enum", False, ["to_read", "reading", "read"])]),
        "ammo": ("Ammunition", [("caliber", "Caliber", "string", True, None), ("quantity", "Quantity", "integer", True, None), ("manufacturer", "Manufacturer", "string", False, None)]),
        "software": ("Software", [("version", "Version", "string", False, None), ("vendor", "Vendor", "string", False, None), ("license", "License", "string", False, None)]),
        "recipe": ("Recipe", [("servings", "Servings", "integer", False, None), ("prep_minutes", "Preparation minutes", "integer", False, None), ("ingredients", "Ingredients", "text", False, None)]),
    }
    for name, (label, properties) in definitions.items():
        entity_type = (await db.execute(select(EntityType).where(EntityType.name == name))).scalar_one_or_none()
        if entity_type is None:
            entity_type = EntityType(name=name, module="knowledge", label=label)
            db.add(entity_type); await db.flush()
        for order, (prop_name, prop_label, data_type, required, choices) in enumerate(properties):
            exists = (await db.execute(select(PropertyDefinition).where(PropertyDefinition.entity_type_id == entity_type.id, PropertyDefinition.name == prop_name))).scalar_one_or_none()
            if exists is None:
                db.add(PropertyDefinition(entity_type_id=entity_type.id, name=prop_name, label=prop_label, data_type=data_type, required=required, sort_order=order, enum_values=choices))
    for name, label, inverse in [("related", "Related to", "Related from"), ("parent", "Parent of", "Child of"), ("works_with", "Works with", "Works with")]:
        if not (await db.execute(select(LinkType).where(LinkType.name == name))).scalar_one_or_none():
            db.add(LinkType(name=name, label=label, inverse_label=inverse))

    await db.flush()


async def run_startup(db: AsyncSession, config: InstanceConfig, registry, extension_manager) -> None:
    logger.info("Running startup tasks...")
    role = await _ensure_admin_role(db)
    await _ensure_admin_user(db, role)
    await _sync_settings(db, config)
    await _sync_modules(db, registry, extension_manager)
    await _seed_metadata(db)
    await db.commit()
    logger.info("Startup complete")
