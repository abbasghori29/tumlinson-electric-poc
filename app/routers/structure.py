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
    page: int = 1,
    limit: int = 50,
    search: str = "",
    storage: StorageService = Depends(get_storage_service)
):
    """
    Get folder and file structure with pagination and search
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 50, use 0 for all)
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
    
    # Handle "all" items case (limit = 0)
    if limit <= 0:
        return {
            "items": all_items,
            "total": total_items,
            "page": 1,
            "limit": 0,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False
        }
    
    # Calculate pagination
    total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1
    page = max(1, min(page, total_pages))  # Clamp page to valid range
    
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    paginated_items = all_items[start_index:end_index]
    
    return {
        "items": paginated_items,
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

