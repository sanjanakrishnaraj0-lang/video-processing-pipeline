import os
import json
import time
import boto3
from dotenv import load_dotenv
from process_video import process_video_pipeline

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
QUEUE_URL = os.getenv("QUEUE_URL")

if not QUEUE_URL:
    print("Warning: QUEUE_URL not set in environment.")

sqs = boto3.client('sqs', region_name=AWS_REGION)
s3 = boto3.client('s3', region_name=AWS_REGION)

def process_message(msg):
    try:
        body = json.loads(msg["Body"])
        
        # Handle S3 Event Notification format
        if "Records" in body:
            record = body["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
        else:
            # Handle custom format specified in prompt
            bucket = body.get("bucket")
            key = body.get("key")
            
        if not bucket or not key:
            print("Invalid message format, skipping.")
            return False
            
        print(f"Processing video from s3://{bucket}/{key}")
        
        video_id = key.split("/")[-1].split(".")[0]
        
        # Generate a short-lived presigned URL so process_video can download it
        # (Alternatively, we could download directly using boto3, but process_video already expects a URL)
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600
        )
        
        # Run the AI pipeline
        result = process_video_pipeline(presigned_url, video_id)
        
        if result:
            print(f"Successfully processed {key}")
            # Optionally, save result to PostgreSQL here
            return True
        else:
            print(f"Failed to process {key} with AI pipeline")
            return False
            
    except Exception as e:
        print(f"Error processing message: {e}")
        return False

def start_polling():
    print(f"Starting SQS consumer for queue: {QUEUE_URL}")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10 # Long polling
            )
            
            messages = response.get("Messages", [])
            
            for msg in messages:
                print("Received message, starting processing...")
                success = process_message(msg)
                
                # If processed successfully or invalid format (don't retry), delete from queue
                if success:
                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"]
                    )
                    print("Message deleted from queue.")
                    
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if QUEUE_URL:
        start_polling()
    else:
        print("Set QUEUE_URL to start polling.")
