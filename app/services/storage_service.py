"""Storage service abstraction for S3 and local filesystem"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
import aioboto3
from botocore.exceptions import ClientError
import aiofiles

from app.core.config import settings
from app.utils.path_utils import generate_slug, normalize_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService(ABC):
    """Abstract base class for storage operations"""
    
    @abstractmethod
    async def upload_file(self, file: UploadFile, folder_path: str) -> dict:
        """Upload a file to storage"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> None:
        """Delete a file from storage"""
        pass
    
    @abstractmethod
    async def delete_folder(self, folder_path: str) -> None:
        """Delete a folder from storage"""
        pass
    
    @abstractmethod
    async def create_folder(self, folder_path: str) -> None:
        """Create a folder in storage"""
        pass
    
    @abstractmethod
    async def list_objects(self) -> Dict[str, List]:
        """List all objects in storage"""
        pass


class S3StorageService(StorageService):
    """S3 storage implementation"""
    
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.AWS_S3_BUCKET
        logger.info(f"S3 storage initialized for bucket: {self.bucket}")
    
    async def upload_file(self, file: UploadFile, folder_path: str) -> dict:
        """Upload file to S3 asynchronously"""
        folder_path = normalize_path(folder_path)
        file_slug = generate_slug(Path(file.filename).stem) + Path(file.filename).suffix
        
        s3_key = f"{folder_path}/{file.filename}" if folder_path else file.filename
        
        try:
            async with self.session.client('s3') as s3_client:
                file_content = await file.read()
                await file.seek(0)
                
                await s3_client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=file_content,
                    Metadata={'slug': file_slug}
                )
            
            logger.info(f"Uploaded file to S3: {s3_key}")
            return {
                "filename": file.filename,
                "path": s3_key,
                "slug": file_slug,
                "folder": folder_path if folder_path else "/",
                "type": "file",
                "storage": "s3"
            }
        except ClientError as e:
            logger.error(f"S3 upload error for {s3_key}: {e}")
            raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
    
    async def delete_file(self, file_path: str) -> None:
        """Delete a file from S3"""
        file_path = normalize_path(file_path)
        try:
            async with self.session.client('s3') as s3_client:
                await s3_client.delete_object(Bucket=self.bucket, Key=file_path)
            logger.info(f"Deleted file from S3: {file_path}")
        except ClientError as e:
            logger.error(f"S3 delete error for {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
    
    async def delete_folder(self, folder_path: str) -> None:
        """Delete a folder (all objects with prefix) from S3"""
        folder_path = normalize_path(folder_path)
        try:
            async with self.session.client('s3') as s3_client:
                response = await s3_client.list_objects_v2(Bucket=self.bucket, Prefix=f"{folder_path}/")
                if 'Contents' in response:
                    objects = [{'Key': obj['Key']} for obj in response['Contents']]
                    await s3_client.delete_objects(Bucket=self.bucket, Delete={'Objects': objects})
            logger.info(f"Deleted folder from S3: {folder_path}")
        except ClientError as e:
            logger.error(f"S3 delete folder error for {folder_path}: {e}")
            raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
    
    async def create_folder(self, folder_path: str) -> None:
        """Create a folder placeholder in S3"""
        folder_path = normalize_path(folder_path)
        try:
            async with self.session.client('s3') as s3_client:
                await s3_client.put_object(Bucket=self.bucket, Key=f"{folder_path}/", Body=b"")
            logger.debug(f"Created folder in S3: {folder_path}/")
        except ClientError as e:
            logger.error(f"S3 create folder error for {folder_path}: {e}")
            raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
    
    async def list_objects(self) -> Dict[str, List]:
        """List all objects in S3 bucket"""
        try:
            async with self.session.client('s3') as s3_client:
                response = await s3_client.list_objects_v2(Bucket=self.bucket)
                
                all_items = []
                folders_set = set()
                
                if 'Contents' not in response:
                    return {"items": [], "folders_set": set()}
                
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Get metadata
                    try:
                        metadata_response = await s3_client.head_object(Bucket=self.bucket, Key=key)
                        metadata = metadata_response.get('Metadata', {})
                        slug = metadata.get('slug', generate_slug(Path(key).stem))
                    except:
                        slug = generate_slug(Path(key).stem)
                    
                    if key.endswith('/'):
                        # Folder
                        folder_path = key.rstrip('/')
                        all_items.append({
                            "path": folder_path,
                            "name": folder_path.split('/')[-1],
                            "slug": slug,
                            "type": "folder",
                            "item_type": "folder",
                            "size": 0,
                            "last_modified": obj['LastModified'].isoformat()
                        })
                        folders_set.add(folder_path)
                    else:
                        # File
                        file_parts = key.split('/')
                        file_name = file_parts[-1]
                        folder_path = '/'.join(file_parts[:-1]) if len(file_parts) > 1 else ""
                        
                        # Add parent folders to set
                        if folder_path:
                            parts = folder_path.split('/')
                            for i in range(len(parts)):
                                folders_set.add('/'.join(parts[:i+1]))
                        
                        all_items.append({
                            "name": file_name,
                            "path": key,
                            "slug": slug,
                            "folder": folder_path if folder_path else "/",
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat(),
                            "type": "file",
                            "item_type": "file"
                        })
                
                return {"items": all_items, "folders_set": folders_set}
        except ClientError as e:
            logger.error(f"S3 list objects error: {e}")
            raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


class LocalStorageService(StorageService):
    """Local filesystem storage implementation"""
    
    def __init__(self):
        self.base_path = Path(settings.UPLOAD_FOLDER)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_path}")
    
    async def upload_file(self, file: UploadFile, folder_path: str) -> dict:
        """Upload file locally asynchronously with aiofiles"""
        folder_path = normalize_path(folder_path)
        file_slug = generate_slug(Path(file.filename).stem) + Path(file.filename).suffix
        
        if folder_path:
            full_folder_path = self.base_path / folder_path
            full_folder_path.mkdir(parents=True, exist_ok=True)
            file_path = full_folder_path / file.filename
            relative_path = f"{folder_path}/{file.filename}"
        else:
            file_path = self.base_path / file.filename
            relative_path = file.filename
        
        try:
            contents = await file.read()
            async with aiofiles.open(file_path, "wb") as buffer:
                await buffer.write(contents)
            
            logger.info(f"Uploaded file locally: {relative_path}")
            return {
                "filename": file.filename,
                "path": relative_path,
                "slug": file_slug,
                "folder": folder_path if folder_path else "/",
                "type": "file",
                "storage": "local"
            }
        except Exception as e:
            logger.error(f"Local upload error for {relative_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    
    async def delete_file(self, file_path: str) -> None:
        """Delete a file from local storage"""
        file_path = normalize_path(file_path)
        full_path = self.base_path / file_path
        try:
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
                logger.info(f"Deleted file locally: {file_path}")
            else:
                raise HTTPException(status_code=404, detail="File not found")
        except Exception as e:
            logger.error(f"Local delete error for {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
    
    async def delete_folder(self, folder_path: str) -> None:
        """Delete a folder from local storage"""
        folder_path = normalize_path(folder_path)
        full_path = self.base_path / folder_path
        try:
            if full_path.exists() and full_path.is_dir():
                import shutil
                shutil.rmtree(full_path)
                logger.info(f"Deleted folder locally: {folder_path}")
            else:
                raise HTTPException(status_code=404, detail="Folder not found")
        except Exception as e:
            logger.error(f"Local delete folder error for {folder_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting folder: {str(e)}")
    
    async def create_folder(self, folder_path: str) -> None:
        """Create a folder in local storage"""
        folder_path = normalize_path(folder_path)
        full_path = self.base_path / folder_path
        full_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created folder locally: {folder_path}")
    
    async def list_objects(self) -> Dict[str, List]:
        """List all objects in local storage"""
        all_items = []
        
        if not self.base_path.exists():
            return {"items": [], "folders_set": set()}
        
        # Get all folders
        for folder in self.base_path.rglob('*'):
            if folder.is_dir():
                relative_path = str(folder.relative_to(self.base_path)).replace('\\', '/')
                all_items.append({
                    "path": relative_path,
                    "name": folder.name,
                    "slug": generate_slug(folder.name),
                    "type": "folder",
                    "item_type": "folder",
                    "size": 0,
                    "last_modified": datetime.fromtimestamp(folder.stat().st_mtime).isoformat()
                })
        
        # Get all files
        for file in self.base_path.rglob('*'):
            if file.is_file():
                relative_path = str(file.relative_to(self.base_path)).replace('\\', '/')
                folder_path = str(file.parent.relative_to(self.base_path)).replace('\\', '/')
                if folder_path == '.':
                    folder_path = ""
                
                all_items.append({
                    "name": file.name,
                    "path": relative_path,
                    "slug": generate_slug(file.stem) + file.suffix,
                    "folder": folder_path if folder_path else "/",
                    "size": file.stat().st_size,
                    "last_modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                    "type": "file",
                    "item_type": "file"
                })
        
        return {"items": all_items, "folders_set": set()}


# Factory function to get the appropriate storage service
def get_storage_service() -> StorageService:
    """Get the appropriate storage service based on configuration"""
    if settings.use_s3:
        return S3StorageService()
    else:
        return LocalStorageService()

