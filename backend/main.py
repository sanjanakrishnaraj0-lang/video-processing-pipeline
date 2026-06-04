import os
import sys
import uuid
import json
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# ── Add worker directory to path so format_manager is importable ───────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
from agents.format_manager import (
    get_all_formats,
    get_format_by_id,
    save_format,
    delete_format,
)

app = FastAPI(title="Kovon AI — Multi-Agent Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUEUE_FILE  = "../queue.json"
UPLOAD_DIR  = "../downloads"
WORKER_DIR  = "../worker"

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _append_to_queue(item: dict):
    queue = []
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                content = f.read()
                if content.strip():
                    queue = json.loads(content)
        except Exception:
            queue = []
    queue.append(item)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def _save_upload(file: UploadFile) -> str:
    """Save an uploaded file and return its path."""
    job_id    = str(uuid.uuid4())
    ext       = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'bin'
    filename  = f"upload_{job_id}.{ext}"
    dest_path = os.path.join(UPLOAD_DIR, filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return dest_path, job_id


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Kovon AI Multi-Agent API"}


# ─────────────────────────────────────────────────────────────────────────────
# Formats API
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/formats")
def list_formats():
    return {"formats": get_all_formats()}


@app.get("/formats/{format_id}")
def get_format(format_id: str):
    fmt = get_format_by_id(format_id)
    if not fmt:
        raise HTTPException(status_code=404, detail="Format not found")
    return fmt


@app.post("/formats")
def create_or_update_format(fmt: dict):
    saved = save_format(fmt)
    return {"status": "saved", "format": saved}


@app.delete("/formats/{format_id}")
def remove_format(format_id: str):
    ok = delete_format(format_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Format not found")
    return {"status": "deleted"}


# ─────────────────────────────────────────────────────────────────────────────
# Video Upload (existing + format_id support)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = "user_demo",
    format_id: str = "video_training_default",
    golden_standard: Optional[str] = Form(None)
):
    try:
        file_path, job_id = _save_upload(file)
        _append_to_queue({
            "job_id":           job_id,
            "video_id":         job_id,   # backward compat
            "video_path":       file_path,
            "user_id":          user_id,
            "original_filename": file.filename,
            "agent_type":       "video",
            "format_id":        format_id,
            "golden_standard":  golden_standard,
        })
        return {"status": "success", "job_id": job_id, "message": "Video uploaded and queued for analysis."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UrlUploadRequest(BaseModel):
    video_url: str
    user_id: str = "user_demo"
    format_id: str = "video_training_default"
    golden_standard: Optional[str] = None


@app.post("/upload-url")
async def upload_video_url(request: UrlUploadRequest):
    try:
        job_id = str(uuid.uuid4())
        _append_to_queue({
            "job_id":      job_id,
            "video_id":    job_id,
            "video_url":   request.video_url,
            "user_id":     request.user_id,
            "agent_type":  "video",
            "format_id":   request.format_id,
            "golden_standard": request.golden_standard,
        })
        return {"status": "success", "job_id": job_id, "message": "Video URL queued for analysis."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Resume Upload
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = "user_demo",
    format_id: str = "resume_standard"
):
    allowed_ext = {".pdf", ".docx", ".doc", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_ext}"
        )
    try:
        file_path, job_id = _save_upload(file)
        _append_to_queue({
            "job_id":            job_id,
            "file_path":         file_path,
            "user_id":           user_id,
            "original_filename": file.filename,
            "agent_type":        "resume",
            "format_id":         format_id,
        })
        return {"status": "success", "job_id": job_id, "message": "Resume uploaded and queued for analysis."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Report Upload
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload/report")
async def upload_report(
    file: UploadFile = File(...),
    user_id: str = "user_demo",
    format_id: str = "report_summary"
):
    allowed_ext = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".csv"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_ext}"
        )
    try:
        file_path, job_id = _save_upload(file)
        _append_to_queue({
            "job_id":            job_id,
            "file_path":         file_path,
            "user_id":           user_id,
            "original_filename": file.filename,
            "agent_type":        "report",
            "format_id":         format_id,
        })
        return {"status": "success", "job_id": job_id, "message": "Report uploaded and queued for analysis."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/generic")
async def upload_generic(
    file: UploadFile = File(...),
    user_id: str = "user_demo"
):
    allowed_ext = {
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
        ".pdf", ".docx", ".doc", ".txt",
        ".xlsx", ".xls", ".csv"
    }
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_ext}"
        )
    try:
        file_path, job_id = _save_upload(file)
        _append_to_queue({
            "job_id":            job_id,
            "video_id":          job_id,
            "video_path":        file_path,
            "file_path":         file_path,
            "user_id":           user_id,
            "original_filename": file.filename,
            "agent_type":        "generic",
            "format_id":         None
        })
        return {"status": "success", "job_id": job_id, "message": "File uploaded and queued for auto-detect analysis."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Unified Result Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    # Check worker dir first, then current dir
    for search_dir in [WORKER_DIR, "."]:
        result_path = os.path.join(search_dir, f"result_{job_id}.json")
        if os.path.exists(result_path):
            try:
                with open(result_path, "r") as f:
                    data = json.load(f)
                if data.get("status") == "failed":
                    return {"status": "error", "message": data.get("error", "Processing failed")}
                return {"status": "complete", "data": data}
            except Exception as e:
                return {"status": "error", "message": f"Error reading result: {str(e)}"}
    return {"status": "processing"}


# ─────────────────────────────────────────────────────────────────────────────
# Presigned URL stub (backward compat)
# ─────────────────────────────────────────────────────────────────────────────

class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    user_id: str = "user123"


@app.post("/generate-presigned-url")
async def generate_presigned_url(request: PresignedUrlRequest):
    return {
        "url": f"http://localhost:8001/upload?user_id={request.user_id}",
        "key": f"{request.user_id}/{request.filename}"
    }
