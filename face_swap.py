"""
Face Swap Module for SadTalker
Implements video face swapping using InsightFace and ONNX Runtime
Based on the HuggingFace space: tonyassi/video-face-swap
"""

import os
import cv2
import numpy as np
import onnxruntime as ort
import insightface
from insightface.app import FaceAnalysis
import imageio
import imageio_ffmpeg
from tqdm import tqdm
import uuid
import threading
import shutil

# Global variables for model caching
face_analyser = None
face_swapper = None
model_lock = threading.Lock()

# Model paths
MODELS_DIR = "checkpoints/face_swap"
FACE_SWAPPER_MODEL = os.path.join(MODELS_DIR, "inswapper_128.onnx")

# Model download URLs
FACE_SWAPPER_URL = "https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx"

def ensure_model_exists():
    """Download face swap model if not exists"""
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    if not os.path.exists(FACE_SWAPPER_MODEL):
        print(f"[Face Swap] Downloading model to {FACE_SWAPPER_MODEL}...")
        import urllib.request
        try:
            urllib.request.urlretrieve(FACE_SWAPPER_URL, FACE_SWAPPER_MODEL)
            print("[Face Swap] Model downloaded successfully!")
        except Exception as e:
            print(f"[Face Swap] Error downloading model: {e}")
            return False
    return True

def get_face_analyser():
    """Get or create face analyser instance"""
    global face_analyser
    if face_analyser is None:
        with model_lock:
            if face_analyser is None:
                print("[Face Swap] Loading face analyser...")
                face_analyser = FaceAnalysis(name='buffalo_l', root=MODELS_DIR, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
                face_analyser.prepare(ctx_id=0, det_size=(640, 640))
                print("[Face Swap] Face analyser loaded!")
    return face_analyser

def get_face_swapper():
    """Get or create face swapper instance"""
    global face_swapper
    if face_swapper is None:
        with model_lock:
            if face_swapper is None:
                if not ensure_model_exists():
                    return None
                print("[Face Swap] Loading face swapper model...")
                face_swapper = insightface.model_zoo.get_model(FACE_SWAPPER_MODEL, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
                print("[Face Swap] Face swapper loaded!")
    return face_swapper

def get_face(img_data, face_analyser):
    """Get the main face from image data"""
    if isinstance(img_data, str):
        img = cv2.imread(img_data)
    else:
        img = img_data
    
    if img is None:
        return None
    
    faces = face_analyser.get(img)
    
    if len(faces) == 0:
        return None
    
    # Return the face with largest area
    return max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))

def swap_face(source_face, target_face, image, face_swapper):
    """Perform face swap on a single image"""
    if source_face is None or target_face is None or face_swapper is None:
        return image
    return face_swapper.get(image, target_face, source_face, paste_back=True)

def process_video(source_img_path, target_video_path, output_path, progress_callback=None):
    """
    Process video face swap
    
    Args:
        source_img_path: Path to source face image
        target_video_path: Path to target video
        output_path: Path for output video
        progress_callback: Function to call with progress updates (0-100)
    
    Returns:
        bool: Success status
    """
    try:
        # Load models
        analyser = get_face_analyser()
        swapper = get_face_swapper()
        
        if analyser is None or swapper is None:
            print("[Face Swap] Failed to load models")
            return False
        
        # Get source face
        source_face = get_face(source_img_path, analyser)
        if source_face is None:
            print("[Face Swap] No face detected in source image")
            return False
        
        print(f"[Face Swap] Source face detected: {source_face.bbox}")
        
        # Open target video
        reader = imageio.get_reader(target_video_path)
        fps = reader.get_meta_data().get('fps', 30)
        
        # Get video dimensions
        first_frame = reader.get_data(0)
        height, width = first_frame.shape[:2]
        
        print(f"[Face Swap] Video: {width}x{height} @ {fps}fps")
        
        # Create writer
        writer = imageio.get_writer(output_path, fps=fps, codec='libx264', quality=8)
        
        # Process frames
        total_frames = reader.count_frames()
        processed = 0
        
        for frame in reader:
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Get target face
            target_face = get_face(frame_bgr, analyser)
            
            if target_face is not None:
                # Swap face
                result_frame = swap_face(source_face, target_face, frame_bgr, swapper)
            else:
                result_frame = frame_bgr
            
            # Convert BGR back to RGB for video writer
            result_rgb = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
            writer.append_data(result_rgb)
            
            processed += 1
            progress = int((processed / total_frames) * 100)
            
            if progress_callback and processed % 5 == 0:  # Update every 5 frames
                progress_callback(progress)
            
            if processed % 30 == 0:
                print(f"[Face Swap] Progress: {progress}%")
        
        reader.close()
        writer.close()
        
        if progress_callback:
            progress_callback(100)
        
        print(f"[Face Swap] Complete! Output: {output_path}")
        return True
        
    except Exception as e:
        print(f"[Face Swap] Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return False

def process_image(source_img_path, target_img_path, output_path):
    """
    Process single image face swap
    
    Args:
        source_img_path: Path to source face image
        target_img_path: Path to target image
        output_path: Path for output image
    
    Returns:
        bool: Success status
    """
    try:
        # Load models
        analyser = get_face_analyser()
        swapper = get_face_swapper()
        
        if analyser is None or swapper is None:
            return False
        
        # Get faces
        source_face = get_face(source_img_path, analyser)
        target_face = get_face(target_img_path, analyser)
        
        if source_face is None:
            print("[Face Swap] No face detected in source image")
            return False
        
        if target_face is None:
            print("[Face Swap] No face detected in target image")
            return False
        
        # Load target image
        target_img = cv2.imread(target_img_path)
        
        # Swap face
        result = swap_face(source_face, target_face, target_img, swapper)
        
        # Save result
        cv2.imwrite(output_path, result)
        
        print(f"[Face Swap] Image saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"[Face Swap] Error processing image: {e}")
        import traceback
        traceback.print_exc()
        return False

class FaceSwapWorker(threading.Thread):
    """Background worker for face swap processing"""
    
    def __init__(self, source_img, target_video, output_path, callback=None):
        super().__init__()
        self.source_img = source_img
        self.target_video = target_video
        self.output_path = output_path
        self.callback = callback
        self.progress = 0
        self.status = "pending"  # pending, processing, completed, failed
        self.error_msg = ""
    
    def update_progress(self, value):
        self.progress = value
        if self.callback:
            self.callback({
                'status': self.status,
                'progress': self.progress,
                'error': self.error_msg
            })
    
    def run(self):
        self.status = "processing"
        self.update_progress(0)
        
        try:
            success = process_video(
                self.source_img,
                self.target_video,
                self.output_path,
                progress_callback=self.update_progress
            )
            
            if success:
                self.status = "completed"
                self.progress = 100
            else:
                self.status = "failed"
                self.error_msg = "Processing failed"
                
        except Exception as e:
            self.status = "failed"
            self.error_msg = str(e)
        
        self.update_progress(self.progress)

# Active workers dictionary
active_workers = {}

def start_face_swap(source_img, target_video, output_path, task_id=None):
    """
    Start face swap processing in background
    
    Returns:
        str: Task ID
    """
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    def on_update(data):
        active_workers[task_id].update(data)
    
    worker = FaceSwapWorker(source_img, target_video, output_path, callback=on_update)
    active_workers[task_id] = {
        'worker': worker,
        'status': 'pending',
        'progress': 0,
        'error': '',
        'output_path': output_path
    }
    
    worker.start()
    return task_id

def get_task_status(task_id):
    """Get status of a face swap task"""
    if task_id not in active_workers:
        return None
    
    worker_data = active_workers[task_id]
    return {
        'status': worker_data['worker'].status,
        'progress': worker_data['worker'].progress,
        'error': worker_data['worker'].error_msg,
        'output_path': worker_data['output_path']
    }

if __name__ == "__main__":
    # Test functionality
    print("Face Swap Module - Test Mode")
    ensure_model_exists()
