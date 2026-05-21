#!/bin/bash
echo "Starting Video Processing Backend & Worker"

# Start the worker in the background
cd /app/worker
python local_consumer.py &

# Start the FastAPI backend in the foreground
cd /app/backend
# Bind to 0.0.0.0 so the cloud platform can route traffic to it
uvicorn main:app --host 0.0.0.0 --port 8000
