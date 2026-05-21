import os
import json
import time
from process_video import process_local_video

QUEUE_FILE = "../queue.json"

def get_next_message():
    if not os.path.exists(QUEUE_FILE):
        return None
        
    try:
        with open(QUEUE_FILE, "r+") as f:
            # Request an exclusive lock (not strictly required for local MVP if single process, but good practice)
            content = f.read()
            if not content.strip():
                return None
                
            queue = json.loads(content)
            if not queue:
                return None
                
            # Get the first message
            msg = queue.pop(0)
            
            # Rewrite queue
            f.seek(0)
            f.truncate()
            json.dump(queue, f, indent=2)
            
            return msg
    except Exception as e:
        print(f"Error reading queue: {e}")
        return None

def start_polling():
    print(f"Starting local consumer polling {QUEUE_FILE}...")
    while True:
        msg = get_next_message()
        if msg:
            print(f"Received message: {msg}")
            video_id = msg.get("video_id")
            video_path = msg.get("video_path")
            
            if video_id and video_path:
                try:
                    result = process_local_video(video_path, video_id)
                    if result:
                        print(f"Successfully processed video {video_id}")
                except Exception as e:
                    print(f"Error processing video: {e}")
        else:
            time.sleep(3)

if __name__ == "__main__":
    start_polling()
