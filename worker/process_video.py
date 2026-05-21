import os
import json
import time
import requests
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai
import imageio_ffmpeg
from typing import List
import concurrent.futures

# Load environment variables
load_dotenv()

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
    # Clear directory if it exists
    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))
    
    # FFmpeg command to extract 1 frame every 3 seconds as per best practices
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y", "-i", video_path, 
        "-vf", "fps=1/3", 
        os.path.join(output_dir, "output_%04d.jpg")
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Frames extracted.")

def extract_audio(video_path: str, output_path: str):
    print("Extracting audio...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-q:a", "0", "-map", "a", output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("Audio extracted.")

def upload_to_gemini(path: str, mime_type: str=None):
    print(f"Uploading {path} to Gemini...")
    file = genai.upload_file(path, mime_type=mime_type)
    return file

def analyze_with_ai(audio_path: str, frames_dir: str, result_path: str = "result.json"):
    print("Uploading audio to Gemini...")
    audio_file = upload_to_gemini(audio_path)
    
    print("Uploading frames to Gemini...")
    # Sort frames to maintain order
    frame_paths = sorted([os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.endswith('.jpg')])
    
    frame_files = []
    # Upload frames in parallel to save time
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(upload_to_gemini, fp, "image/jpeg") for fp in frame_paths]
        for future in concurrent.futures.as_completed(futures):
            try:
                frame_files.append(future.result())
            except Exception as e:
                print(f"Error uploading frame: {e}")
                
    # Sort frame files by name to ensure correct chronological order
    frame_files = sorted(frame_files, key=lambda f: f.display_name if f.display_name else f.name)
        
    print("Waiting for audio file to be processed by Gemini...")
    # Wait for the audio file to be ready
    while audio_file.state.name == 'PROCESSING':
        print('.', end='', flush=True)
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)
    print()

    print("Analyzing with Gemini Flash...")
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = """
    Analyze this worker training session using the provided audio and frames.
    
    Based on the visual evidence in the frames and the spoken instructions/context in the audio, please find:
    1. Skill gaps or mistakes made
    2. Safety violations (e.g. missing gloves, improper tools)
    3. Missing steps in the procedure
    4. Generate 2 Multiple Choice Questions (MCQs) to test the viewer's understanding.
    
    Output the result as a strict JSON object with this exact structure:
    {
      "skill_score": 85,
      "missing_steps": ["list of missing steps"],
      "safety_violations": ["list of safety violations"],
      "mcqs": [
        {
          "question": "Question text?",
          "options": ["A", "B", "C", "D"],
          "answer": "Correct option"
        }
      ]
    }
    
    Ensure the response contains ONLY the valid JSON block without markdown formatting or extra text.
    """
    
    # Combine prompt, audio, and frames
    contents = [prompt, audio_file] + frame_files
    
    response = model.generate_content(contents)
    
    result_text = response.text.strip()
    # Strip markdown if present
    if result_text.startswith("```json"):
        result_text = result_text[7:-3]
    elif result_text.startswith("```"):
        result_text = result_text[3:-3]
        
    result_text = result_text.strip()
    
    try:
        data = json.loads(result_text)
        with open(result_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Analysis complete. Results saved to {result_path}.")
        print(json.dumps(data, indent=2))
        return data
    except json.JSONDecodeError:
        print("Failed to parse JSON. Raw output:")
        print(result_text)
        with open("result_raw.txt", "w") as f:
            f.write(result_text)
        return None

def process_video_pipeline(video_url: str, video_id: str):
    video_path = f"downloads/video_{video_id}.mp4"
    audio_path = f"downloads/audio_{video_id}.mp3"
    frames_dir = f"frames/{video_id}"
    result_path = f"result_{video_id}.json"
    
    os.makedirs(frames_dir, exist_ok=True)
    
    download_video(video_url, video_path)
    extract_audio(video_path, audio_path)
    extract_frames(video_path, frames_dir)
    return analyze_with_ai(audio_path, frames_dir, result_path)

def process_local_video(video_path: str, video_id: str):
    audio_path = f"downloads/audio_{video_id}.mp3"
    frames_dir = f"frames/{video_id}"
    result_path = f"result_{video_id}.json"
    
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    
    print(f"Processing local video: {video_path}")
    extract_audio(video_path, audio_path)
    extract_frames(video_path, frames_dir)
    return analyze_with_ai(audio_path, frames_dir, result_path)
