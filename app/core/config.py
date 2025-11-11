"""Application configuration"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # Application
    APP_TITLE: str = "Tumlinson Electrive Drive"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET_NAME", "")
    
    # Local Storage
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # Folders
    ROOT_INVITES: str = "accepted_invites"
    ROOT_PROCESSED: str = "accepted_processed"
    
    # Tracking
    TRACKING_CSV_PATH: str = os.getenv(
        "TRACKING_CSV_PATH", 
        str(Path(__file__).parent.parent.parent / "Customers.csv")
    )
    TRACKING_S3_KEY: str = os.getenv(
        "TRACKING_S3_KEY",
        "Estimate Tracking and Historical Data 3.06.2025.xls"
    )
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    @property
    def use_s3(self) -> bool:
        """Check if S3 is configured"""
        return bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY and self.AWS_S3_BUCKET)
    
    @property
    def folder_structure_template(self) -> list:
        """Template for folder structure in accepted_processed"""
        return [
            "",  # Root project folder
            "0 ITB's & Plan Link",
            "1 Bid Docs",
            "1 Bid Docs/01 - Bid",
            "1 Bid Docs/01 - Bid/00-TE Extracted Drawings",
            "1 Bid Docs/01 - Bid/00-TE Extracted Drawings/00 LC Drawings",
            "1 Bid Docs/01 - Bid/01-TE Extracted Specifications",
            "2 Electrical",
            "3 Telecomm",
            "4 NDA"
        ]


# Global settings instance
settings = Settings()

