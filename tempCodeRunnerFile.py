import os
import shutil
from flask import Flask, render_template, request, redirect, url_for
from src.gradio_demo import SadTalker

app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = "uploads"
RESULT_DIR = "static/results"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Initialize SadTalker once when the app starts
sadtalker = SadTalker("checkpoints", "src/config", lazy_load=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 1. Handle Source Image (Required)
        if 'image' not in request.files:
            return redirect(request.url)
        image = request.files["image"]
        if image.filename == '':
            return redirect(request.url)
        img_path = os.path.join(UPLOAD_DIR, image.filename)
        image.save(img_path)

        # 2. Handle Audio (Optional if Idle Mode is on)
        aud_path = None
        if 'audio' in request.files:
            audio = request.files["audio"]
            if audio.filename != '':
                aud_path = os.path.join(UPLOAD_DIR, audio.filename)
                audio.save(aud_path)

        # 3. Handle Reference Video (Optional)
        ref_vid_path = None
        if 'ref_video' in request.files:
            ref_video = request.files["ref_video"]
            if ref_video.filename != '':
                ref_vid_path = os.path.join(UPLOAD_DIR, ref_video.filename)
                ref_video.save(ref_vid_path)

        # 4. Get Form Settings
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

        # Basic Validation
        if not aud_path and not use_idle_mode and not (use_ref_video and ref_vid_path):
            return "Error: Please upload audio, enable idle mode, or provide a reference video.", 400

        # Generate video using the existing SadTalker logic
        video_path = sadtalker.test(
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
            use_blink=use_blink
        )

        # Copy result into static folder so it can be served
        final_name = os.path.basename(video_path)
        final_path = os.path.join(RESULT_DIR, final_name)
        shutil.copy(video_path, final_path)

        return redirect(url_for("result", video=final_name))

    return render_template("index.html")

@app.route("/result/<video>")
def result(video):
    return render_template("result.html", video=video)

if __name__ == "__main__":
    print("Launching Flask app on http://127.0.0.1:7860")
    app.run(host="127.0.0.1", port=7860, debug=True)