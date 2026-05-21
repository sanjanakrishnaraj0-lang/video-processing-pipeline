FROM python:3.10-slim

# Install system dependencies (ffmpeg is needed for video processing)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files first
COPY backend/requirements.txt /app/backend/requirements.txt
COPY worker/requirements.txt /app/worker/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir -r worker/requirements.txt

# Copy all project files
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/downloads /app/frames /app/worker/frames

# Make the start script executable
RUN chmod +x /app/start_server.sh

# Expose the FastAPI port
EXPOSE 8000

# Start both processes
CMD ["/app/start_server.sh"]
