"""File management service"""
from typing import List, Dict, Optional
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
        file_paths: List[str],
        client_id: Optional[str] = None
    ) -> Dict:
        """
        Upload multiple files with optional WebSocket progress
        Files are uploaded in small batches to show real-time progress
        
        Args:
            files: List of files to upload
            file_paths: List of folder paths for each file
            client_id: Optional WebSocket client ID for progress updates
            
        Returns:
            Dictionary with success/failure counts and results
        """
        from app.services.websocket_manager import ws_manager
        
        logger.info(f"Starting upload of {len(files)} files")
        
        # Send initial progress
        if client_id:
            await ws_manager.send_progress(
                client_id, 
                f"Starting upload of {len(files)} files...",
                1  # Start at 1% to show something is happening
            )
            # Small delay so initial message is visible
            await asyncio.sleep(0.2)
        
        results = []
        errors = []
        completed_count = 0
        
        # Batch size for concurrent uploads (balance between speed and progress visibility)
        BATCH_SIZE = 5
        
        # File upload takes 85% of total progress (0-85%)
        # Folder creation will be 85-100%
        FILE_UPLOAD_PROGRESS_WEIGHT = 85
        
        async def upload_single_file(idx, file, folder_path):
            try:
                # Extract actual filename from full path
                actual_filename = file.filename.split('/')[-1]
                logger.debug(f"Uploading: {file.filename} -> {actual_filename} to {folder_path}")
                
                # Override with just the filename
                file.filename = actual_filename
                
                result = await self.storage.upload_file(file, folder_path)
                return ("success", result, actual_filename)
                
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {e}")
                actual_filename = file.filename.split('/')[-1]
                return ("error", {"file": actual_filename, "error": str(e)}, actual_filename)
        
        # Process uploads in batches for better progress visibility
        for batch_start in range(0, len(files), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(files))
            batch_files = files[batch_start:batch_end]
            
            # Send progress for this batch
            if client_id:
                # Calculate real progress: batch_start / total_files * 85%
                # Add 1% to show movement even at start
                batch_progress = int((batch_start / len(files)) * FILE_UPLOAD_PROGRESS_WEIGHT)
                if batch_progress == 0 and batch_start == 0:
                    batch_progress = 1  # Show at least 1% to indicate start
                await ws_manager.send_progress(
                    client_id,
                    f"Uploading batch {batch_start + 1}-{batch_end} of {len(files)} files...",
                    batch_progress
                )
                # Small delay to make batch start message visible
                await asyncio.sleep(0.1)
            
            # Create tasks for this batch
            batch_tasks = [
                upload_single_file(
                    batch_start + idx, 
                    file, 
                    file_paths[batch_start + idx] if (batch_start + idx) < len(file_paths) else ""
                )
                for idx, file in enumerate(batch_files)
        ]
        
            # Show uploading progress (before actual upload completes)
            if client_id and len(batch_files) > 0:
                uploading_progress = int((batch_start / len(files)) * FILE_UPLOAD_PROGRESS_WEIGHT) + 5
                uploading_progress = min(uploading_progress, FILE_UPLOAD_PROGRESS_WEIGHT - 5)
                await ws_manager.send_progress(
                    client_id,
                    f"⏳ Uploading {len(batch_files)} file(s) to storage...",
                    max(2, uploading_progress)
                )
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Process results and send individual progress updates
            for status, data, filename in batch_results:
                if status == "success":
                    results.append(data)
                    completed_count += 1
                    
                    if client_id:
                        # Calculate real progress: completed/total * 85%
                        # Ensure minimum progress of 2% to show movement
                        file_progress = max(2, int((completed_count / len(files)) * FILE_UPLOAD_PROGRESS_WEIGHT))
                        await ws_manager.send_progress(
                            client_id,
                            f"✓ Uploaded ({completed_count}/{len(files)}): {filename}",
                            file_progress
                        )
                        # Small delay to make progress visible
                        await asyncio.sleep(0.05)
                else:
                    errors.append(data)
                    completed_count += 1
                    
                    if client_id:
                        # Calculate real progress: completed/total * 85%
                        # Ensure minimum progress of 2% to show movement
                        file_progress = max(2, int((completed_count / len(files)) * FILE_UPLOAD_PROGRESS_WEIGHT))
                        await ws_manager.send_progress(
                            client_id,
                            f"✗ Failed ({completed_count}/{len(files)}): {filename}",
                            file_progress
                        )
                        # Small delay to make progress visible
                        await asyncio.sleep(0.05)
        
        logger.info(f"Upload complete: {len(results)} success, {len(errors)} errors")
        
        # Send final progress for file upload phase (85%)
        if client_id:
            await ws_manager.send_progress(
                client_id,
                f"File upload complete: {len(results)} uploaded, {len(errors)} failed",
                FILE_UPLOAD_PROGRESS_WEIGHT
            )
            # Small delay so final message is visible
            await asyncio.sleep(0.2)
        
        return {
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    
    async def on_folder_uploaded(self, folder_info: dict, client_id: Optional[str] = None) -> None:
        """
        Hook that triggers after folder upload (runs in background)
        Creates folder structure in accepted_processed if upload is to accepted_invites
        
        Args:
            folder_info: Dictionary containing folder upload information
            client_id: Optional WebSocket client ID for progress updates
        """
        from app.services.websocket_manager import ws_manager
        
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
                
                if client_id:
                    await ws_manager.send_progress(
                        client_id,
                        f"Creating directory structure for: {project_name}",
                        86
                    )
                
                # Pass progress range 86-100% to folder service
                await self.folder_service.create_processed_folder_structure(project_name, client_id, 86, 100)
                
                logger.info(f"✅ Created folder structure for: {project_name}")
                
                if client_id:
                    await ws_manager.send_complete(
                        client_id,
                        f"Upload complete! Created folder structure for: {project_name}",
                        {"project_name": project_name, "total_files": folder_info['total_files']}
                    )
        except Exception as e:
            logger.error(f"Failed to create processed folder structure: {e}")
            
            if client_id:
                await ws_manager.send_error(
                    client_id,
                    f"Failed to create folder structure: {str(e)}"
                )

