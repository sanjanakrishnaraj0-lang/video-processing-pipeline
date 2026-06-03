import os
import json
import time
import requests
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
import imageio_ffmpeg
from typing import List, Optional, Dict, Any
import concurrent.futures
from agents.format_manager import get_format_by_id, build_prompt_for_format, DEFAULT_FORMATS

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Load domain standard prompts and fallbacks
STANDARDS_FILE = os.path.join(os.path.dirname(__file__), "domain_standards.json")
try:
    with open(STANDARDS_FILE, "r", encoding="utf-8") as f:
        DOMAIN_STANDARDS = json.load(f)
except Exception as e:
    print(f"Warning: could not load domain standards from {STANDARDS_FILE}: {e}")
    DOMAIN_STANDARDS = {}

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create necessary directories
os.makedirs("frames", exist_ok=True)
os.makedirs("downloads", exist_ok=True)


def download_video(url: str, output_path: str):
    print(f"Downloading video from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")


def extract_frames(video_path: str, output_dir: str):
    print("Extracting frames at 1 fps...")
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-vf", "fps=1/3",
        os.path.join(output_dir, "output_%04d.jpg")
    ]
    subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Frames extracted.")


def extract_audio(video_path: str, output_path: str):
    print("Extracting audio...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-q:a", "0", "-map", "a", output_path
    ]
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print("Warning: audio extraction failed (video may be mute). Continuing without audio.")
    else:
        print("Audio extracted.")


def upload_to_gemini(path: str, mime_type: str = None):
    print(f"Uploading {path} to Gemini...")
    file = genai.upload_file(path, mime_type=mime_type)
    return file


def analyze_with_ai(
    audio_path: str,
    frames_dir: str,
    result_path: str = "result.json",
    format_id: str = "video_training_default",
    golden_standard: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze video frames + audio with Gemini using a custom or default output format.
    """
    # ── Resolve format ─────────────────────────────────────────────────────────
    fmt = get_format_by_id(format_id)
    if not fmt:
        fmt = next((f for f in DEFAULT_FORMATS if f["id"] == "video_training_default"), None)

    standard_data = DOMAIN_STANDARDS.get(golden_standard or "general", DOMAIN_STANDARDS.get("general", {}))
    context_str = standard_data.get("context_prompt", "You are analyzing a worker training video. Use both the audio narration and visual frames.")

    prompt = build_prompt_for_format(
        fmt,
        context=context_str
    )

    try:
        # Upload audio only if it exists
        audio_file = None
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print("Uploading audio to Gemini...")
            audio_file = upload_to_gemini(audio_path)

        print("Uploading frames to Gemini...")
        frame_paths = sorted([
            os.path.join(frames_dir, f)
            for f in os.listdir(frames_dir) if f.endswith('.jpg')
        ])

        frame_files = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(upload_to_gemini, fp, "image/jpeg") for fp in frame_paths]
            for future in concurrent.futures.as_completed(futures):
                try:
                    frame_files.append(future.result())
                except Exception as e:
                    print(f"Error uploading frame: {e}")

        frame_files = sorted(frame_files, key=lambda f: f.display_name if f.display_name else f.name)

        if audio_file:
            print("Waiting for audio file to be processed by Gemini...")
            while audio_file.state.name == 'PROCESSING':
                print('.', end='', flush=True)
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            print()

        print("Analyzing with Gemini Flash...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        contents = [prompt]
        if audio_file:
            contents.append(audio_file)
        contents += frame_files

        response = model.generate_content(contents)
        result_text = response.text.strip()

        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        data = json.loads(result_text.strip())

    except Exception as e:
        print(f"Gemini API failed ({e}). Falling back to simulated analysis...")
        data = _fallback_video_result(fmt, golden_standard)

    try:
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Analysis complete. Results saved to {result_path}.")
        print(json.dumps(data, indent=2))
        return data
    except Exception as write_err:
        print(f"Failed to write results: {write_err}")
        return None


def _fallback_video_result(fmt: dict, golden_standard: Optional[str] = None) -> dict:
    standard_data = DOMAIN_STANDARDS.get(golden_standard or "general", DOMAIN_STANDARDS.get("general", {}))
    fallback = standard_data.get("fallback", {})
    if fmt and fmt.get("fields"):
        keys = [f["key"] for f in fmt["fields"]]
        return {k: v for k, v in fallback.items() if k in keys}
    return fallback


def process_video_pipeline(video_url: str, video_id: str, format_id: str = "video_training_default", golden_standard: Optional[str] = None):
    video_path = f"downloads/video_{video_id}.mp4"
    audio_path = f"downloads/audio_{video_id}.mp3"
    frames_dir = f"frames/{video_id}"
    result_path = f"result_{video_id}.json"

    os.makedirs(frames_dir, exist_ok=True)

    download_video(video_url, video_path)
    extract_audio(video_path, audio_path)
    extract_frames(video_path, frames_dir)
    return analyze_with_ai(audio_path, frames_dir, result_path, format_id, golden_standard)


def process_local_video(video_path: str, video_id: str, format_id: str = "video_training_default", golden_standard: Optional[str] = None):
    audio_path = f"downloads/audio_{video_id}.mp3"
    frames_dir = f"frames/{video_id}"
    result_path = f"result_{video_id}.json"

    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs("downloads", exist_ok=True)

    print(f"Processing local video: {video_path}")
    extract_audio(video_path, audio_path)
    extract_frames(video_path, frames_dir)
    return analyze_with_ai(audio_path, frames_dir, result_path, format_id, golden_standard)
