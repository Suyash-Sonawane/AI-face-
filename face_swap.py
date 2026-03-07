"""
Face Swap Module for SadTalker - CPU Only Version
Uses MediaPipe for face detection and OpenCV for face swapping
No compilation required - works on CPU
"""

import os
import cv2
import numpy as np
import imageio
import imageio_ffmpeg
from tqdm import tqdm
import uuid
import threading
import mediapipe as mp
from skimage import transform as sktransform

# MediaPipe face detection
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

# Global variables for model caching
face_detector = None
face_mesh = None
model_lock = threading.Lock()

def get_face_detector():
    """Get or create face detector"""
    global face_detector
    if face_detector is None:
        with model_lock:
            if face_detector is None:
                print("[Face Swap] Loading face detector...")
                face_detector = mp_face_detection.FaceDetection(
                    model_selection=1,  # 0=short range, 1=full range
                    min_detection_confidence=0.5
                )
                print("[Face Swap] Face detector loaded!")
    return face_detector

def get_face_mesh():
    """Get or create face mesh for landmarks"""
    global face_mesh
    if face_mesh is None:
        with model_lock:
            if face_mesh is None:
                print("[Face Swap] Loading face mesh...")
                face_mesh = mp_face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                print("[Face Swap] Face mesh loaded!")
    return face_mesh

def get_face_landmarks(image, face_mesh_detector):
    """Get face landmarks using MediaPipe"""
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh_detector.process(rgb_image)
    
    if not results.multi_face_landmarks:
        return None
    
    landmarks = []
    for landmark in results.multi_face_landmarks[0].landmark:
        h, w = image.shape[:2]
        x, y = int(landmark.x * w), int(landmark.y * h)
        landmarks.append((x, y))
    
    return np.array(landmarks)

def get_face_bbox(image, face_detector):
    """Get face bounding box"""
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_detector.process(rgb_image)
    
    if not results.detections:
        return None
    
    h, w = image.shape[:2]
    detection = results.detections[0]
    bbox = detection.location_data.relative_bounding_box
    
    x = int(bbox.xmin * w)
    y = int(bbox.ymin * h)
    width = int(bbox.width * w)
    height = int(bbox.height * h)
    
    return (x, y, width, height)

def warp_face(source_face, target_face, source_landmarks, target_landmarks):
    """Warp source face to match target face landmarks using Delaunay triangulation"""
    if source_landmarks is None or target_landmarks is None:
        return source_face
    
    # Use a subset of landmarks for triangulation (face outline + key features)
    key_points = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                  33, 37, 40, 46, 52, 55, 61, 64, 70, 73, 76, 85, 88, 91, 94, 97, 100, 103, 106, 109, 112,
                  133, 136, 139, 148, 151, 154, 157, 160, 163, 166, 169, 172, 175, 178, 181, 184, 187, 190, 193, 196,
                  263, 266, 269, 276, 282, 285, 291, 294, 300, 303, 306, 315, 318, 321, 324, 327, 330, 333, 336, 339, 342,
                  362, 365, 368, 377, 380, 383, 386, 389, 392, 395, 398, 401, 404, 407, 410, 413, 416, 419, 422, 425]
    
    try:
        src_pts = np.float32([source_landmarks[i] for i in key_points if i < len(source_landmarks)])
        tgt_pts = np.float32([target_landmarks[i] for i in key_points if i < len(target_landmarks)])
        
        # Estimate transformation
        transformation = sktransform.estimate_transform('similarity', src_pts, tgt_pts)
        
        # Warp source face
        warped = sktransform.warp(source_face, transformation.inverse, output_shape=target_face.shape[:2])
        warped = (warped * 255).astype(np.uint8)
        
        return warped
    except Exception as e:
        print(f"[Face Swap] Warp error: {e}")
        return source_face

def blend_faces(source_face, target_face, mask):
    """Blend source face onto target using seamless cloning"""
    try:
        # Create center point for seamless cloning
        h, w = target_face.shape[:2]
        center = (w // 2, h // 2)
        
        # Seamless clone
        blended = cv2.seamlessClone(
            source_face.astype(np.uint8),
            target_face.astype(np.uint8),
            mask.astype(np.uint8),
            center,
            cv2.NORMAL_CLONE
        )
        return blended
    except Exception as e:
        print(f"[Face Swap] Blend error: {e}")
        # Fallback to simple alpha blending
        alpha = 0.8
        return cv2.addWeighted(source_face, alpha, target_face, 1 - alpha, 0)

def create_face_mask(image, landmarks):
    """Create a mask for the face region"""
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    if landmarks is None or len(landmarks) == 0:
        return mask
    
    # Create convex hull of face landmarks
    hull = cv2.convexHull(landmarks.astype(np.float32))
    cv2.fillConvexPoly(mask, hull.astype(np.int32), 255)
    
    # Feather the edges
    kernel = np.ones((15, 15), np.uint8)
    mask = cv2.GaussianBlur(mask, (31, 31), 0)
    
    return mask

def simple_face_swap(source_img, target_img, detector, mesh_detector):
    """Simple face swap using landmark warping and blending"""
    # Get landmarks
    source_landmarks = get_face_landmarks(source_img, mesh_detector)
    target_landmarks = get_face_landmarks(target_img, mesh_detector)
    
    if source_landmarks is None or target_landmarks is None:
        print("[Face Swap] No face detected")
        return target_img
    
    # Get face bounding boxes
    source_bbox = get_face_bbox(source_img, detector)
    target_bbox = get_face_bbox(target_img, detector)
    
    if source_bbox is None or target_bbox is None:
        return target_img
    
    # Extract source face
    sx, sy, sw, sh = source_bbox
    source_face = source_img[sy:sy+sh, sx:sx+sw]
    
    # Resize source face to match target
    tx, ty, tw, th = target_bbox
    source_face_resized = cv2.resize(source_face, (tw, th))
    
    # Create mask for blending
    mask = np.zeros_like(target_img)
    mask_landmarks = target_landmarks.copy()
    mask_landmarks[:, 0] = mask_landmarks[:, 0] - tx
    mask_landmarks[:, 1] = mask_landmarks[:, 1] - ty
    face_mask = create_face_mask(source_face_resized, mask_landmarks)
    
    # Apply mask to all channels
    mask_3channel = cv2.cvtColor(face_mask, cv2.COLOR_GRAY2BGR) / 255.0
    
    # Blend faces
    target_face_region = target_img[ty:ty+th, tx:tx+tw].copy()
    
    # Simple alpha blending
    blended_face = (source_face_resized * mask_3channel + target_face_region * (1 - mask_3channel)).astype(np.uint8)
    
    # Place back
    result = target_img.copy()
    result[ty:ty+th, tx:tx+tw] = blended_face
    
    # Color correction (match histograms)
    result = match_color_histogram(result, target_img, mask_3channel)
    
    return result

def match_color_histogram(source, target, mask):
    """Match color histogram of source to target"""
    result = source.copy()
    
    for i in range(3):  # BGR channels
        source_hist = cv2.calcHist([source], [i], None, [256], [0, 256])
        target_hist = cv2.calcHist([target], [i], None, [256], [0, 256])
        
        # Calculate CDF
        source_cdf = source_hist.cumsum()
        target_cdf = target_hist.cumsum()
        
        # Normalize
        source_cdf = (source_cdf / source_cdf[-1]) * 255
        target_cdf = (target_cdf / target_cdf[-1]) * 255
        
        # Create lookup table
        lookup = np.interp(source_cdf, target_cdf, np.arange(256))
        
        # Apply only to face region
        channel = source[:, :, i]
        result[:, :, i] = np.take(lookup.astype(np.uint8), channel)
    
    # Blend with original to preserve background
    result = (result * mask + source * (1 - mask)).astype(np.uint8)
    
    return result

def process_video(source_img_path, target_video_path, output_path, progress_callback=None):
    """
    Process video face swap
    """
    try:
        # Load models
        detector = get_face_detector()
        mesh_detector = get_face_mesh()
        
        if detector is None or mesh_detector is None:
            print("[Face Swap] Failed to load models")
            return False
        
        # Load source image
        source_img = cv2.imread(source_img_path)
        if source_img is None:
            print("[Face Swap] Could not load source image")
            return False
        
        # Verify source face
        source_bbox = get_face_bbox(source_img, detector)
        if source_bbox is None:
            print("[Face Swap] No face detected in source image")
            return False
        
        print("[Face Swap] Source face detected")
        
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
            
            # Detect face in target
            target_bbox = get_face_bbox(frame_bgr, detector)
            
            if target_bbox is not None:
                # Perform face swap
                result_frame = simple_face_swap(source_img, frame_bgr, detector, mesh_detector)
            else:
                result_frame = frame_bgr
            
            # Convert BGR back to RGB for video writer
            result_rgb = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
            writer.append_data(result_rgb)
            
            processed += 1
            progress = int((processed / total_frames) * 100)
            
            if progress_callback and processed % 5 == 0:
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
    """Process single image face swap"""
    try:
        # Load models
        detector = get_face_detector()
        mesh_detector = get_face_mesh()
        
        if detector is None or mesh_detector is None:
            return False
        
        # Load images
        source_img = cv2.imread(source_img_path)
        target_img = cv2.imread(target_img_path)
        
        if source_img is None or target_img is None:
            print("[Face Swap] Could not load images")
            return False
        
        # Perform face swap
        result = simple_face_swap(source_img, target_img, detector, mesh_detector)
        
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
        self.status = "pending"
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
    """Start face swap processing in background"""
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    def on_update(data):
        if task_id in active_workers:
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
    print("Face Swap Module (CPU Only) - Test Mode")
