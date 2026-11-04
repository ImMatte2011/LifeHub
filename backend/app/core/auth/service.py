"""
Auth service — autenticazione e sessioni server-side.

Le sessioni sono token opachi (secrets.token_urlsafe) salvati in core.sessions.
Non si usa JWT: il token viene verificato contro il DB ad ogni richiesta.
"""
import secrets
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import AuditLog, Session, Setting, User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

async def get_setting(db: AsyncSession, key: str) -> dict | None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def is_multi_user_enabled(db: AsyncSession) -> bool:
    value = await get_setting(db, "multi_user_enabled")
    if value is None:
        return False
    return bool(value.get("enabled", False))


# ---------------------------------------------------------------------------
# Autenticazione
# ---------------------------------------------------------------------------

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ---------------------------------------------------------------------------
# Sessioni
# ---------------------------------------------------------------------------

async def create_session(
    db: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    token = secrets.token_urlsafe(32)
    expires_at = _now() + timedelta(hours=settings.session_expire_hours)

    session = Session(
        user_id=user.id,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        last_seen_at=_now(),
    )
    db.add(session)
    await db.flush()
    return session


async def get_valid_session(db: AsyncSession, token: str) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.token == token,
            Session.expires_at > _now(),
        )
    )
    return result.scalar_one_or_none()


async def touch_session(db: AsyncSession, session: Session) -> None:
    """Aggiorna last_seen_at senza rinnovare la scadenza."""
    session.last_seen_at = _now()
    db.add(session)


async def delete_session(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

async def write_audit(
    db: AsyncSession,
    action: str,
    user_id: object = None,
    resource_type: str | None = None,
    resource_id: object = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
