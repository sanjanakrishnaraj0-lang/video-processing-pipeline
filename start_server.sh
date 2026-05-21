#!/bin/bash
echo "Starting Video Processing Backend & Worker"

# Start the worker in the background
cd worker
python local_consumer.py &

# Start the FastAPI backend in the foreground
cd ../backend
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
