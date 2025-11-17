"""Tracking CSV/Excel file routes"""
from fastapi import APIRouter
from pathlib import Path
import csv
from io import StringIO, BytesIO
import pandas as pd
import aioboto3

from app.core.config import settings
from app.utils.logger import get_logger
from app.services.cache_service import get_cache_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Tracking"])


async def _load_csv_rows_s3() -> list:
    """Load CSV/Excel rows from S3. Returns list of dicts."""
    # Use the configured filename from S3
    s3_key = settings.TRACKING_S3_KEY
    
    logger.info(f"Loading tracking file from S3 bucket '{settings.AWS_S3_BUCKET}' with key '{s3_key}'")
    
    try:
        session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        async with session.client('s3') as s3_client:
            # First check if file exists
            try:
                await s3_client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
            except Exception as head_error:
                logger.error(f"File not found at S3 key '{s3_key}' in bucket '{settings.AWS_S3_BUCKET}'. Error: {head_error}")
                # Try to list files in root to help debug
                try:
                    response = await s3_client.list_objects_v2(Bucket=settings.AWS_S3_BUCKET, Prefix="", Delimiter="/")
                    root_files = []
                    if 'Contents' in response:
                        root_files = [obj['Key'] for obj in response['Contents'] if not obj['Key'].endswith('/')]
                    logger.info(f"Files found in bucket root: {root_files[:10]}")  # Show first 10
                except:
                    pass
                raise
            
            obj = await s3_client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
            content = await obj['Body'].read()
            logger.info(f"Successfully downloaded {len(content)} bytes from S3 key '{s3_key}'")
            
            # Check file extension
            file_ext = Path(s3_key).suffix.lower()
            
            if file_ext in ['.xls', '.xlsx']:
                # Excel file - use pandas
                try:
                    engine = 'xlrd' if file_ext == '.xls' else 'openpyxl'
                    logger.info(f"Reading Excel file with engine: {engine}")
                    df = pd.read_excel(BytesIO(content), engine=engine)
                    logger.info(f"Excel file read successfully. Shape: {df.shape}, Columns: {list(df.columns)}")
                    
                    if df.empty:
                        logger.warning("Excel file is empty - no data rows found")
                        return []
                    
                    # Replace NaN values with None
                    df = df.where(pd.notna(df), None)
                    # Convert datetime objects to strings
                    for col in df.columns:
                        if df[col].dtype == 'datetime64[ns]':
                            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    records = df.to_dict('records')
                    
                    # Clean records
                    for record in records:
                        for key, value in record.items():
                            if value is None:
                                continue
                            try:
                                if pd.isna(value):
                                    record[key] = None
                                elif isinstance(value, pd.Timestamp):
                                    record[key] = str(value)
                                elif isinstance(value, float) and (value != value):  # NaN check
                                    record[key] = None
                            except (TypeError, ValueError):
                                pass
                    logger.info(f"Loaded {len(records)} rows from S3 Excel file")
                    return records
                except Exception as parse_error:
                    logger.error(f"Error parsing Excel file: {parse_error}")
                    logger.error(f"File size: {len(content)} bytes, Extension: {file_ext}")
                    raise
            else:
                # CSV file
                try:
                    text = content.decode('utf-8')
                    logger.info(f"Decoded CSV content, length: {len(text)} characters")
                    reader = csv.DictReader(StringIO(text))
                    rows = list(reader)
                    logger.info(f"Loaded {len(rows)} rows from S3 CSV")
                    if not rows:
                        logger.warning("CSV file appears to be empty or has no data rows")
                    return rows
                except Exception as parse_error:
                    logger.error(f"Error parsing CSV file: {parse_error}")
                    logger.error(f"File size: {len(content)} bytes")
                    raise
    except Exception as e:
        error_msg = f"Error loading tracking file from S3 bucket '{settings.AWS_S3_BUCKET}' with key '{s3_key}': {e}"
        logger.error(error_msg)
        logger.error(f"Current configuration - Bucket: {settings.AWS_S3_BUCKET}, Key: {s3_key}, Region: {settings.AWS_REGION}")
        return []


def _load_csv_rows_local() -> list:
    """Load CSV/Excel rows from local filesystem. Returns list of dicts."""
    file_path = Path(settings.TRACKING_CSV_PATH).resolve()
    
    logger.info(f"Looking for tracking file at: {file_path}")
    
    if not file_path.exists():
        logger.warning(f"Tracking file not found at: {file_path}")
        return []
    
    try:
        file_ext = file_path.suffix.lower()
        
        if file_ext in ['.xls', '.xlsx']:
            # Excel file - use pandas
            df = pd.read_excel(file_path, engine='xlrd' if file_ext == '.xls' else 'openpyxl')
            # Replace NaN values with None
            df = df.where(pd.notna(df), None)
            # Convert datetime objects to strings
            for col in df.columns:
                if df[col].dtype == 'datetime64[ns]':
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            records = df.to_dict('records')
            # Clean records
            for record in records:
                for key, value in record.items():
                    if value is None:
                        continue
                    try:
                        if pd.isna(value):
                            record[key] = None
                        elif isinstance(value, pd.Timestamp):
                            record[key] = str(value)
                        elif isinstance(value, float) and (value != value):  # NaN check
                            record[key] = None
                    except (TypeError, ValueError):
                        pass
            logger.info(f"Loaded {len(records)} rows from Excel file")
            return records
        else:
            # CSV file
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                logger.info(f"Loaded {len(rows)} rows from CSV")
                return rows
    except Exception as e:
        logger.error(f"Error reading tracking file: {e}")
        return []


def _filter_rows(rows: list, search: str) -> dict:
    """Filter rows by search query"""
    if not rows:
        return {
            "headers": [],
            "rows": [],
            "total": 0
        }
    
    headers = list(rows[0].keys())
    
    # Search across all columns (case-insensitive substring)
    if search and search.strip():
        q = search.lower()
        rows = [r for r in rows if any((str(v or "").lower().find(q) != -1) for v in r.values())]
    
    total = len(rows)
    
    return {
        "headers": headers,
        "rows": rows,
        "total": total
    }


@router.get("/tracking")
async def get_tracking_csv(search: str = ""):
    """Return CSV/Excel rows with search filtering (no pagination - returns all rows)"""
    try:
        # Use S3 if configured, otherwise use local
        if settings.use_s3:
            # Check cache first
            cache_service = await get_cache_service()
            cached_rows = await cache_service.get_tracking_cache(
                settings.AWS_S3_BUCKET, 
                settings.TRACKING_S3_KEY
            )
            
            if cached_rows is not None:
                logger.debug(f"Using cached tracking data for bucket '{settings.AWS_S3_BUCKET}' key '{settings.TRACKING_S3_KEY}'")
                rows = cached_rows
            else:
                # Cache miss - load from S3
                logger.info(f"Cache miss - loading from S3 bucket '{settings.AWS_S3_BUCKET}' key '{settings.TRACKING_S3_KEY}'")
                rows = await _load_csv_rows_s3()
                if rows:
                    # Cache the result only if we got data
                    await cache_service.set_tracking_cache(
                        settings.AWS_S3_BUCKET,
                        settings.TRACKING_S3_KEY,
                        rows,
                        ttl=settings.CACHE_TTL
                    )
                    logger.info(f"Loaded and cached {len(rows)} rows from S3")
                else:
                    logger.warning(f"No rows loaded from S3 - file may be missing or empty")
        else:
            rows = _load_csv_rows_local()
    except Exception as e:
        logger.error(f"Failed to load tracking data: {e}")
        rows = []
    
    return _filter_rows(rows, search)


@router.get("/tracking/debug")
async def debug_tracking_config():
    """Debug endpoint to check tracking file configuration and list available files"""
    cache_service = await get_cache_service()
    cached_data = await cache_service.get_tracking_cache(
        settings.AWS_S3_BUCKET,
        settings.TRACKING_S3_KEY
    )
    
    result = {
        "s3_configured": settings.use_s3,
        "bucket": settings.AWS_S3_BUCKET,
        "region": settings.AWS_REGION,
        "tracking_s3_key": settings.TRACKING_S3_KEY,
        "file_exists": False,
        "error": None,
        "root_files": [],
        "cache_status": {
            "has_cached_data": cached_data is not None,
            "cached_row_count": len(cached_data) if cached_data else 0
        }
    }
    
    if not settings.use_s3:
        result["error"] = "S3 is not configured"
        return result
    
    try:
        session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        async with session.client('s3') as s3_client:
            # Check if the configured file exists
            try:
                await s3_client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=settings.TRACKING_S3_KEY)
                result["file_exists"] = True
            except Exception as e:
                result["error"] = f"File not found: {str(e)}"
            
            # List files in root (first 50)
            try:
                response = await s3_client.list_objects_v2(
                    Bucket=settings.AWS_S3_BUCKET, 
                    Prefix="", 
                    Delimiter="/",
                    MaxKeys=50
                )
                if 'Contents' in response:
                    result["root_files"] = [
                        {
                            "key": obj['Key'],
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat()
                        }
                        for obj in response['Contents'] 
                        if not obj['Key'].endswith('/')
                    ]
            except Exception as e:
                result["error"] = f"Error listing files: {str(e)}"
    
    except Exception as e:
        result["error"] = f"Error connecting to S3: {str(e)}"
    
    return result

