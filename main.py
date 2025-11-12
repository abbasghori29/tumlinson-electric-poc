"""
FastAPI application entry point
Minimal main.py - all business logic is in routers and services
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.config import settings
from app.routers import auth, files, folders, structure, tracking, websocket
from app.services.storage_service import get_storage_service
from app.services.folder_service import FolderService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(structure.router)
app.include_router(tracking.router)
app.include_router(websocket.router)


@app.on_event("startup")
async def startup_event():
    """Initialize app on startup"""
    logger.info(f"Starting {settings.APP_TITLE} v{settings.APP_VERSION}")
    logger.info(f"Storage: {'S3' if settings.use_s3 else 'Local'}")
    
    # Ensure root folders exist
    try:
        storage = get_storage_service()
        folder_service = FolderService(storage)
        await folder_service.ensure_root_folders()
        logger.info("Root folders ensured")
    except Exception as e:
        logger.error(f"Failed to ensure root folders: {e}")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the login page"""
    html_path = Path("static/login.html")
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return "<h1>Login page not found. Please create static/login.html</h1>"


@app.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard():
    """Serve the dashboard (protected frontend)"""
    html_path = Path("static/dashboard.html")
    if html_path.exists():
        return html_path.read_text(encoding='utf-8')
    return "<h1>Dashboard not found. Please create static/dashboard.html</h1>"


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    storage_type = "s3" if settings.use_s3 else "local"
    return {
        "storage_type": storage_type,
        "bucket": settings.AWS_S3_BUCKET if settings.use_s3 else None,
        "region": settings.AWS_REGION if settings.use_s3 else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
