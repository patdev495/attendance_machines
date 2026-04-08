import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from .config import config
from .routers import attendance, machines, export

from .database import init_db

def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Time Attendance System")

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Modular Routers
    app.include_router(attendance.router)
    app.include_router(machines.router)
    app.include_router(export.router)

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
    
    uvicorn.run(app, host=args.host, port=args.port)
