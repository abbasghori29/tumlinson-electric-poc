"""
Database configuration and session management for Supabase PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine with connection timeout settings
# For connection pooling with PgBouncer, use pool_pre_ping and disable pool recycle
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,  # Set to True for SQL query logging
        connect_args={
            "connect_timeout": 10,  # 10 second connection timeout
            "options": "-c statement_timeout=30000"  # 30 second statement timeout
        }
    )
else:
    engine = None

# Create SessionLocal class for database sessions
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    SessionLocal = None

# Create Base class for declarative models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session
    Usage in FastAPI routes:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    if SessionLocal is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Please set DATABASE_URL environment variable."
        )
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        from sqlalchemy.exc import OperationalError
        from fastapi import HTTPException, status
        if isinstance(e, OperationalError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection failed: {str(e)}. Please check your database configuration and network connectivity."
            )
        raise
    finally:
        db.close()

