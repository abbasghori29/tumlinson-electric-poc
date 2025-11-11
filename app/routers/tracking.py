"""Tracking CSV/Excel file routes"""
from fastapi import APIRouter
from pathlib import Path
import csv
from io import StringIO, BytesIO
import pandas as pd
import aioboto3

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Tracking"])


async def _load_csv_rows_s3() -> list:
    """Load CSV/Excel rows from S3. Returns list of dicts."""
    # Use the configured filename from S3
    s3_key = settings.TRACKING_S3_KEY
    
    logger.info(f"Loading tracking file from S3: {s3_key}")
    
    try:
        session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        async with session.client('s3') as s3_client:
            obj = await s3_client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
            content = await obj['Body'].read()
            logger.info(f"Successfully downloaded {len(content)} bytes from S3")
            
            # Check file extension
            file_ext = Path(s3_key).suffix.lower()
            
            if file_ext in ['.xls', '.xlsx']:
                # Excel file - use pandas
                df = pd.read_excel(BytesIO(content), engine='xlrd' if file_ext == '.xls' else 'openpyxl')
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
            else:
                # CSV file
                text = content.decode('utf-8')
                reader = csv.DictReader(StringIO(text))
                rows = list(reader)
                logger.info(f"Loaded {len(rows)} rows from S3 CSV")
                return rows
    except Exception as e:
        logger.error(f"Error loading tracking file from S3: {e}")
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
            rows = await _load_csv_rows_s3()
        else:
            rows = _load_csv_rows_local()
    except Exception as e:
        logger.error(f"Failed to load tracking data: {e}")
        rows = []
    
    return _filter_rows(rows, search)

