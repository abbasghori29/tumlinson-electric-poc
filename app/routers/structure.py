"""File/folder structure and listing routes"""
from fastapi import APIRouter, Depends

from app.services.storage_service import get_storage_service, StorageService
from app.utils.path_utils import generate_slug
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Structure"])


@router.get("/structure")
async def get_structure(
    search: str = "",
    storage: StorageService = Depends(get_storage_service)
):
    """
    Get folder and file structure with search (no pagination - returns all items)
    
    Args:
        search: Search query for filtering by name
    """
    # Get all items from storage
    data = await storage.list_objects()
    all_items = data["items"]
    folders_set = data["folders_set"]
    
    # Add implicit folders (folders that exist because files are in them)
    for folder_path in folders_set:
        if not any(item.get('path') == folder_path and item.get('item_type') == 'folder' for item in all_items):
            all_items.append({
                "path": folder_path,
                "name": folder_path.split('/')[-1],
                "slug": generate_slug(folder_path.split('/')[-1]),
                "type": "folder",
                "item_type": "folder",
                "size": 0,
                "last_modified": datetime.now().isoformat(),
                "implicit": True
            })
    
    # Apply search filter
    if search.strip():
        search_lower = search.lower()
        all_items = [item for item in all_items if search_lower in item['name'].lower()]
    
    # Sort: folders first, then files, both alphabetically
    all_items.sort(key=lambda x: (x['item_type'] != 'folder', x['name'].lower()))
    
    total_items = len(all_items)
    
    # Return all items (no pagination)
    return {
        "items": all_items,
        "total": total_items
    }

