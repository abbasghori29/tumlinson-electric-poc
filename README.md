# Tumlinson Electrive - POC 

A scalable FastAPI-based web application for managing folders and files with support for both AWS S3 and local storage. Features a professional frontend for creating nested folders, uploading files, and displaying slugs.

## 🚀 Features

- **Folder Management**: Create folders with nested paths (e.g., `folder1/folder2/folder3`)
- **File Upload**: Upload individual files to specific folders
- **Folder Upload**: Upload entire folders with nested structure (preserves all subfolders and files)
- **Auto Folder Structure**: Automatically creates standardized folder structure in `accepted_processed` when folders are uploaded to `accepted_invites`
- **Folder Navigation**: Click folders to browse into them, use breadcrumb to navigate back
- **Dual Storage**: Automatic fallback from S3 to local storage if AWS is not configured
- **Slug Generation**: Automatic URL-friendly slug generation for all folders and files
- **Professional UI**: OneDrive-like interface with grid layout and orange/black/white theme (Tumlinson Electrive Drive branding)
- **Delete Operations**: Delete files and folders (including nested content)
- **Real-time Updates**: Refresh structure view to see changes
- **Bulk Operations**: Handle multiple files in a single upload (folder upload)
- **Tracking Integration**: Load tracking data from Excel/CSV files (S3 or local)
- **User Authentication**: JWT-based authentication system
- **Pagination & Search**: Efficient pagination and search for large file structures

## 📋 Prerequisites

- Python 3.8 or higher
- AWS Account (optional, for S3 storage)
- PostgreSQL database (for user authentication)
- pip (Python package manager)

## 🛠️ Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**:
   
   Create a `.env` file in the project root:
   ```env
   # Database (PostgreSQL)
   DATABASE_URL=postgresql://user:password@host:port/database
   
   # AWS S3 (Optional - falls back to local storage if not configured)
   AWS_ACCESS_KEY_ID=your_actual_access_key
   AWS_SECRET_ACCESS_KEY=your_actual_secret_key
   AWS_REGION=us-east-1
   AWS_S3_BUCKET_NAME=your_bucket_name
   
   # Tracking File (S3 key if using S3, or local path if using local storage)
   TRACKING_S3_KEY=Estimate Tracking and Historical Data 3.06.2025.xls
   
   # Authentication
   SECRET_KEY=your-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Application
   HOST=0.0.0.0
   PORT=8000
   UPLOAD_FOLDER=uploads
   ```

   **Note**: If you don't configure AWS credentials, the application will automatically use local storage instead.

5. **Run database migrations**:
```bash
alembic upgrade head
```

## 🏃 Running the Application

1. **Start the server**:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. **Access the application**:
   
   Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## 📖 API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/logout` - Logout (optional)
- `GET /api/auth/me` - Get current user profile

### Configuration
- `GET /api/config` - Get current storage configuration

### Files
- `POST /api/upload-multiple` - Upload multiple files with paths (for folder upload)
  - Body: `files` (multiple files), `paths` (JSON array of folder paths)
  - Requires: Authentication
  - **Auto-creates folder structure** in `accepted_processed` if upload is to `accepted_invites`

- `DELETE /api/files/{file_path:path}` - Delete a file
  - Requires: Authentication

### Folders
- `DELETE /api/folders/{folder_path:path}` - Delete a folder and its contents
  - Requires: Authentication

### Structure
- `GET /api/structure` - Get folder/file structure with pagination and search
  - Query params: `page` (default: 1), `limit` (default: 50, use 0 for all), `search` (optional)

### Tracking
- `GET /api/tracking` - Get tracking data from Excel/CSV file
  - Query params: `search` (optional, filters rows)
  - Loads from S3 if configured, otherwise from local file

## 🏗️ Architecture

The application follows FastAPI best practices with a clean, scalable architecture:

```
app/
├── core/
│   ├── config.py              # Centralized configuration management
│   └── dependencies.py        # Shared dependencies
├── services/
│   ├── storage_service.py     # Storage abstraction (S3/Local)
│   ├── folder_service.py      # Folder operations business logic
│   └── file_service.py        # File operations business logic
├── routers/
│   ├── auth.py                # Authentication routes
│   ├── files.py               # File management routes
│   ├── folders.py             # Folder management routes
│   ├── structure.py            # File/folder listing routes
│   └── tracking.py            # Tracking data routes
├── utils/
│   ├── path_utils.py          # Path normalization and slug generation
│   └── logger.py              # Logging configuration
├── models.py                   # SQLAlchemy database models
├── schemas.py                  # Pydantic schemas for validation
├── auth.py                     # Authentication utilities
└── database.py                 # Database configuration

main.py                         # FastAPI app entry point (minimal)
static/                         # Frontend HTML files
├── login.html
└── dashboard.html
```

### Key Design Patterns

- **Service Layer**: Business logic separated from routes
- **Storage Abstraction**: Easy to switch between S3 and local storage
- **Dependency Injection**: Proper use of FastAPI's dependency system
- **Configuration Management**: Centralized settings via environment variables
- **Proper Logging**: Structured logging instead of print statements
- **Type Safety**: Full type hints throughout

## 🎨 Frontend Features

The professional Tumlinson Electrive Drive interface provides:

1. **Upload Folder**:
   - Select entire folders from your computer
   - Automatically preserves nested folder structure
   - Shows preview of files to be uploaded
   - Handles hundreds of files with nested subfolders
   - **Auto-creates folder structure** in `accepted_processed` when uploading to `accepted_invites`

2. **Folder Navigation**:
   - Click any folder to browse into it
   - Breadcrumb navigation at the top
   - Click breadcrumb items to navigate back
   - Shows only current directory contents

3. **File Grid View**:
   - Professional OneDrive-like layout
   - Folders shown first (light orange background)
   - Files listed below folders
   - Columns: Icon | Name (with slug) | Size | Modified | Actions
   - Responsive design for mobile devices
   - Pagination support for large directories

4. **Tracking Tab**:
   - View tracking data from Excel/CSV files
   - Search functionality across all columns
   - Loads from S3 or local storage

5. **Visual Features**:
   - Orange/Black/White theme (Tumlinson Electrive Drive branding)
   - Sticky action bar (always visible at top)
   - Real-time messages for success/error
   - Empty state indicators
   - Delete confirmations

## 📁 Folder Structure Auto-Creation

When a folder is uploaded to `accepted_invites/{project_name}/`, the system automatically creates the following structure in `accepted_processed/{project_name}/`:

```
project_name/
├── 0 ITB's & Plan Link/
├── 1 Bid Docs/
│   └── 01 - Bid/
│       ├── 00-TE Extracted Drawings/
│       │   └── 00 LC Drawings/
│       └── 01-TE Extracted Specifications/
├── 2 Electrical/
├── 3 Telecomm/
└── 4 NDA/
```

This happens automatically in the background after file upload completes.

## 🔐 AWS S3 Setup

If you want to use AWS S3 storage:

1. **Create an S3 bucket** in AWS Console

2. **Create IAM user** with the following permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket",
           "s3:HeadObject"
         ],
         "Resource": [
           "arn:aws:s3:::your-bucket-name",
           "arn:aws:s3:::your-bucket-name/*"
         ]
       }
     ]
   }
   ```

3. **Get access credentials** (Access Key ID and Secret Access Key)

4. **Update `.env` file** with your credentials

5. **Upload tracking file** to S3 bucket root:
   - File name: `Estimate Tracking and Historical Data 3.06.2025.xls` (or configure `TRACKING_S3_KEY`)

## 📁 Local Storage

If AWS is not configured, the application will:
- Create an `uploads/` folder in the project directory
- Store all files and folders locally
- Maintain the same folder structure as S3
- Use local file path for tracking data (configured via `TRACKING_CSV_PATH`)

## 🔧 Slug Generation

The application automatically generates URL-friendly slugs:
- Converts to lowercase
- Removes special characters
- Replaces spaces with hyphens
- Example: `My Project 2024!` → `my-project-2024`

## 🐛 Troubleshooting

### AWS Connection Issues
- Check your AWS credentials in `.env`
- Verify S3 bucket exists and is accessible
- Check IAM permissions
- Application will automatically fallback to local storage

### Database Connection Issues
- Verify `DATABASE_URL` in `.env` is correct
- Ensure PostgreSQL is running
- Check database migrations: `alembic upgrade head`

### Port Already in Use
Change the port in `.env`:
```env
PORT=8001
```

### File Upload Errors
- Check file size limits (default: unlimited, but can be configured in FastAPI)
- Verify folder path format (use `/` for nested paths)
- Check server logs for detailed error messages

### Tracking File Not Found
- If using S3: Verify file exists in bucket with correct name (check `TRACKING_S3_KEY`)
- If using local: Verify file path in `TRACKING_CSV_PATH` is correct

## 📦 Project Structure

```
.
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (configure this!)
├── README.md                  # This file
├── alembic.ini                # Alembic configuration
├── app/
│   ├── core/                  # Core application modules
│   │   ├── config.py          # Configuration management
│   │   └── dependencies.py    # Shared dependencies
│   ├── services/              # Business logic layer
│   │   ├── storage_service.py # Storage abstraction
│   │   ├── folder_service.py  # Folder operations
│   │   └── file_service.py    # File operations
│   ├── routers/               # API route handlers
│   │   ├── auth.py            # Authentication routes
│   │   ├── files.py           # File routes
│   │   ├── folders.py        # Folder routes
│   │   ├── structure.py      # Structure listing routes
│   │   └── tracking.py        # Tracking routes
│   ├── utils/                 # Utility functions
│   │   ├── path_utils.py     # Path utilities
│   │   └── logger.py         # Logging setup
│   ├── models.py             # Database models
│   ├── schemas.py            # Pydantic schemas
│   ├── auth.py               # Auth utilities
│   └── database.py           # Database config
├── alembic/                   # Database migrations
│   └── versions/
├── static/                    # Frontend files
│   ├── login.html
│   └── dashboard.html
└── uploads/                   # Local storage (created automatically)
```

## 🧪 Development

### Running Tests
```bash
# Add tests to app/tests/ directory
pytest
```

### Code Quality
- Type hints throughout
- Follows FastAPI best practices
- Proper error handling and logging
- Scalable architecture

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For issues or questions, please create an issue in the repository.