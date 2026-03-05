import cv2, os
import numpy as np
from tqdm import tqdm
import uuid

from src.utils.videoio import save_video_with_watermark

def paste_pic(video_path, pic_path, crop_info, new_audio_path, full_video_path, extended_crop=False, is_video_source=False):
    """
    Paste generated face frames onto the source video/image.
    
    Args:
        video_path: Path to the generated face video
        pic_path: Path to source image or video
        crop_info: Crop information tuple
        new_audio_path: Path to the audio file
        full_video_path: Output path for the final video
        extended_crop: Whether to use extended crop
        is_video_source: Whether the source is a video (passed from gradio_demo.py)
    """
    
    # Check if source is video or image
    # If is_video_source is passed from caller (gradio_demo.py), use it
    # Otherwise auto-detect based on file extension
    if is_video_source:
        # Force video mode - source is a video
        if not os.path.isfile(pic_path):
            raise ValueError('pic_path must be a valid path to video/image file')
        
        # Source is a video - load all frames
        source_video_stream = cv2.VideoCapture(pic_path)
        source_fps = source_video_stream.get(cv2.CAP_PROP_FPS)
        source_frame_count = int(source_video_stream.get(cv2.CAP_PROP_FRAME_COUNT))
        
        source_frames = []
        while True:
            ret, frame = source_video_stream.read()
            if not ret:
                break
            source_frames.append(frame)
        source_video_stream.release()
        
        if len(source_frames) > 0:
            frame_h = source_frames[0].shape[0]
            frame_w = source_frames[0].shape[1]
        else:
            raise ValueError('Could not read frames from source video')
    elif pic_path.split('.')[-1].lower() in ['jpg', 'png', 'jpeg', 'bmp', 'webp']:
        # loader for first frame
        full_img = cv2.imread(pic_path)
        frame_h = full_img.shape[0]
        frame_w = full_img.shape[1]
        source_frames = None
    else:
        # Auto-detect: Source is a video - load all frames
        source_video_stream = cv2.VideoCapture(pic_path)
        source_fps = source_video_stream.get(cv2.CAP_PROP_FPS)
        source_frame_count = int(source_video_stream.get(cv2.CAP_PROP_FRAME_COUNT))
        
        source_frames = []
        while True:
            ret, frame = source_video_stream.read()
            if not ret:
                break
            source_frames.append(frame)
        source_video_stream.release()
        
        if len(source_frames) > 0:
            frame_h = source_frames[0].shape[0]
            frame_w = source_frames[0].shape[1]
        else:
            raise ValueError('Could not read frames from source video')

    # Load generated video frames
    video_stream = cv2.VideoCapture(video_path)
    fps = video_stream.get(cv2.CAP_PROP_FPS)
    crop_frames = []
    while True:
        still_reading, frame = video_stream.read()
        if not still_reading:
            break
        crop_frames.append(frame)
    video_stream.release()
    
    if len(crop_info) != 3:
        print("you didn't crop the image")
        return
    
    # Extract crop coordinates
    r_w, r_h = crop_info[0]
    clx, cly, crx, cry = crop_info[1]
    lx, ly, rx, ry = crop_info[2]
    lx, ly, rx, ry = int(lx), int(ly), int(rx), int(ry)

    if extended_crop:
        oy1, oy2, ox1, ox2 = cly, cry, clx, crx
    else:
        oy1, oy2, ox1, ox2 = cly+ly, cly+ry, clx+lx, clx+rx

    # Create output video
    tmp_path = str(uuid.uuid4())+'.mp4'
    out_tmp = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*'MP4V'), fps, (frame_w, frame_h))
    
    # Process each frame
    frame_count = len(crop_frames)
    for i, crop_frame in enumerate(tqdm(crop_frames, 'seamlessClone:')):
        p = cv2.resize(crop_frame.astype(np.uint8), (ox2-ox1, oy2 - oy1))

        # Get the appropriate background frame
        if source_frames is not None:
            # Cycle through source video frames if needed
            source_idx = i % len(source_frames)
            full_img = source_frames[source_idx].copy()
        else:
            # Use the same static image for all frames
            full_img = cv2.imread(pic_path)

        mask = 255*np.ones(p.shape, p.dtype)
        location = ((ox1+ox2) // 2, (oy1+oy2) // 2)
        gen_img = cv2.seamlessClone(p, full_img, mask, location, cv2.NORMAL_CLONE)
        out_tmp.write(gen_img)

    out_tmp.release()

    save_video_with_watermark(tmp_path, new_audio_path, full_video_path, watermark=False)
    os.remove(tmp_path)
