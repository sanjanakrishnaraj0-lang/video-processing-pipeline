@echo off
echo Starting Video Processing Pipeline (Local Mode)

echo 1. Starting FastAPI Backend...
start cmd /k "cd backend && .\venv\Scripts\uvicorn main:app --reload --port 8001"

echo 2. Starting Local Worker...
start cmd /k "cd worker && .\venv\Scripts\python local_consumer.py"

echo 3. Starting React Frontend...
start cmd /k "cd frontend && npm run dev"

echo All services are starting up! 
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8001
