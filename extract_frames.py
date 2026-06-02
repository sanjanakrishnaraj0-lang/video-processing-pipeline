import os
import cv2

SUPPORTED_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

def extract_frames_from_video(video_path, output_dir, interval=30):
    print(f"Processing video: {video_path}...")
    cap = cv2.VideoCapture(video_path)
    count = 0
    extracted_count = 0
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            frame_name = os.path.join(output_dir, f"{base_name}_frame_{count}.jpg")
            cv2.imwrite(frame_name, frame)
            extracted_count += 1
        count += 1
        
    cap.release()
    print(f"Extracted {extracted_count} frames from {os.path.basename(video_path)}.")
    return extracted_count

def clear_folder_images(directory_path):
    print(f"Cleaning existing images in {directory_path}...")
    if os.path.exists(directory_path):
        for file in os.listdir(directory_path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                try:
                    os.remove(os.path.join(directory_path, file))
                except Exception as e:
                    print(f"Error removing {file}: {e}")

def process_folder(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        return
        
    clear_folder_images(directory_path)
    
    video_found = False
    for file in os.listdir(directory_path):
        if file.lower().endswith(SUPPORTED_EXTENSIONS):
            video_found = True
            video_path = os.path.join(directory_path, file)
            extract_frames_from_video(video_path, directory_path)
            
    if not video_found:
        print(f"No video files found in {directory_path}.")

def main():
    print("=== Scanning Golden Dataset Folders ===")
    
    # Process good folder
    print("\n[Good Folder]")
    process_folder("golden_dataset/good")
    
    # Process bad folder
    print("\n[Bad Folder]")
    process_folder("golden_dataset/bad")
    
    print("\n=== Processing Complete ===")

if __name__ == "__main__":
    main()