"""FastAPI process: simulation loop + JSON API (/api/*). Run from backend/: python main.py [--dev]"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api import (
    routes_admin,
    routes_auth,
    routes_config,
    routes_houses,
    routes_me,
    routes_sim,
    routes_stats,
    routes_trading,
    routes_vpp,
    routes_wallet,
)
from app.db.database import close_db, get_session_context, init_db
from app.db.init_data import seed_houses
from app.services.simulation_loop import sim
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("vpp")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.require_secret()
    await init_db()
    async with get_session_context() as session:
        await seed_houses(session)
    await sim.load()
    if settings.sim_autostart:
        await sim.start()
        logger.info("Simulation loop started (%s s per %.0f-minute step)", sim.config.tick_seconds, sim.dt_h * 60)
    yield
    await sim.stop()
    await close_db()


app = FastAPI(title="VPP Simulator API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,   # auth is a bearer header, cookies are not used
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (routes_auth.router, routes_me.router, routes_stats.router, routes_houses.router, routes_sim.router,
               routes_vpp.router, routes_trading.router, routes_wallet.router, routes_admin.router,
               routes_config.router):
    app.include_router(router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc: RequestValidationError):
    """Same 422 as FastAPI's default, minus the echoed input (NaN/inf cannot be serialised)."""
    errors = [{k: v for k, v in e.items() if k in ("type", "loc", "msg")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/", include_in_schema=False)
def root():
    """The operator panel is served by the web container under /admin; the API root only points to the docs."""
    return RedirectResponse("/docs")


@app.get("/health")
async def health():
    status = sim.status()
    ok = status["loaded"] and status["last_error"] is None
    return {"status": "ok" if ok else "degraded", "simulation": status}


if __name__ == "__main__":
    import sys

    import uvicorn

    dev = "--dev" in sys.argv
    uvicorn.run("main:app" if dev else app, host=settings.host, port=settings.port, reload=dev)
