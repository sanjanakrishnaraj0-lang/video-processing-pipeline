import os
import uuid
import json
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Video Processing API (Local)")

# Allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUEUE_FILE = "../queue.json"
UPLOAD_DIR = "../downloads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    user_id: str = "user123"

# Keep the presigned URL endpoint for backward compatibility (simulates S3)
@app.post("/generate-presigned-url")
async def generate_presigned_url(request: PresignedUrlRequest):
    return {
        "url": f"http://localhost:8000/upload?user_id={request.user_id}", 
        "key": f"{request.user_id}/{request.filename}"
    }

# New direct upload endpoint for local bypassing of S3
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = "user123"):
    try:
        video_id = str(uuid.uuid4())
        extension = file.filename.split('.')[-1] if '.' in file.filename else 'mp4'
        video_filename = f"video_{video_id}.{extension}"
        video_path = os.path.join(UPLOAD_DIR, video_filename)
        
        # Save file to local disk
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Add to local queue
        queue = []
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, "r") as f:
                    content = f.read()
                    if content.strip():
                        queue = json.loads(content)
            except Exception:
                queue = []
                
        queue.append({
            "video_id": video_id,
            "video_path": video_path,
            "user_id": user_id,
            "original_filename": file.filename
        })
        
        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=2)
            
        return {"status": "success", "video_id": video_id, "message": "File uploaded and queued for processing."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Video Processing Backend (Local)"}

@app.get("/result/{video_id}")
async def get_result(video_id: str):
    result_path = os.path.join("..", "worker", f"result_{video_id}.json")
    if os.path.exists(result_path):
        try:
            with open(result_path, "r") as f:
                data = json.load(f)
            return {"status": "complete", "data": data}
        except Exception as e:
            return {"status": "error", "message": f"Error reading result: {str(e)}"}
    else:
        return {"status": "processing"}
