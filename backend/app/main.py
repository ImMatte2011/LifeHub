import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.router import router as core_router
from app.database import AsyncSessionLocal
from app.instance.loader import load_instance_config
from app.startup import run_startup

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    instance_config = load_instance_config(settings.instance_config_path)
    logger.info(f"Starting LifeHub — {instance_config.name}")

    async with AsyncSessionLocal() as db:
        await run_startup(db, instance_config)

    yield

    logger.info("LifeHub shutting down")


app = FastAPI(
    title="LifeHub API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione: restringere all'origin del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router, prefix="/api")


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
