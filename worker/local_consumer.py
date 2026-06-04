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
                actual_agent_type = agent_type
                if agent_type == "generic":
                    print(f"[Worker] -> Job is generic, running classification first for job {job_id}")
                    classification_res = runner.run_workflow("generic", msg)
                    actual_agent_type = classification_res.get("classification", "other")
                    print(f"[Worker] -> Classification result: '{actual_agent_type}'")
                    msg["agent_type"] = actual_agent_type

                if actual_agent_type == "other":
                    result_path = f"result_{job_id}.json"
                    data = {
                        "status": "failed",
                        "detected_agent_type": "other",
                        "error": "The uploaded document type could not be recognized as a valid video, resume, or report."
                    }
                    with open(result_path, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"[Worker] [UNSUPPORTED] Job {job_id} is unsupported format.")
                else:
                    print(f"[Worker] -> Running dynamic JSON workflow: '{actual_agent_type}' for job {job_id}")
                    runner.run_workflow(actual_agent_type, msg)
                    
                    # Ensure detected_agent_type is written into the result JSON
                    result_path = f"result_{job_id}.json"
                    if os.path.exists(result_path):
                        try:
                            with open(result_path, "r") as f:
                                res_data = json.load(f)
                            res_data["detected_agent_type"] = actual_agent_type
                            with open(result_path, "w") as f:
                                json.dump(res_data, f, indent=2)
                        except Exception as write_err:
                            print(f"[Worker] Warning: could not inject detected_agent_type: {write_err}")

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

