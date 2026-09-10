import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings, BASE_DIR, DATA_DIR, PHOTOS_DIR
from app.db.database import init_db
from app.api.routes_scan import router as scan_router
from app.api.routes_people import router as people_router
from app.api.routes_history import router as history_router
from app.api.routes_settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    print("==================================================")
    print(f"  FelisEye v{settings.APP_VERSION} - Private Face Recognition")
    print(f"  Engine: 100% Offline Deep Biometrics")
    print(f"  Web UI: http://{settings.HOST}:{settings.PORT}")
    print("==================================================")
    yield
    # Shutdown
    print("FelisEye shutting down safely.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade, offline-first private AI face recognition system.",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(scan_router)
app.include_router(people_router)
app.include_router(history_router)
app.include_router(settings_router)

# Mount Photos Storage for UI avatars
if not PHOTOS_DIR.exists():
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/data/photos", StaticFiles(directory=str(PHOTOS_DIR)), name="photos")

# Mount Static Files (HTML, CSS, JS, Assets)
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "FelisEye API is running. UI index.html not yet deployed."}
