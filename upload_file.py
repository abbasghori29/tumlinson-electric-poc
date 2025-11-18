"""
Simple file upload script for Tumlinson API with WebSocket support
"""
import requests
import json
import urllib3
import asyncio
import websockets
import ssl
import time
from threading import Thread

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_URL = "http://51.20.87.226:8000"
USERNAME = "abbas@abbas.com"
PASSWORD = "abbas@"
FILE_PATH = r"C:\Users\Abbas-Work\Desktop\tumlinson_poc_v2\alembic.ini"
UPLOAD_FOLDER = "accepted_invites"  # Change this to your desired folder

def login():
    """Login and get access token"""
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        verify=False
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful!")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

async def websocket_listener(client_id):
    """Listen to WebSocket for real-time progress updates"""
    ws_url = f"ws://51.20.87.226:8000/ws/{client_id}"
    
    # No SSL needed for ws:// connections
    ssl_context = None
    
    try:
        print(f"\n🔌 Connecting to WebSocket...")
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected!")
            print("\n" + "=" * 60)
            print("📊 Upload Progress:")
            print("=" * 60)
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(message)
                    
                    if data.get('type') == 'progress':
                        progress = data.get('progress', 0)
                        msg = data.get('message', '')
                        bar_length = 40
                        filled = int(bar_length * progress / 100)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        print(f"\r[{bar}] {progress}% - {msg}", end='', flush=True)
                    
                    elif data.get('type') == 'complete':
                        print(f"\n\n✅ {data.get('message', 'Upload complete!')}")
                        break
                    
                    elif data.get('type') == 'error':
                        print(f"\n\n❌ {data.get('message', 'Upload error!')}")
                        break
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await websocket.send("ping")
                except Exception as e:
                    print(f"\n⚠️  WebSocket error: {e}")
                    break
    
    except Exception as e:
        print(f"\n⚠️  Failed to connect to WebSocket: {e}")

def upload_file(token, file_path, upload_folder, use_websocket=True):
    """Upload a single file with optional WebSocket progress"""
    print(f"\n📤 Uploading file: {file_path}")
    print(f"📁 Destination folder: {upload_folder}")
    
    # Generate client ID for WebSocket
    client_id = f"upload-{int(time.time() * 1000)}"
    
    # Start WebSocket listener in background if enabled
    ws_task = None
    if use_websocket:
        loop = asyncio.new_event_loop()
        def run_ws():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(websocket_listener(client_id))
        
        ws_thread = Thread(target=run_ws, daemon=True)
        ws_thread.start()
        time.sleep(1)  # Give WebSocket time to connect
    
    # Prepare the file
    with open(file_path, 'rb') as f:
        files = [('files', (file_path.split('\\')[-1], f, 'application/octet-stream'))]
        
        # Prepare form data
        data = {
            'paths': json.dumps([upload_folder]),
            'client_id': client_id if use_websocket else ''
        }
        
        # Upload
        response = requests.post(
            f"{BASE_URL}/api/upload-multiple",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            verify=False
        )
    
    # Wait for WebSocket to finish
    if use_websocket and ws_thread:
        ws_thread.join(timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        print("\n\n" + "=" * 60)
        print("✅ Upload API Response:")
        print(f"   Success: {result['success']} file(s)")
        print(f"   Failed: {result['failed']} file(s)")
        
        if result.get('results'):
            print("\n📋 Uploaded files:")
            for item in result['results']:
                # Handle different response formats
                file_name = item.get('file') or item.get('name', 'unknown')
                file_path = item.get('path', 'unknown')
                file_size = item.get('size', 0)
                print(f"   - {file_name} → {file_path} ({file_size} bytes)")
        
        if result.get('errors'):
            print("\n⚠️  Errors:")
            for error in result['errors']:
                if isinstance(error, dict):
                    print(f"   - {error.get('file', 'unknown')}: {error.get('error', 'unknown error')}")
                else:
                    print(f"   - {error}")
        
        return result
    else:
        print(f"\n❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def main():
    print("=" * 60)
    print("Tumlinson File Upload Script")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        return
    
    # Upload file
    result = upload_file(token, FILE_PATH, UPLOAD_FOLDER)
    
    print("\n" + "=" * 60)
    if result and result['success'] > 0:
        print("🎉 Upload completed successfully!")
    else:
        print("⚠️  Upload failed or completed with errors")
    print("=" * 60)

if __name__ == "__main__":
    main()

