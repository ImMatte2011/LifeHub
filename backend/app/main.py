import logging
import json
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.router import router as core_router
from app.database import AsyncSessionLocal, engine
from app.extensions.manager import ExtensionManager
from app.instance.loader import load_instance_config
from app.modules.registry import build_module_registry
from app.modules.api import router as modules_router
from app.modules.search_api import router as search_router
from app.startup import run_startup

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"time": self.formatTime(record), "level": record.levelname,
                           "logger": record.name, "message": record.getMessage()}, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config = load_instance_config(settings.instance_config_path)
    app.state.instance_config = config
    app.state.extension_manager = ExtensionManager(config.extensions)
    app.state.module_registry = build_module_registry()
    async with engine.begin() as connection:
        await app.state.extension_manager.initialize(connection)
    async with AsyncSessionLocal() as db:
        await run_startup(db, config, app.state.module_registry, app.state.extension_manager)
    logger.info("Starting LifeHub — %s", config.name)
    yield
    await engine.dispose()


app = FastAPI(title="LifeHub API", version="0.2.0", docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(core_router, prefix="/api")
app.include_router(modules_router, prefix="/api")
app.include_router(search_router, prefix="/api")


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT 1"))
    memory_mb = None
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                memory_mb = round(int(line.split()[1]) / 1024, 1)
                break
    except (OSError, ValueError):
        pass
    disk_free_gb = None
    try:
        disk_free_gb = round(shutil.disk_usage(settings.file_storage_path).free / (1024 ** 3), 2)
    except OSError:
        pass
    return {"status": "ok", "version": app.version, "database": "ok",
            "resources": {"process_memory_mb": memory_mb, "storage_free_gb": disk_free_gb}}
