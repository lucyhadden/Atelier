"""Atelier API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .routers import boards, items, meta, pinterest_routes, spaces

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logging.getLogger(__name__).info(
        "Atelier ready - model=%s region=%s web_search=%s",
        settings.atelier_model,
        settings.atelier_region,
        settings.atelier_web_search,
    )
    yield


app = FastAPI(
    title="Atelier",
    description="Turn saved images and floor plans into a design brief and a shopping list.",
    version="0.1.0",
    lifespan=lifespan,
)

# The frontend dev server runs on another port; everything stays on localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router, prefix="/api")
app.include_router(boards.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(spaces.router, prefix="/api")
app.include_router(pinterest_routes.router, prefix="/api")

# Pin images are served straight off disk.
app.mount("/images", StaticFiles(directory=settings.image_dir), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
