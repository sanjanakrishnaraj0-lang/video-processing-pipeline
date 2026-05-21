# Video Processing Pipeline MVP

A minimal viable product for processing training videos, automatically extracting transcripts via audio and AI analysis of visual frames to detect skill gaps, missing steps, and generate MCQs.

## Architecture (Local MVP)
This version of the project is configured to run fully locally without needing an AWS account:
- **Frontend**: React (Vite) interface for uploading videos.
- **Backend**: FastAPI server that accepts multipart uploads and writes to a local `queue.json` file.
- **Worker**: A Python daemon (`local_consumer.py`) that polls the queue and runs the AI processing pipeline using `google-genai` and `ffmpeg`.

## Prerequisites
1. Python 3.10+
2. Node.js 18+
3. FFmpeg installed on the system (handled automatically by `imageio-ffmpeg` for Python).

## Deployment / How to Run

I have included a `start_all.bat` script in the root directory. To run the full stack:

1. Ensure your `worker/.env` file contains your `GEMINI_API_KEY`.
2. Double-click the `start_all.bat` file in your File Explorer, or run `.\start_all.bat` from your command prompt.

This script will automatically open 3 terminal windows and start:
- The FastAPI Backend on `http://localhost:8000`
- The Local AI Worker polling the queue
- The React Frontend on `http://localhost:5173`

To deploy this in a production environment (like AWS, Render, or Vercel), you would typically use Docker to containerize these three directories, or deploy the frontend to Vercel/Netlify, the backend to Render/AWS App Runner, and the worker as an AWS Lambda or ECS container interacting with SQS.
