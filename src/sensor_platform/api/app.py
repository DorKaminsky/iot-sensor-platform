"""FastAPI application factory."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from sensor_platform.api.routes import health, metrics


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sensor Platform API",
        version="1.0.0",
        description="Industrial IoT sensor data ingestion and metrics service",
    )
    app.include_router(health.router)
    app.include_router(metrics.router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("sensor_platform.api.app:app", host="0.0.0.0", port=8000, reload=True)
