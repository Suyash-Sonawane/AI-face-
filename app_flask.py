"""
SadTalker Flask Application
Main application entry point with database-backed authentication and video processing
"""

import os
import shutil
import subprocess
import threading
import uuid
import json
import time
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename
from src.gradio_demo import SadTalker
from flask_cors import CORS
from datetime import datetime

# Import our new modules
from database import init_database, migrate_database, create_video_project, update_video_progress, complete_video_project, fail_video_project
from api_routes import api_bp

# Performance optimizations for PyTorch
import torch
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Flask app configuration
app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))
app.secret_key = os.urandom(24)
CORS(app)

# Register API blueprint
app.register_blueprint(api_bp)

# Directory configuration
UPLOAD_DIR = "uploads"
AVATAR_DIR = "uploads/avatars"
RESULT_DIR = "static/results"
PREVIEW_DIR = "static/previews"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# Serve avatar files
@app.route('/uploads/avatars/<path:filename>')
def serve_avatar(filename):
    """Serve avatar images"""
    return send_from_directory(AVATAR_DIR, filename)

# Initialize SadTalker once when the app starts (lazy loading for faster startup)
sadtalker = None

def load_sadtalker_model():
    """Load SadTalker model on first use for faster startup"""
    global sadtalker
    if sadtalker is None:
        print("[INIT] Loading SadTalker model (first use)...")
        try:
            sadtalker = SadTalker("checkpoints", "src/config", lazy_load=True)
            print("[INIT] SadTalker model loaded successfully!")
        except Exception as e:
            print(f"[INIT ERROR] Failed to load SadTalker: {e}")
            sadtalker = None
    return sadtalker

# Global dictionary to store processing status
processing_status = {}

# ==================== VIDEO GENERATION ====================

def generate_video_background(img_path, aud_path, preprocess, still_mode, use_enhancer, 
                               batch_size, size, pose_style, exp_scale, use_ref_video, 
                               ref_vid_path, ref_info, use_idle_mode, length_of_audio, 
                               use_blink, final_name, user_id=None, settings=None, use_video_source=False):
    """Background thread for video generation with comprehensive logging"""
    
    stop_event = threading.Event()
    start_time = time.time()
    
    print(f"\n{'='*70}")
    print(f"[VIDEO GENERATION STARTED]")
    print(f"{'='*70}")
    print(f"[INFO] Video ID: {final_name}")
    print(f"[INFO] User ID: {user_id}")
    print(f"[INFO] Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"[INPUT] Source: {img_path}")
    print(f"[INPUT] Source Type: {'Video' if use_video_source else 'Image'}")
    print(f"[INPUT] Audio File: {aud_path}")
    print(f"[INPUT] Reference Video: {ref_vid_path if use_ref_video else 'None'}")
    print(f"{'='*70}")
    print(f"[SETTINGS] Preprocess: {preprocess}")
    print(f"[SETTINGS] Still Mode: {still_mode}")
    print(f"[SETTINGS] Enhancer: {use_enhancer}")
    print(f"[SETTINGS] Batch Size: {batch_size}")
    print(f"[SETTINGS] Size: {size}px")
    print(f"[SETTINGS] Pose Style: {pose_style}")
    print(f"[SETTINGS] Expression Scale: {exp_scale}")
    print(f"[SETTINGS] Idle Mode: {use_idle_mode}")
    print(f"[SETTINGS] Blink: {use_blink}")
    print(f"[SETTINGS] Reference Video Enabled: {use_ref_video}")
    if use_ref_video:
        print(f"[SETTINGS] Reference Info: {ref_info}")
    print(f"{'='*70}")

    def progress_simulator():
        """Simulate progress updates while processing"""
        current_progress = 0
        stage_messages = {
            0: "Initializing AI models...",
            15: "Loading face detection models...",
            25: "Preprocessing source image...",
            35: "Extracting facial landmarks...",
            45: "Generating face animation...",
            60: "Synthesizing lip movements...",
            75: "Rendering video frames...",
            85: "Applying enhancements...",
            92: "Encoding final video...",
            97: "Finalizing output..."
        }
        
        while not stop_event.is_set():
            if current_progress < 20:
                current_progress += 1.5
            elif current_progress < 50:
                current_progress += 0.8
            elif current_progress < 80:
                current_progress += 0.4
            elif current_progress < 95:
                current_progress += 0.2
            
            current_progress = min(current_progress, 98)
            
            # Get appropriate message for current stage
            msg = "Processing..."
            for threshold, message in sorted(stage_messages.items(), reverse=True):
                if current_progress >= threshold:
                    msg = message
                    break
            
            # Update status
            processing_status[final_name] = {
                "progress": round(current_progress, 1),
                "message": msg
            }
            
            # Update database
            update_video_progress(final_name, round(current_progress, 1), msg)
            
            time.sleep(0.8)

    try:
        # Create video project in database
        print(f"[DB] Creating video project record...")
        display_name = f"Video {final_name[:8]}"
        create_video_project(
            user_id=user_id,
            video_id=final_name,
            display_name=display_name,
            filename=final_name,
            original_image=img_path,
            original_audio=aud_path,
            ref_video=ref_vid_path if use_ref_video else None,
            settings=settings
        )
        print(f"[DB] Video project created successfully")
        
        # Load SadTalker model on first use
        model = load_sadtalker_model()
        if model is None:
            raise Exception("SadTalker model not loaded. Cannot generate video.")
        
        # Start progress simulator
        print(f"[PROCESS] Starting video generation pipeline...")
        sim_thread = threading.Thread(target=progress_simulator)
        sim_thread.start()
        
        # Generate video
        print(f"[PROCESS] Calling SadTalker.test() - this may take several minutes...")
        video_path = model.test(
            source_image=img_path,
            driven_audio=aud_path,
            preprocess=preprocess,
            still_mode=still_mode,
            use_enhancer=use_enhancer,
            batch_size=batch_size,
            size=size,
            pose_style=pose_style,
            exp_scale=exp_scale,
            use_ref_video=use_ref_video,
            ref_video=ref_vid_path,
            ref_info=ref_info,
            use_idle_mode=use_idle_mode,
            length_of_audio=length_of_audio,
            use_blink=use_blink,
            use_video_source=use_video_source
        )
        
        print(f"[PROCESS] SadTalker processing complete!")
        print(f"[PROCESS] Generated video path: {video_path}")
        
        # Stop simulator
        stop_event.set()
        sim_thread.join()
        
        # Copy result to static folder
        print(f"[FILE] Copying video to results directory...")
        final_path = os.path.join(RESULT_DIR, final_name)
        
        if os.path.exists(video_path):
            shutil.copy(video_path, final_path)
            file_size = os.path.getsize(final_path)
            print(f"[FILE] Video saved: {final_path}")
            print(f"[FILE] File size: {file_size / (1024*1024):.2f} MB")
        else:
            raise Exception(f"Generated video not found at {video_path}")
        
        # Update database
        print(f"[DB] Marking video as completed...")
        complete_video_project(final_name, final_path, file_size)
        
        # Final status
        processing_time = time.time() - start_time
        processing_status[final_name] = {
            "progress": 100,
            "message": "Complete!"
        }
        
        print(f"\n{'='*70}")
        print(f"[SUCCESS] Video generation completed successfully!")
        print(f"[SUCCESS] Video ID: {final_name}")
        print(f"[SUCCESS] Processing time: {processing_time:.2f} seconds ({processing_time/60:.2f} minutes)")
        print(f"[SUCCESS] Output: {final_path}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        stop_event.set()
        processing_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print(f"[ERROR] Video generation failed!")
        print(f"[ERROR] Video ID: {final_name}")
        print(f"[ERROR] Error: {str(e)}")
        print(f"[ERROR] Processing time before failure: {processing_time:.2f} seconds")
        print(f"{'='*70}\n")
        
        processing_status[final_name] = {
            "progress": -1,
            "message": f"Error: {str(e)}"
        }
        
        # Update database with failure
        fail_video_project(final_name, str(e))


# ==================== FLASK ROUTES ====================

@app.route("/unified_api.html")
def unified_api():
    """Serve the API-based unified HTML file"""
    return render_template("unified_api.html")


@app.route("/", methods=["GET", "POST"])
def index():
    """Main page route"""
    if request.method == "POST":
        print(f"\n{'='*70}")
        print(f"[REQUEST] New video generation request received")
        print(f"{'='*70}")
        
        # Get user from session token if available
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            from database import validate_session
            session_token = auth_header.split(' ')[1]
            valid, user = validate_session(session_token)
            if valid:
                user_id = user['id']
                print(f"[AUTH] User authenticated: {user['email']} (ID: {user_id})")
        
        if not user_id:
            print(f"[AUTH] No valid session - video will be created without user association")
        
        # Handle file uploads
        use_video_source = 'use_video_source' in request.form
        
        if use_video_source:
            # Video source mode
            if 'source_video' not in request.files:
                print("[ERROR] No source video file in request")
                return redirect(request.url)
            
            source_video = request.files["source_video"]
            if source_video.filename == '':
                print("[ERROR] Empty source video filename")
                return redirect(request.url)
            
            # Save source video
            vid_filename = secure_filename(source_video.filename)
            img_path = os.path.join(UPLOAD_DIR, vid_filename)
            source_video.save(img_path)
            print(f"[UPLOAD] Source video saved: {img_path}")
        else:
            # Image source mode
            if 'image' not in request.files:
                print("[ERROR] No image file in request")
                return redirect(request.url)
            
            image = request.files["image"]
            if image.filename == '':
                print("[ERROR] Empty image filename")
                return redirect(request.url)
            
            # Save uploaded files
            img_filename = secure_filename(image.filename)
            img_path = os.path.join(UPLOAD_DIR, img_filename)
            image.save(img_path)
            print(f"[UPLOAD] Image saved: {img_path}")
        
        # Handle audio
        aud_path = None
        if 'audio' in request.files:
            audio = request.files["audio"]
            if audio.filename != '':
                aud_filename = secure_filename(audio.filename)
                aud_path = os.path.join(UPLOAD_DIR, aud_filename)
                audio.save(aud_path)
                print(f"[UPLOAD] Audio saved: {aud_path}")
        
        # Handle reference video
        ref_vid_path = None
        if 'ref_video' in request.files:
            ref_video = request.files["ref_video"]
            if ref_video.filename != '':
                ref_filename = secure_filename(ref_video.filename)
                ref_vid_path = os.path.join(UPLOAD_DIR, ref_filename)
                ref_video.save(ref_vid_path)
                print(f"[UPLOAD] Reference video saved: {ref_vid_path}")
        
        # Get form settings
        preprocess = request.form.get("preprocess", "crop")
        still_mode = "still_mode" in request.form
        use_enhancer = "enhancer" in request.form
        batch_size = int(request.form.get("batch_size", 1))
        size = int(request.form.get("size", 256))
        pose_style = int(request.form.get("pose_style", 0))
        exp_scale = float(request.form.get("exp_scale", 1.0))
        use_idle_mode = "use_idle_mode" in request.form
        length_of_audio = int(request.form.get("length_of_audio", 5))
        use_blink = "use_blink" in request.form
        use_ref_video = "use_ref_video" in request.form
        ref_info = request.form.get("ref_info", "pose")
        use_video_source = "use_video_source" in request.form
        
        print(f"[SETTINGS] Preprocess: {preprocess}")
        print(f"[SETTINGS] Still Mode: {still_mode}")
        print(f"[SETTINGS] Enhancer: {use_enhancer}")
        print(f"[SETTINGS] Batch Size: {batch_size}")
        print(f"[SETTINGS] Size: {size}")
        print(f"[SETTINGS] Pose Style: {pose_style}")
        print(f"[SETTINGS] Expression Scale: {exp_scale}")
        print(f"[SETTINGS] Idle Mode: {use_idle_mode}")
        print(f"[SETTINGS] Blink: {use_blink}")
        print(f"[SETTINGS] Use Ref Video: {use_ref_video}")
        
        # Validation
        if not aud_path and not use_idle_mode and not use_ref_video:
            print("[ERROR] Validation failed: No audio, idle mode not enabled, and no reference video")
            return "Error: Please upload audio, enable idle mode, or provide a reference video.", 400
        
        # Generate unique filename
        final_name = f"{uuid.uuid4()}.mp4"
        print(f"[GENERATE] Starting video generation with ID: {final_name}")
        
        # Collect settings
        settings = {
            'preprocess': preprocess,
            'still_mode': still_mode,
            'use_enhancer': use_enhancer,
            'batch_size': batch_size,
            'size': size,
            'pose_style': pose_style,
            'exp_scale': exp_scale,
            'use_idle_mode': use_idle_mode,
            'length_of_audio': length_of_audio,
            'use_blink': use_blink,
            'use_ref_video': use_ref_video,
            'ref_info': ref_info,
            'use_video_source': use_video_source
        }
        
        # Start background generation
        print(f"[THREAD] Starting background generation thread...")
        thread = threading.Thread(
            target=generate_video_background,
            args=(
                img_path, aud_path, preprocess, still_mode, use_enhancer,
                batch_size, size, pose_style, exp_scale, use_ref_video,
                ref_vid_path, ref_info, use_idle_mode, length_of_audio,
                use_blink, final_name, user_id, settings, use_video_source
            )
        )
        thread.start()
        
        print(f"[REDIRECT] Redirecting to result page: /result/{final_name}")
        print(f"{'='*70}\n")
        
        return redirect(url_for("result", video=final_name))
    
    return render_template("unified_api.html")


@app.route("/result/<video>")
def result(video):
    """Result page route"""
    return render_template("unified.html", video=video)


@app.route("/stream/<video>")
def stream(video):
    """SSE stream for video generation progress"""
    def event_stream():
        last_status = None
        while True:
            # Check in-memory status
            if video in processing_status:
                status = processing_status[video]
            elif os.path.exists(os.path.join(RESULT_DIR, video)):
                status = {"progress": 100, "message": "Complete!"}
            else:
                status = {"progress": 0, "message": "Waiting to start..."}
            
            # Only send if status changed
            if status != last_status:
                yield f"data: {json.dumps(status)}\n\n"
                last_status = status
            
            # End conditions
            if status.get("progress", 0) >= 100 or status.get("progress", 0) < 0:
                break
            
            time.sleep(0.5)
    
    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/upload_preview", methods=["POST"])
def upload_preview():
    """Handle video preview upload and conversion"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        temp_path = os.path.join(UPLOAD_DIR, secure_filename(file.filename))
        file.save(temp_path)
        
        # Convert for preview
        preview_filename = convert_for_preview(temp_path)
        
        return jsonify({
            "url": url_for('static', filename=f'previews/{preview_filename}')
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Preview conversion failed: {e}")
        return jsonify({"error": str(e)}), 500


def convert_for_preview(video_path):
    """Convert video to browser-friendly format"""
    filename = os.path.basename(video_path)
    preview_filename = os.path.splitext(filename)[0] + "_preview.mp4"
    preview_path = os.path.join(PREVIEW_DIR, preview_filename)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "baseline",
        "-level", "3.0",
        "-movflags", "+faststart",
        "-c:a", "aac",
        preview_path
    ]
    
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return preview_filename


@app.route("/history")
def history():
    """Get video history"""
    # This is now handled by the API, keeping for backward compatibility
    return jsonify([])


@app.route('/static/examples/<path:filename>')
def serve_examples(filename):
    """Serve example files"""
    return send_from_directory('examples', filename)


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" SadTalker AI Video Generation Platform")
    print("="*70)
    
    # Initialize database
    print("\n[INIT] Initializing database...")
    if init_database():
        migrate_database()
        print("[INIT] Database ready!")
    else:
        print("[INIT WARNING] Database initialization had issues. Some features may not work.")
    
    # Print startup info
    print(f"\n[INIT] Upload directory: {os.path.abspath(UPLOAD_DIR)}")
    print(f"[INIT] Results directory: {os.path.abspath(RESULT_DIR)}")
    print(f"[INIT] Previews directory: {os.path.abspath(PREVIEW_DIR)}")
    
    print("\n" + "="*70)
    print(f" Starting Flask server on http://127.0.0.1:7860")
    print(" Press CTRL+C to stop")
    print("="*70 + "\n")
    
    # Run Flask app
    app.run(
        host="127.0.0.1",
        port=7860,
        debug=True,
        threaded=True
    )