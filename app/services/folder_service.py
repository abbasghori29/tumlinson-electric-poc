"""Folder management service"""
from typing import List, Dict, Optional
from app.services.storage_service import StorageService
from app.core.config import settings
from app.utils.path_utils import normalize_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FolderService:
    """Service for folder operations"""
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    async def create_processed_folder_structure(
        self, 
        project_name: str, 
        client_id: Optional[str] = None,
        start_progress: int = 0,
        end_progress: int = 100
    ) -> None:
        """
        Create the standard folder structure in accepted_processed for a project
        
        Args:
            project_name: Name of the project
            client_id: Optional WebSocket client ID for progress updates
            start_progress: Starting progress percentage (default 0)
            end_progress: Ending progress percentage (default 100)
        """
        from app.services.websocket_manager import ws_manager
        import asyncio
        
        try:
            processed_root = f"{settings.ROOT_PROCESSED}/{project_name}"
            
            # Build folder list from template
            folders_to_create = []
            for folder_template in settings.folder_structure_template:
                if folder_template == "":
                    # Root project folder
                    folders_to_create.append(processed_root)
                else:
                    folders_to_create.append(f"{processed_root}/{folder_template}")
            
            logger.info(f"Creating folder structure for project: {project_name}")
            
            # Calculate progress range
            progress_range = end_progress - start_progress
            
            # Create all folders sequentially with progress updates
            for idx, folder_path in enumerate(folders_to_create):
                # Extract just the folder name for display
                folder_display = folder_path.replace(processed_root + "/", "").replace(processed_root, project_name)
                
                if client_id:
                    # Calculate progress within the range (86-100%)
                    folder_progress = start_progress + int((idx / len(folders_to_create)) * progress_range)
                    await ws_manager.send_progress(
                        client_id,
                        f"📁 Creating folder ({idx + 1}/{len(folders_to_create)}): {folder_display}",
                        folder_progress
                    )
                
                await self.storage.create_folder(folder_path)
                logger.debug(f"Created folder: {folder_path}")
                
                # Small delay to ensure progress messages are visible
                await asyncio.sleep(0.15)
            
            logger.info(f"Created {len(folders_to_create)} folders for project: {project_name}")
            
            if client_id:
                await ws_manager.send_progress(
                    client_id,
                    f"✓ Created {len(folders_to_create)} folders for: {project_name}",
                    end_progress
                )
            
        except Exception as e:
            logger.error(f"Failed to create folder structure for {project_name}: {e}")
            raise
    
    async def ensure_root_folders(self) -> None:
        """Ensure required root folders exist in storage"""
        try:
            await self.storage.create_folder(settings.ROOT_INVITES)
            await self.storage.create_folder(settings.ROOT_PROCESSED)
            logger.info("Root folders ensured")
        except Exception as e:
            logger.error(f"Failed to ensure root folders: {e}")
            raise

