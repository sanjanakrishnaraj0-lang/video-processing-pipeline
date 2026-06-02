import os
import json
import time
from process_video import process_local_video, process_video_pipeline
from agents.resume_agent import analyze_resume
from agents.report_agent import analyze_report

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
    while True:
        msg = get_next_message()
        if msg:
            print(f"\n[Worker] Received job: {msg}")
            job_id          = msg.get("video_id") or msg.get("job_id")
            agent_type      = msg.get("agent_type", "video")
            format_id       = msg.get("format_id", "")
            golden_standard = msg.get("golden_standard")
            file_path       = msg.get("file_path") or msg.get("video_path")
            video_url       = msg.get("video_url")

            if not job_id:
                print("[Worker] No job_id in message, skipping.")
                continue

            try:
                if agent_type == "resume":
                    print(f"[Worker] -> ResumeAgent processing job {job_id}")
                    analyze_resume(file_path, job_id, format_id or "resume_standard")

                elif agent_type == "report":
                    print(f"[Worker] -> ReportAgent processing job {job_id}")
                    analyze_report(file_path, job_id, format_id or "report_summary")

                else:  # default: video
                    print(f"[Worker] -> VideoAgent processing job {job_id}")
                    if video_url:
                        process_video_pipeline(video_url, job_id, format_id or "video_training_default", golden_standard)
                    elif file_path:
                        process_local_video(file_path, job_id, format_id or "video_training_default", golden_standard)
                    else:
                        print("[Worker] No video source provided.")

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
