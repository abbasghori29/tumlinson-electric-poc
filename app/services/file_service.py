"""File management service"""
from typing import List, Dict
from fastapi import UploadFile
import asyncio

from app.services.storage_service import StorageService
from app.services.folder_service import FolderService
from app.core.config import settings
from app.utils.path_utils import normalize_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileService:
    """Service for file operations"""
    
    def __init__(self, storage: StorageService, folder_service: FolderService):
        self.storage = storage
        self.folder_service = folder_service
    
    async def upload_multiple_files(
        self, 
        files: List[UploadFile], 
        file_paths: List[str]
    ) -> Dict:
        """
        Upload multiple files concurrently
        
        Args:
            files: List of files to upload
            file_paths: List of folder paths for each file
            
        Returns:
            Dictionary with success/failure counts and results
        """
        logger.info(f"Starting upload of {len(files)} files")
        
        results = []
        errors = []
        
        async def upload_single_file(idx, file, folder_path):
            try:
                # Extract actual filename from full path
                actual_filename = file.filename.split('/')[-1]
                logger.debug(f"Uploading: {file.filename} -> {actual_filename} to {folder_path}")
                
                # Override with just the filename
                file.filename = actual_filename
                
                result = await self.storage.upload_file(file, folder_path)
                return ("success", result)
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {e}")
                return ("error", {"file": file.filename, "error": str(e)})
        
        # Process all uploads concurrently
        upload_tasks = [
            upload_single_file(idx, file, file_paths[idx] if idx < len(file_paths) else "")
            for idx, file in enumerate(files)
        ]
        
        upload_results = await asyncio.gather(*upload_tasks)
        
        # Separate successes and errors
        for status, data in upload_results:
            if status == "success":
                results.append(data)
            else:
                errors.append(data)
        
        logger.info(f"Upload complete: {len(results)} success, {len(errors)} errors")
        
        return {
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    
    async def on_folder_uploaded(self, folder_info: dict) -> None:
        """
        Hook that triggers after folder upload (runs in background)
        Creates folder structure in accepted_processed if upload is to accepted_invites
        
        Args:
            folder_info: Dictionary containing folder upload information
        """
        logger.info(f"📁 Folder uploaded: {folder_info['folder_name']} ({folder_info['total_files']} files)")
        
        try:
            if not folder_info.get('file_paths'):
                return
            
            first_path = folder_info['file_paths'][0]
            first_path = normalize_path(first_path)
            parts = first_path.split('/')
            
            # Check if upload is to accepted_invites
            if len(parts) >= 2 and parts[0] == settings.ROOT_INVITES:
                project_name = parts[1]
                
                logger.info(f"Creating processed folder structure for: {project_name}")
                await self.folder_service.create_processed_folder_structure(project_name)
                logger.info(f"✅ Created folder structure for: {project_name}")
        except Exception as e:
            logger.error(f"Failed to create processed folder structure: {e}")

