"""
Point d'entrée de l'API Ansibase
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from .config import settings
from .routers import auth, audit, groups, hosts, inventory, users, variables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialisation et nettoyage de l'application"""
    # Démarrage : rien pour l'instant, les migrations Alembic gèrent le schéma
    yield
    # Arrêt
    from .database import engine

    engine.dispose()


app = FastAPI(
    title=settings.ANSIBASE_API_TITLE,
    description=(
        "API REST pour la gestion d'inventaire Ansible dynamique avec PostgreSQL. "
        "Gère les hôtes, groupes, variables et l'export d'inventaire au format Ansible."
    ),
    version=settings.ANSIBASE_API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(variables.router)
app.include_router(groups.router)
app.include_router(hosts.router)
app.include_router(inventory.router)
app.include_router(audit.router)


@app.get("/", tags=["health"])
def root():
    """Point de vérification de l'état de l'API"""
    return {
        "name": settings.ANSIBASE_API_TITLE,
        "version": settings.ANSIBASE_API_VERSION,
        "status": "ok",
    }
