import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

import sys
from pathlib import Path

# Add current directory to sys.path to support both script and frozen execution
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from config import config
from database import init_db
from features.machines.live_monitor import live_monitor
import asyncio

# v2.0 Feature routers (registered when implemented, phases 2-5)
from features.logs.router import router as logs_router
from features.daily_summary.router import router as daily_summary_router
from features.employees.router import router as employees_router
from features.machines.router import router as machines_router
from features.shift_definitions.router import router as shift_router
from features.meal_tracking.router import router as meal_router
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    loop = asyncio.get_running_loop()
    live_monitor.set_loop(loop)
    live_monitor.start()
    yield
    # Shutdown
    live_monitor.stop()

def create_app() -> FastAPI:
    # Set up logging for the application
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Initializing Application...")
    
    init_db()
    app = FastAPI(title="Time Attendance System", lifespan=lifespan)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    # ── API Routers ──
    app.include_router(logs_router)       # v2.0
    app.include_router(daily_summary_router) # v2.0
    app.include_router(employees_router)    # v2.0
    app.include_router(machines_router)     # v2.0
    app.include_router(shift_router)        # v3.0
    app.include_router(meal_router)         # v8.1 Meal Kiosk



    # Serve Vue 3 SPA
    app.mount("/assets", StaticFiles(directory=str(config.STATIC_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index = config.STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return HTMLResponse("<h1>Frontend not built yet. Run: npm run build</h1>", status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Trình tự fallback: nếu không khớp bất kỳ API nào ở trên, nó sẽ trả về index.html
        index = config.STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        return HTMLResponse("<h1>Frontend not built yet. Run: npm run build</h1>", status_code=404)

    return app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Time Attendance System API.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to listen on")
    
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port, ws="websockets")
