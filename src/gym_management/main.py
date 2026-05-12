"""Application factory + demo seed for first run."""

from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from gym_management.api.routes import equipment, membership, reports, subscriptions
from gym_management.infrastructure.database import create_schema, init_engine
from gym_management.infrastructure.seed import seed_if_empty
from gym_management.web import ui_routes

_WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app() -> FastAPI:
    init_engine()
    create_schema()
    seed_if_empty()

    app = FastAPI(
        title="Gym management information system",
        version="0.1.0",
        description="BLM3722 course project API — gym management domain (Topic 3).",
    )
    app.mount(
        "/ui/static",
        StaticFiles(directory=str(_WEB_DIR / "static")),
        name="ui_static",
    )
    app.include_router(ui_routes.router)
    app.include_router(membership.router)
    app.include_router(subscriptions.router)
    app.include_router(equipment.router)
    app.include_router(reports.router)
    return app


app = create_app()
