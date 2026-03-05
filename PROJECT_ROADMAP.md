# SadTalker Project Roadmap - Complete Workflow Guide

## Project Overview
SadTalker is an AI-powered **Audio-Driven Talking Face Animation** system that generates realistic talking head videos from a single image and audio input. It uses 3D motion coefficients and deep learning to create lip-synced, expressive face animations.

---

## Table of Contents
1. [Project Architecture](#1-project-architecture)
2. [Entry Points & User Interfaces](#2-entry-points--user-interfaces)
3. [Data Flow - Step by Step](#3-data-flow---step-by-step)
4. [Core Processing Pipeline](#4-core-processing-pipeline)
5. [Database & Storage](#5-database--storage)
6. [API Endpoints](#6-api-endpoints)
7. [File Structure](#7-file-structure)
8. [Model Components](#8-model-components)
9. [Execution Flow Diagram](#9-execution-flow-diagram)
10. [Configuration & Environment](#10-configuration--environment)

---

## 1. Project Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SadTalker Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Frontend    │    │   Flask API  │    │  AI Models   │                  │
│  │  (React)     │◄──►│  (app_flask) │◄──►│  (PyTorch)   │                  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘                  │
│                             │                                               │
│                      ┌──────▼───────┐                                      │
│                      │   Database   │                                      │
│                      │ (SQLite/MySQL)│                                     │
│                      └──────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Entry Points & User Interfaces

### 2.1 Web UI Entry (Primary) - `webui.bat`
```batch
@ User runs: webui.bat
├─► Creates virtual environment (venv310)
├─► Activates venv310
├─► Calls: python launcher.py
│
└─► launcher.py:
    ├─ Checks Python version (requires 3.10)
    ├─ Installs dependencies from requirements.txt
    └─ Launches: python app_flask.py
```

### 2.2 Flask Application Entry - `app_flask.py`
```python
# Main application initialization
├─► Sets up Flask app with CORS
├─► Registers API blueprint (api_routes.py)
├─► Creates directories:
│   ├── uploads/          # User uploaded files
│   ├── uploads/avatars/  # User avatars
│   ├── static/results/   # Generated videos
│   └── static/previews/  # Video previews
├─► Initializes database (database.py)
└─► Loads SadTalker model (lazy loading on first use)
```

### 2.3 Alternative Entry Points

| Entry Point | Purpose | Usage |
|-------------|---------|-------|
| `inference.py` | Command-line inference | `python inference.py --driven_audio audio.wav --source_image img.png` |
| `src/gradio_demo.py` | Gradio demo interface | Interactive web demo |
| `desktop_app.py` | Desktop application | Standalone app |

---

## 3. Data Flow - Step by Step

### Complete Request Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────►│  Flask API  │────►│   Video     │────►│   AI Model  │
│  (Browser)  │     │(app_flask)  │     │  Queue/     │     │  Processing │
└─────────────┘     └─────────────┘     │  Threading  │     └─────────────┘
                                        └─────────────┘            │
                                             ▲                      │
                                             │                      ▼
                                        ┌─────────────┐     ┌─────────────┐
                                        │   Database  │◄────│   Output    │
                                        │  (MySQL/    │     │   Video     │
                                        │   SQLite)   │     └─────────────┘
                                        └─────────────┘            │
                                                                   │
                                                                   ▼
                                        ┌─────────────┐     ┌─────────────┐
                                        │    Logs/    │◄────│  Client     │
                                        │   Status    │     │  Download   │
                                        └─────────────┘     └─────────────┘
```

---

## 4. Core Processing Pipeline

### 4.1 Pipeline Overview
```
INPUT (Image + Audio) → PREPROCESS → AUDIO2COEFF → FACERENDER → ENHANCE → OUTPUT
```

### 4.2 Detailed Pipeline Steps

#### Step 1: Initialization (`src/utils/init_path.py`)
```python
init_path(checkpoint_dir, config_dir, size, old_version, preprocess)
├─► Determines model format (.safetensors vs .pth)
├─► Loads checkpoint paths:
│   ├── audio2pose_checkpoint    # Head pose prediction
│   ├── audio2exp_checkpoint     # Facial expression prediction
│   ├── free_view_checkpoint     # Face rendering
│   └── path_of_net_recon_model  # 3D face reconstruction
└─► Returns sadtalker_paths dictionary
```

#### Step 2: Preprocessing (`src/utils/preprocess.py`)
```python
class CropAndExtract
├─► Input: Source image/video
├─► Process:
│   ├── Face detection using face-alignment
│   ├── Face cropping (based on preprocess mode: crop/full/extcrop/resize)
│   ├── Extract 3DMM (3D Morphable Model) coefficients
│   └── Save landmarks and coefficients
└─► Output: first_coeff_path, crop_pic_path, crop_info
```

#### Step 3: Audio Processing (`src/generate_batch.py`)
```python
get_data(first_coeff_path, audio_path, device, ref_eyeblink_coeff_path, still)
├─► Convert audio to mel-spectrogram features
├─► Parse audio length and calculate frames (25 fps)
├─► Generate blink sequences (if enabled)
└─► Create batch data for model inference
```

#### Step 4: Audio to Coefficients (`src/test_audio2coeff.py`)
```python
class Audio2Coeff
├─► Initialize models:
│   ├── Audio2Pose (head pose prediction from audio)
│   └── Audio2Exp (expression coefficients from audio)
├─► generate():
│   ├── Predict expression coefficients (exp_pred)
│   ├── Predict head pose (pose_pred)
│   └── Combine into motion coefficients
└─► Output: coeff_path (.mat file with motion data)
```

#### Step 5: Face Rendering (`src/facerender/animate.py`)
```python
class AnimateFromCoeff
├─► Initialize components:
│   ├── KPDetector (keypoint detector)
│   ├── HEEstimator (head pose estimator)
│   ├── MappingNet (feature mapping)
│   └── OcclusionAwareSPADEGenerator (face generator)
├─► generate():
│   ├── Load source image
│   ├── Process motion coefficients
│   ├── Generate talking face frames
│   └── Composite frames with audio
├─► Optional Enhancement:
│   ├── GFPGAN face enhancement
│   └── Background enhancement
└─► Output: Final video file (MP4)
```

---

## 5. Database & Storage

### 5.1 Database Schema (`database.py`)

```sql
-- Users Table
┌─────────────┬──────────────┬─────────────┐
│   Field     │     Type     │ Description │
├─────────────┼──────────────┼─────────────┤
│ id          │ INTEGER PK   │ User ID     │
│ email       │ VARCHAR(255) │ Login email │
│ password_hash│ VARCHAR(255)│ BCrypt hash │
│ name        │ VARCHAR(255) │ Display name│
│ role        │ VARCHAR(50)  │ admin/user  │
│ avatar_url  │ VARCHAR(500) │ Profile pic │
│ is_active   │ BOOLEAN      │ Account status│
│ google_id   │ VARCHAR(255) │ OAuth ID    │
│ created_at  │ TIMESTAMP    │ Join date   │
│ last_login  │ TIMESTAMP    │ Last access │
└─────────────┴──────────────┴─────────────┘

-- Videos Table
┌─────────────┬──────────────┬──────────────────┐
│   Field     │     Type     │ Description      │
├─────────────┼──────────────┼──────────────────┤
│ id          │ INTEGER PK   │ Video ID         │
│ user_id     │ INTEGER FK   │ Owner reference  │
│ video_name  │ VARCHAR(255) │ Generated name   │
│ input_image │ VARCHAR(500) │ Source image path│
│ input_audio │ VARCHAR(500) │ Source audio path│
│ output_path │ VARCHAR(500) │ Result video path│
│ status      │ VARCHAR(50)  │ pending/processing/completed/failed│
│ progress    │ INTEGER      │ 0-100 completion │
│ settings    │ JSON         │ Generation params│
│ created_at  │ TIMESTAMP    │ Start time       │
│ completed_at│ TIMESTAMP    │ Finish time      │
└─────────────┴──────────────┴──────────────────┘

-- Sessions Table (for auth)
┌─────────────┬──────────────┬──────────────────┐
│   Field     │     Type     │ Description      │
├─────────────┼──────────────┼──────────────────┤
│ id          │ INTEGER PK   │ Session ID       │
│ user_id     │ INTEGER FK   │ User reference   │
│ session_token│ VARCHAR(255)│ JWT-like token   │
│ expires_at  │ TIMESTAMP    │ Expiration       │
│ created_at  │ TIMESTAMP    │ Session start    │
└─────────────┴──────────────┴──────────────────┘
```

### 5.2 Storage Structure
```
SadTalker/
├── uploads/
│   ├── avatars/          # User profile pictures
│   ├── [audio_files]     # User uploaded audio
│   └── [image_files]     # User uploaded images
├── static/
│   ├── results/          # Generated videos
│   └── previews/         # Preview frames
├── checkpoints/          # AI model weights
│   ├── SadTalker_V0.0.2_256.safetensors
│   ├── mapping_00229-model.pth.tar
│   └── ...
├── src/config/           # Model configs
│   ├── facerender.yaml
│   ├── auido2pose.yaml
│   └── auido2exp.yaml
└── sadtalker.db          # SQLite database
```

---

## 6. API Endpoints

### 6.1 Authentication Routes (`api_routes.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create new account |
| POST | `/api/auth/login` | Authenticate user |
| POST | `/api/auth/logout` | End session |
| GET | `/api/auth/google` | Google OAuth login |
| GET | `/api/auth/google/callback` | OAuth callback |
| GET | `/api/auth/me` | Get current user |
| PUT | `/api/auth/profile` | Update profile |

### 6.2 Video Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/videos` | Create new video project |
| GET | `/api/videos` | List user videos |
| GET | `/api/videos/<id>` | Get video details |
| DELETE | `/api/videos/<id>` | Delete video |
| PUT | `/api/videos/<id>/rename` | Rename video |
| GET | `/api/videos/<id>/status` | Get processing status |
| GET | `/api/videos/<id>/download` | Download video |

### 6.3 Admin Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users |
| PUT | `/api/admin/users/<id>/toggle` | Enable/disable user |
| DELETE | `/api/admin/users/<id>` | Delete user |
| GET | `/api/admin/stats` | System statistics |

---

## 7. File Structure

```
SadTalker/
│
├── 📁 Entry Points
│   ├── webui.bat           # Windows launcher
│   ├── launcher.py         # Environment setup
│   ├── app_flask.py        # Main Flask app
│   ├── inference.py        # CLI inference
│   └── desktop_app.py      # Desktop GUI
│
├── 📁 API & Backend
│   ├── api_routes.py       # REST API endpoints
│   ├── database.py         # Database operations
│   └── config.py           # Configuration management
│
├── 📁 Frontend (React)
│   ├── app/
│   │   ├── src/App.tsx     # Main React component
│   │   ├── src/components/ # UI components
│   │   ├── index.html      # HTML entry
│   │   └── package.json    # Node deps
│   └── unified_api.html    # Standalone HTML interface
│
├── 📁 Core AI Models (src/)
│   ├── gradio_demo.py      # SadTalker class wrapper
│   ├── test_audio2coeff.py # Audio→3DMM processing
│   ├── generate_batch.py   # Audio preprocessing
│   ├── generate_facerender_batch.py  # Face rendering prep
│   │
│   ├── 📁 facerender/      # Face generation
│   │   ├── animate.py      # Main renderer
│   │   ├── modules/        # Model components
│   │   └── sync_batchnorm/# Training utilities
│   │
│   ├── 📁 face3d/          # 3D face processing
│   │   ├── models/         # 3DMM networks
│   │   └── util/           # 3D utilities
│   │
│   ├── 📁 audio2pose_models/# Head pose prediction
│   ├── 📁 audio2exp_models/# Expression prediction
│   │
│   └── 📁 utils/           # Utilities
│       ├── preprocess.py   # Image preprocessing
│       ├── face_enhancer.py# GFPGAN enhancement
│       ├── croper.py       # Face cropping
│       ├── videoio.py      # Video I/O
│       ├── paste_pic.py    # Image composition
│       ├── audio.py        # Audio processing
│       └── init_path.py    # Path initialization
│
├── 📁 Data
│   ├── uploads/            # User uploads
│   ├── static/results/     # Output videos
│   ├── checkpoints/        # Model weights
│   └── sadtalker.db        # Database
│
├── 📁 Configuration
│   └── src/config/
│       ├── facerender.yaml
│       ├── facerender_still.yaml
│       ├── auido2pose.yaml
│       └── auido2exp.yaml
│
└── 📁 Documentation
    ├── README.md
    ├── docs/
    └── PROJECT_ROADMAP.md  # This file
```

---

## 8. Model Components

### 8.1 Neural Network Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    SadTalker AI Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Audio      │    │  Audio2Pose  │    │  Head Pose   │      │
│  │   Input      │───►│    Model     │───►│  Coefficients│      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                               │       │
│         │         ┌──────────────┐                      │       │
│         └────────►│  Audio2Exp   │                      │       │
│                   │    Model     │                      │       │
│                   └──────┬───────┘                      │       │
│                          │                              │       │
│                          ▼                              ▼       │
│                   ┌──────────────┐               ┌───────────┐  │
│                   │  Expression  │               │  Combine  │  │
│                   │ Coefficients │──────────────►│   3DMM    │  │
│                   └──────────────┘               └─────┬─────┘  │
│                                                        │        │
│  ┌──────────────┐    ┌──────────────┐                 │        │
│  │   Source     │    │  Face3D      │                 │        │
│  │   Image      │───►│  Recon       │                 │        │
│  └──────────────┘    └──────┬───────┘                 │        │
│                             │                          │        │
│                             ▼                          ▼        │
│                      ┌──────────────┐          ┌───────────┐   │
│                      │ Identity     │          │  Motion   │   │
│                      │ Coefficients │─────────►│  Coeffs   │   │
│                      └──────────────┘          └─────┬─────┘   │
│                                                      │         │
│                                                      ▼         │
│                                              ┌───────────┐    │
│                                              │ Face      │    │
│                                              │ Renderer  │    │
│                                              │ (vid2vid) │    │
│                                              └─────┬─────┘    │
│                                                    │          │
│                                                    ▼          │
│                                              ┌───────────┐    │
│                                              │  Output   │    │
│                                              │  Video    │    │
│                                              └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Model Checkpoints

| Checkpoint | Purpose | File |
|------------|---------|------|
| SadTalker | Combined model (safetensors) | `checkpoints/SadTalker_V0.0.2_256.safetensors` |
| Audio2Pose | Head pose from audio | Included in safetensors |
| Audio2Exp | Facial expression from audio | Included in safetensors |
| FaceVid2Vid | Face video generation | Included in safetensors |
| MappingNet | Feature mapping | `mapping_00229-model.pth.tar` |
| GFPGAN | Face enhancement (optional) | Downloaded on demand |

---

## 9. Execution Flow Diagram

### Complete Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION FLOW DIAGRAM                               │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: LAUNCH
===============
[webui.bat]
     │
     ▼
[launcher.py] ──► Check Python 3.10
     │            Install requirements
     │            Validate models
     ▼
[app_flask.py] ──► Initialize Flask app
                   Setup CORS
                   Register blueprints
                   Init database
                   Start server on :5000


PHASE 2: USER REGISTRATION/AUTH
===============================
[Browser] ──► POST /api/auth/register
                   │
                   ▼
[api_routes.py] ──► Validate input
                        │
                        ▼
[database.py] ──► Hash password (bcrypt)
                  INSERT INTO users
                        │
                        ▼
[Response] ◄──── Return user object + session token


PHASE 3: VIDEO GENERATION REQUEST
=================================
[Browser] ──► POST /generate_video (multipart/form-data)
                    ├── source_image
                    ├── driven_audio
                    └── settings (JSON)
                   │
                   ▼
[app_flask.py] ──► Authenticate user
                   Save uploaded files
                   Create video project in DB
                   Start background thread
                   │
                   ▼
[generate_video_background] ──► Async processing
                                     │
                                     ▼
[PHASE 4: AI PROCESSING PIPELINE]


PHASE 4: AI PIPELINE (Background Thread)
========================================
[1. Initialize] ──► Load SadTalker model (lazy)
                        ├── Preprocess model
                        ├── Audio2Coeff model
                        └── AnimateFromCoeff model
                        │
                        ▼
[2. Preprocess] ──► CropAndExtract.generate()
                        ├── Face detection
                        ├── Image cropping
                        └── 3DMM coefficient extraction
                        │
                        ▼
[3. Audio Processing] ──► generate_batch.get_data()
                             ├── Mel-spectrogram extraction
                             ├── Frame alignment (25fps)
                             └── Blink sequence generation
                        │
                        ▼
[4. Audio to Coeff] ──► Audio2Coeff.generate()
                           ├── Audio2Pose: Predict head pose
                           ├── Audio2Exp: Predict expressions
                           └── Combine into motion coefficients
                        │
                        ▼
[5. Face Render] ──► AnimateFromCoeff.generate()
                        ├── Load source image
                        ├── Apply motion coefficients
                        ├── Generate face frames (vid2vid)
                        ├── Add audio track
                        └── Optional: GFPGAN enhancement
                        │
                        ▼
[6. Post-process] ──► Move to results folder
                      Update DB (status: completed)
                      Cleanup temp files


PHASE 5: STATUS POLLING & DOWNLOAD
==================================
[Browser] ──► GET /api/videos/<id>/status
                   │
                   ▼
[Database] ──► SELECT status, progress
                   │
                   ▼
[Response] ◄── Return: {"status": "completed", "progress": 100}
                   │
                   ▼
[Browser] ──► GET /api/videos/<id>/download
                   │
                   ▼
[app_flask.py] ──► Send file from static/results/


PHASE 6: CLEANUP
================
├─► Old sessions purged (auto-cleanup)
├─► Expired videos deleted (configurable)
└─► Temp files removed after processing
```

---

## 10. Configuration & Environment

### 10.1 Environment Variables (`config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_TYPE` | mysql | Database type (mysql/sqlite) |
| `DB_HOST` | 127.0.0.1 | MySQL host |
| `DB_PORT` | 3306 | MySQL port |
| `DB_USER` | root | MySQL username |
| `DB_PASSWORD` | - | MySQL password |
| `DB_NAME` | sadtalker_db | Database name |
| `CLOUD_ENV` | false | Cloud deployment flag |
| `STORAGE_PATH` | ./data | Persistent storage path |

### 10.2 Processing Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `preprocess` | crop/full/extcrop/resize | Face cropping mode |
| `still_mode` | true/false | Disable head motion |
| `use_enhancer` | true/false | GFPGAN face enhancement |
| `batch_size` | 1-16 | Processing batch size |
| `size` | 256/512 | Output resolution |
| `pose_style` | 0-45 | Pose style reference |
| `exp_scale` | 0.0-2.0 | Expression intensity |
| `use_ref_video` | true/false | Use video for pose reference |

### 10.3 Directory Paths

```python
# Generated by init_path()
sadtalker_paths = {
    'checkpoint': 'checkpoints/SadTalker_V0.0.2_256.safetensors',
    'audio2pose_yaml_path': 'src/config/auido2pose.yaml',
    'audio2exp_yaml_path': 'src/config/auido2exp.yaml',
    'facerender_yaml': 'src/config/facerender.yaml',
    'mappingnet_checkpoint': 'checkpoints/mapping_00229-model.pth.tar',
    'dir_of_BFM_fitting': 'src/config',
    'use_safetensor': True
}
```

---

## Summary: Key Files Quick Reference

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `webui.bat` | Windows launcher | Activates venv, starts server |
| `launcher.py` | Environment setup | Python check, dependency install |
| `app_flask.py` | Flask web server | `load_sadtalker_model()`, `generate_video_background()` |
| `api_routes.py` | API endpoints | Auth, video, admin routes |
| `database.py` | Database layer | `init_database()`, CRUD operations |
| `src/gradio_demo.py` | SadTalker wrapper | `SadTalker` class, `test()` method |
| `src/utils/preprocess.py` | Image preprocessing | `CropAndExtract` class |
| `src/test_audio2coeff.py` | Audio processing | `Audio2Coeff` class |
| `src/facerender/animate.py` | Face generation | `AnimateFromCoeff` class |
| `src/utils/init_path.py` | Path setup | `init_path()` function |

---

## Workflow Cheat Sheet

```
┌─────────────────────────────────────────────────────────────────┐
│  START → webui.bat → launcher.py → app_flask.py → Server Ready │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  USER → Register/Login → Upload Image+Audio → Configure Settings│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  API → Validate → Save Files → Create DB Entry → Start Thread   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  AI PIPELINE: Preprocess → Audio2Coeff → FaceRender → Enhance   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT → Update DB → Notify User → Download Video              │
└─────────────────────────────────────────────────────────────────┘
```

---

*Document generated for SadTalker Project - Understanding the complete workflow from user input to video output.*
