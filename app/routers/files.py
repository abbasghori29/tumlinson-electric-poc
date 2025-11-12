"""File management routes"""
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
import json

from app.models import User
from app.auth import get_current_active_user
from app.services.storage_service import get_storage_service
from app.services.folder_service import FolderService
from app.services.file_service import FileService
from app.utils.path_utils import normalize_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Files"])


def get_file_service():
    """Dependency to get file service"""
    storage = get_storage_service()
    folder_service = FolderService(storage)
    return FileService(storage, folder_service)


@router.post("/upload-multiple")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    paths: str = Form(...),
    client_id: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    file_service: FileService = Depends(get_file_service)
):
    """
    Upload multiple files with their folder paths (for folder upload)
    Preserves complete folder structure including the root folder name.
    
    Args:
        files: List of files to upload
        paths: JSON string of file paths
        client_id: Optional WebSocket client ID for progress updates
    """
    # Parse the paths JSON string
    file_paths = json.loads(paths)
    
    logger.info(f"User {current_user.username} uploading {len(files)} files (client_id: {client_id})")
    
    # Upload files with WebSocket progress
    result = await file_service.upload_multiple_files(files, file_paths, client_id)
    
    # Trigger hook in background if successful
    if result['success'] > 0:
        first_path = normalize_path(file_paths[0]) if file_paths else ""
        parts = first_path.split('/') if first_path else []
        root_folder = parts[0] if parts else ""
        
        if root_folder:
            folder_info = {
                "folder_name": root_folder,
                "total_files": result['success'],
                "file_paths": [r['path'] for r in result['results']],
                "storage_type": "s3" if get_storage_service().__class__.__name__ == "S3StorageService" else "local",
                "upload_location": root_folder
            }
            
            # Add hook to background tasks with client_id for WebSocket updates
            background_tasks.add_task(file_service.on_folder_uploaded, folder_info, client_id)
            logger.info("Hook added to background tasks")
    
    return result


@router.delete("/files/{file_path:path}")
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_active_user),
    file_service: FileService = Depends(get_file_service)
):
    """Delete a file"""
    logger.info(f"User {current_user.username} deleting file: {file_path}")
    await file_service.storage.delete_file(file_path)
    return {"message": f"File '{file_path}' deleted successfully"}

