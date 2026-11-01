from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routers import health

DESCRIPTION = """
Inventory and point-of-sale API for small shops in Qatar and the Gulf.
Prices are in Qatari riyals (QAR).
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Dukkan API", version=__version__, description=DESCRIPTION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
