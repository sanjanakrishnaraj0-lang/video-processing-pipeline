import os
import json
import sys
from dotenv import load_dotenv
from process_video import process_video_pipeline

# Ensure we load the .env from parent directory if not present in current directory
load_dotenv()
load_dotenv("../.env")

def main():
    video_url = "https://lms-tutorials.s3.ap-south-1.amazonaws.com/plumbing/t1.mp4"
    video_id = "t1"
    
    print(f"Starting processing pipeline for URL: {video_url}")
    result = process_video_pipeline(video_url, video_id)
    
    if result:
        print("\n=== PIPELINE RUN SUCCESSFUL ===")
        print(json.dumps(result, indent=2))
        
        # Save results to a file for the user
        output_file = "../result_t1.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved results to {output_file}")
    else:
        print("\n=== PIPELINE RUN FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
