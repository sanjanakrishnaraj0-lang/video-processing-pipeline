import os
import json
import time
from workflow_runner import WorkflowRunner

QUEUE_FILE = "../queue.json"


def get_next_message():
    if not os.path.exists(QUEUE_FILE):
        return None
    try:
        with open(QUEUE_FILE, "r+") as f:
            content = f.read()
            if not content.strip():
                return None
            queue = json.loads(content)
            if not queue:
                return None
            msg = queue.pop(0)
            f.seek(0)
            f.truncate()
            json.dump(queue, f, indent=2)
            return msg
    except Exception as e:
        print(f"Error reading queue: {e}")
        return None


def start_polling():
    print(f"Starting local consumer polling {QUEUE_FILE}...")
    runner = WorkflowRunner()
    
    while True:
        msg = get_next_message()
        if msg:
            print(f"\n[Worker] Received job: {msg}")
            job_id          = msg.get("video_id") or msg.get("job_id")
            agent_type      = msg.get("agent_type", "video")

            if not job_id:
                print("[Worker] No job_id in message, skipping.")
                continue

            try:
                print(f"[Worker] -> Running dynamic JSON workflow: '{agent_type}' for job {job_id}")
                runner.run_workflow(agent_type, msg)
                print(f"[Worker] [SUCCESS] Job {job_id} complete.")

            except Exception as e:
                print(f"[Worker] [ERROR] Error processing job {job_id}: {e}")
                # Write error result so frontend stops polling
                result_path = f"result_{job_id}.json"
                with open(result_path, "w") as f:
                    json.dump({"error": str(e), "status": "failed"}, f)
        else:
            time.sleep(3)


if __name__ == "__main__":
    start_polling()

