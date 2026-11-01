import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import DEFAULT_SECRET_KEY, get_settings
from app.errors import register_error_handlers
from app.routers import (
    auth,
    branches,
    categories,
    health,
    inventory,
    products,
    settings,
    users,
)

DESCRIPTION = """
Inventory and point-of-sale API for small shops in Qatar and the Gulf.
Prices are in Qatari riyals (QAR).

Use **Authorize** with a username and password to try the protected endpoints.
"""

logger = logging.getLogger("dukkan")


def create_app() -> FastAPI:
    config = get_settings()
    if config.secret_key == DEFAULT_SECRET_KEY:
        logger.warning("DUKKAN_SECRET_KEY is not set; using the development default")

    app = FastAPI(title="Dukkan API", version=__version__, description=DESCRIPTION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    routers = (health, auth, users, branches, settings, categories, products, inventory)
    for module in routers:
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
