"""Folder management service"""
from typing import List, Dict
from app.services.storage_service import StorageService
from app.core.config import settings
from app.utils.path_utils import normalize_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FolderService:
    """Service for folder operations"""
    
    def __init__(self, storage: StorageService):
        self.storage = storage
    
    async def create_processed_folder_structure(self, project_name: str) -> None:
        """
        Create the standard folder structure in accepted_processed for a project
        
        Args:
            project_name: Name of the project
        """
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
            
            # Create all folders
            for folder_path in folders_to_create:
                await self.storage.create_folder(folder_path)
                logger.debug(f"Created folder: {folder_path}")
            
            logger.info(f"Created {len(folders_to_create)} folders for project: {project_name}")
            
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

