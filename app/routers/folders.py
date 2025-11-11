"""Folder management routes"""
from fastapi import APIRouter, HTTPException, Depends

from app.models import User
from app.auth import get_current_active_user
from app.services.storage_service import get_storage_service
from app.services.folder_service import FolderService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Folders"])


def get_folder_service():
    """Dependency to get folder service"""
    storage = get_storage_service()
    return FolderService(storage)


@router.delete("/folders/{folder_path:path}")
async def delete_folder(
    folder_path: str,
    current_user: User = Depends(get_current_active_user),
    folder_service: FolderService = Depends(get_folder_service)
):
    """Delete a folder"""
    logger.info(f"User {current_user.username} deleting folder: {folder_path}")
    await folder_service.storage.delete_folder(folder_path)
    return {"message": f"Folder '{folder_path}' deleted successfully"}

