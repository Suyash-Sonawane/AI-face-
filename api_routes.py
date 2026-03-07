"""
SadTalker API Routes Module
RESTful API endpoints for authentication, videos, audio, and system management
"""

import os
import uuid
import json
import requests
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app, redirect
from werkzeug.utils import secure_filename
from database import (
    register_user, login_user, logout_user, validate_session, register_oauth_user, create_session_for_user,
    create_video_project, update_video_progress, complete_video_project, fail_video_project,
    get_user_videos, get_video_by_id, delete_video, rename_video,
    get_all_users, get_all_videos, toggle_user_active, delete_user, update_user_role, update_user_email, get_system_stats,
    get_user_preferences, update_user_preferences,
    get_system_config, update_system_config, log_usage_stat,
    update_user_avatar, update_user_profile
)

# Google OAuth Configuration - Use environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/google/callback')

# Create Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== AUTHENTICATION DECORATOR ====================

def require_auth(f):
    """Decorator to require valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        session_token = auth_header.split(' ')[1]
        valid, user = validate_session(session_token)
        
        if not valid:
            return jsonify({'success': False, 'error': 'Invalid or expired session'}), 401
        
        # Add user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        session_token = auth_header.split(' ')[1]
        valid, user = validate_session(session_token)
        
        if not valid:
            return jsonify({'success': False, 'error': 'Invalid or expired session'}), 401
        
        if user.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


# ==================== AUTHENTICATION ENDPOINTS ====================

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    """Register a new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    # Validation
    if not email or not password or not name:
        return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    
    success, message, user_id = register_user(email, password, name)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'user_id': user_id
        }), 201
    else:
        return jsonify({'success': False, 'error': message}), 400


@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """Login user and create session"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required'}), 400
    
    # Get client info
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:500]
    
    success, message, user_data = login_user(email, password, ip_address, user_agent)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'user': {
                'id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data['role'],
                'avatar_url': user_data.get('avatar_url'),
                'session_token': user_data['session_token']
            }
        }), 200
    else:
        return jsonify({'success': False, 'error': message}), 401


@api_bp.route('/auth/logout', methods=['POST'])
@require_auth
def api_logout():
    """Logout user and invalidate session"""
    auth_header = request.headers.get('Authorization')
    session_token = auth_header.split(' ')[1]
    
    success = logout_user(session_token)
    
    if success:
        return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
    else:
        return jsonify({'success': False, 'error': 'Logout failed'}), 500


@api_bp.route('/auth/me', methods=['GET'])
@require_auth
def api_get_current_user():
    """Get current logged-in user info"""
    user = request.current_user
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'avatar_url': user.get('avatar_url')
        }
    }), 200


@api_bp.route('/auth/validate', methods=['GET'])
def api_validate_session():
    """Validate session token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'valid': False}), 200
    
    session_token = auth_header.split(' ')[1]
    valid, user = validate_session(session_token)
    
    if valid:
        return jsonify({
            'success': True,
            'valid': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            }
        }), 200
    else:
        return jsonify({'success': True, 'valid': False}), 200


# ==================== GOOGLE OAUTH ENDPOINTS ====================

@api_bp.route('/auth/google', methods=['GET'])
def google_login():
    """Initiate Google OAuth login"""
    if not GOOGLE_CLIENT_ID:
        return jsonify({'success': False, 'error': 'Google OAuth not configured'}), 500
    
    # Generate state parameter for security
    import secrets
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Build Google OAuth URL
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return jsonify({'success': True, 'auth_url': google_auth_url}), 200


@api_bp.route('/auth/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    # Check for errors
    if error:
        return redirect(f'/unified_api.html?auth=error&message={error}')
    
    if not code:
        return redirect('/unified_api.html?auth=error&message=No authorization code received')
    
    # Verify state parameter
    stored_state = session.get('oauth_state')
    if not stored_state or state != stored_state:
        return redirect('/unified_api.html?auth=error&message=Invalid state parameter')
    
    # Clear state from session
    session.pop('oauth_state', None)
    
    try:
        # Exchange code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        access_token = tokens.get('access_token')
        if not access_token:
            return redirect('/unified_api.html?auth=error&message=Failed to get access token')
        
        # Get user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
        
        # Extract user data
        google_id = userinfo.get('id')
        email = userinfo.get('email')
        name = userinfo.get('name', email.split('@')[0])
        avatar_url = userinfo.get('picture')
        
        if not google_id or not email:
            return redirect('/unified_api.html?auth=error&message=Failed to get user info from Google')
        
        # Register or get existing user
        success, message, user = register_oauth_user(email, name, google_id, avatar_url)
        
        if not success:
            return redirect(f'/unified_api.html?auth=error&message={message}')
        
        # Create session for user
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:500]
        session_token = create_session_for_user(user['id'], ip_address, user_agent)
        
        if not session_token:
            return redirect('/unified_api.html?auth=error&message=Failed to create session')
        
        # Redirect back to frontend with session token
        return redirect(f'/unified_api.html?auth=success&token={session_token}&name={name}&email={email}')
        
    except requests.RequestException as e:
        print(f"[GOOGLE OAUTH ERROR] {e}")
        return redirect('/unified_api.html?auth=error&message=Google authentication failed')
    except Exception as e:
        print(f"[GOOGLE OAUTH ERROR] {e}")
        return redirect('/unified_api.html?auth=error&message=An error occurred during authentication')


@api_bp.route('/auth/google/verify', methods=['POST'])
def google_verify_token():
    """Verify Google ID token (for frontend Google Sign-In)"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    id_token = data.get('id_token')
    if not id_token:
        return jsonify({'success': False, 'error': 'ID token is required'}), 400
    
    try:
        # Verify the ID token with Google
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
        
        # Verify token
        idinfo = google_id_token.verify_oauth2_token(
            id_token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        
        # Check issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return jsonify({'success': False, 'error': 'Invalid token issuer'}), 401
        
        # Extract user data
        google_id = idinfo['sub']
        email = idinfo.get('email')
        name = idinfo.get('name', email.split('@')[0])
        avatar_url = idinfo.get('picture')
        
        if not google_id or not email:
            return jsonify({'success': False, 'error': 'Invalid token data'}), 400
        
        # Register or get existing user
        success, message, user = register_oauth_user(email, name, google_id, avatar_url)
        
        if not success:
            return jsonify({'success': False, 'error': message}), 400
        
        # Create session for user
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:500]
        session_token = create_session_for_user(user['id'], ip_address, user_agent)
        
        if not session_token:
            return jsonify({'success': False, 'error': 'Failed to create session'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'avatar_url': user.get('avatar_url'),
                'session_token': session_token
            }
        }), 200
        
    except ValueError as e:
        # Invalid token
        return jsonify({'success': False, 'error': 'Invalid token'}), 401
    except Exception as e:
        print(f"[GOOGLE VERIFY ERROR] {e}")
        return jsonify({'success': False, 'error': 'Token verification failed'}), 500


# ==================== VIDEO ENDPOINTS ====================

@api_bp.route('/videos', methods=['GET'])
@require_auth
def api_get_videos():
    """Get all videos for current user"""
    user = request.current_user
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    videos = get_user_videos(user['id'], limit, offset)
    
    return jsonify({
        'success': True,
        'videos': videos,
        'count': len(videos)
    }), 200


@api_bp.route('/videos/<video_id>', methods=['GET'])
@require_auth
def api_get_video(video_id):
    """Get specific video by ID"""
    user = request.current_user
    video = get_video_by_id(video_id, user['id'])
    
    if not video:
        return jsonify({'success': False, 'error': 'Video not found'}), 404
    
    return jsonify({
        'success': True,
        'video': video
    }), 200


@api_bp.route('/videos/<path:video_id>', methods=['DELETE'])
@require_auth
def api_delete_video(video_id):
    """Delete a video"""
    user = request.current_user
    
    # Clean up video_id - remove .mp4 extension if present
    clean_video_id = video_id.replace('.mp4', '')
    
    print(f"[API DELETE] User {user['id']} attempting to delete video: {clean_video_id}")
    
    success = delete_video(clean_video_id, user['id'])
    
    if success:
        return jsonify({'success': True, 'message': 'Video deleted successfully'}), 200
    else:
        return jsonify({'success': False, 'error': 'Video not found or access denied'}), 404


@api_bp.route('/videos/<video_id>/favorite', methods=['POST'])
@require_auth
def api_toggle_favorite(video_id):
    """Toggle favorite status for a video"""
    # TODO: Implement favorite toggle
    return jsonify({'success': False, 'error': 'Not implemented yet'}), 501


@api_bp.route('/videos/<video_id>/rename', methods=['POST'])
@require_auth
def api_rename_video(video_id):
    """Rename a video's display name"""
    user = request.current_user
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'New name is required'}), 400
    
    new_name = data['name'].strip()
    if not new_name:
        return jsonify({'success': False, 'error': 'Name cannot be empty'}), 400
    
    success = rename_video(video_id, user['id'], new_name)
    
    if success:
        return jsonify({'success': True, 'message': 'Video renamed successfully'}), 200
    else:
        return jsonify({'success': False, 'error': 'Video not found or access denied'}), 404


# ==================== ADMIN ENDPOINTS ====================

@api_bp.route('/admin/users', methods=['GET'])
@require_admin
def api_admin_get_users():
    """Get all users (admin only)"""
    users = get_all_users()
    return jsonify({
        'success': True,
        'users': users,
        'count': len(users)
    }), 200


@api_bp.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@require_admin
def api_admin_toggle_user(user_id):
    """Toggle user active status (admin only)"""
    data = request.get_json() or {}
    is_active = data.get('is_active', True)
    
    success = toggle_user_active(user_id, is_active)
    
    if success:
        return jsonify({
            'success': True,
            'message': f"User {'activated' if is_active else 'deactivated'} successfully"
        }), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to update user'}), 500


@api_bp.route('/admin/videos', methods=['GET'])
@require_admin
def api_admin_get_all_videos():
    """Get all videos from all users (admin only)"""
    limit = request.args.get('limit', 100, type=int)
    videos = get_all_videos(limit)
    
    return jsonify({
        'success': True,
        'videos': videos,
        'count': len(videos)
    }), 200


@api_bp.route('/admin/stats', methods=['GET'])
@require_admin
def api_admin_get_stats():
    """Get system statistics (admin only)"""
    stats = get_system_stats()
    return jsonify({
        'success': True,
        'stats': stats
    }), 200


@api_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@require_admin
def api_admin_delete_user(user_id):
    """Delete a user (admin only)"""
    # Prevent deleting yourself
    if request.current_user['id'] == user_id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    success = delete_user(user_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to delete user'}), 500


@api_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@require_admin
def api_admin_update_user_role(user_id):
    """Update user role (admin only)"""
    data = request.get_json() or {}
    role = data.get('role', 'user')
    
    if role not in ['user', 'admin']:
        return jsonify({'success': False, 'error': 'Invalid role. Must be "user" or "admin"'}), 400
    
    # Prevent demoting yourself
    if request.current_user['id'] == user_id and role != 'admin':
        return jsonify({'success': False, 'error': 'Cannot demote yourself from admin'}), 400
    
    success = update_user_role(user_id, role)
    
    if success:
        return jsonify({
            'success': True,
            'message': f"User role updated to {role}"
        }), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to update user role'}), 500


@api_bp.route('/admin/users/<int:user_id>/email', methods=['POST'])
@require_admin
def api_admin_update_user_email(user_id):
    """Update user email (admin only)"""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    success, message = update_user_email(user_id, email)
    
    if success:
        return jsonify({
            'success': True,
            'message': message
        }), 200
    else:
        return jsonify({'success': False, 'error': message}), 400


@api_bp.route('/admin/users/bulk-delete', methods=['POST'])
@require_admin
def api_admin_bulk_delete_users():
    """Delete multiple users (admin only)"""
    data = request.get_json() or {}
    user_ids = data.get('user_ids', [])
    
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'success': False, 'error': 'user_ids array is required'}), 400
    
    # Prevent deleting yourself
    current_user_id = request.current_user['id']
    if current_user_id in user_ids:
        return jsonify({'success': False, 'error': 'Cannot delete your own account from bulk delete'}), 400
    
    deleted_count = 0
    failed_count = 0
    
    for user_id in user_ids:
        if delete_user(user_id):
            deleted_count += 1
        else:
            failed_count += 1
    
    return jsonify({
        'success': True,
        'message': f"Deleted {deleted_count} users, {failed_count} failed",
        'deleted_count': deleted_count,
        'failed_count': failed_count
    }), 200


@api_bp.route('/admin/users/export', methods=['GET'])
@require_admin
def api_admin_export_users():
    """Export user data as JSON (admin only)"""
    import json
    from flask import make_response
    
    users = get_all_users()
    
    # Create export data
    export_data = {
        'export_date': datetime.now().isoformat(),
        'total_users': len(users),
        'users': users
    }
    
    # Create response with proper headers for CORS and download
    response = make_response(json.dumps(export_data, indent=2, default=str))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=sadtalker_users_export.json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response


@api_bp.route('/admin/users/export', methods=['OPTIONS'])
def api_admin_export_users_options():
    """Handle CORS preflight for export endpoint"""
    from flask import make_response
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    return response, 200


# ==================== USER PROFILE ENDPOINTS ====================

@api_bp.route('/user/avatar', methods=['POST'])
@require_auth
def api_update_avatar():
    """Update user avatar"""
    user = request.current_user
    
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No avatar file provided'}), 400
    
    avatar_file = request.files['avatar']
    
    if avatar_file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = avatar_file.filename.rsplit('.', 1)[1].lower() if '.' in avatar_file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
    
    try:
        # Create avatars directory if it doesn't exist
        avatar_dir = os.path.join('uploads', 'avatars')
        os.makedirs(avatar_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"user_{user['id']}_{uuid.uuid4().hex[:8]}.{file_ext}"
        filepath = os.path.join(avatar_dir, filename)
        
        # Save the file
        avatar_file.save(filepath)
        
        # Create URL path for the avatar
        avatar_url = f"/uploads/avatars/{filename}"
        
        # Update database
        success, message = update_user_avatar(user['id'], avatar_url)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Avatar updated successfully',
                'avatar_url': avatar_url
            }), 200
        else:
            # Remove file if database update failed
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'success': False, 'error': message}), 500
            
    except Exception as e:
        print(f"[AVATAR UPLOAD ERROR] {e}")
        return jsonify({'success': False, 'error': 'Failed to upload avatar'}), 500


@api_bp.route('/user/profile', methods=['PUT'])
@require_auth
def api_update_profile():
    """Update user profile (name and/or avatar URL)"""
    user = request.current_user
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    name = data.get('name')
    avatar_url = data.get('avatar_url')
    
    success, message = update_user_profile(user['id'], name, avatar_url)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'user': {
                'id': user['id'],
                'name': name if name else user['name'],
                'avatar_url': avatar_url if avatar_url else user.get('avatar_url')
            }
        }), 200
    else:
        return jsonify({'success': False, 'error': message}), 400


@api_bp.route('/user/profile', methods=['GET'])
@require_auth
def api_get_user_profile():
    """Get current user profile info"""
    user = request.current_user
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'avatar_url': user.get('avatar_url')
        }
    }), 200


# ==================== USER PREFERENCES ENDPOINTS ====================

@api_bp.route('/preferences', methods=['GET'])
@require_auth
def api_get_preferences():
    """Get user preferences"""
    user = request.current_user
    preferences = get_user_preferences(user['id'])
    
    return jsonify({
        'success': True,
        'preferences': preferences
    }), 200


@api_bp.route('/preferences', methods=['PUT'])
@require_auth
def api_update_preferences():
    """Update user preferences"""
    user = request.current_user
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    success = update_user_preferences(user['id'], data)
    
    if success:
        return jsonify({'success': True, 'message': 'Preferences updated'}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to update preferences'}), 500


# ==================== SYSTEM CONFIG ENDPOINTS ====================

@api_bp.route('/config/<config_key>', methods=['GET'])
def api_get_config(config_key):
    """Get system configuration value (public)"""
    value = get_system_config(config_key)
    
    if value is not None:
        return jsonify({
            'success': True,
            'config_key': config_key,
            'config_value': value
        }), 200
    else:
        return jsonify({'success': False, 'error': 'Config not found'}), 404


@api_bp.route('/config/<config_key>', methods=['PUT'])
@require_admin
def api_update_config(config_key):
    """Update system configuration (admin only)"""
    data = request.get_json()
    
    if not data or 'value' not in data:
        return jsonify({'success': False, 'error': 'Value is required'}), 400
    
    success = update_system_config(config_key, str(data['value']))
    
    if success:
        return jsonify({'success': True, 'message': 'Config updated'}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to update config'}), 500


# ==================== FACE SWAP ====================

@api_bp.route('/face-swap', methods=['POST'])
@require_auth
def api_face_swap():
    """Start face swap processing"""
    try:
        # Check if face_swap module is available
        try:
            from face_swap import start_face_swap
        except ImportError as e:
            return jsonify({'success': False, 'error': f'Face swap module not available: {str(e)}'}), 500
        
        # Get uploaded files
        source_img = request.files.get('source_image')
        target_video = request.files.get('target_video')
        
        if not source_img or not target_video:
            return jsonify({'success': False, 'error': 'Source image and target video are required'}), 400
        
        # Validate file types
        allowed_img = ['.jpg', '.jpeg', '.png', '.webp']
        allowed_video = ['.mp4', '.webm', '.mov', '.avi']
        
        img_ext = os.path.splitext(source_img.filename)[1].lower()
        video_ext = os.path.splitext(target_video.filename)[1].lower()
        
        if img_ext not in allowed_img:
            return jsonify({'success': False, 'error': f'Invalid image format. Allowed: {allowed_img}'}), 400
        
        if video_ext not in allowed_video:
            return jsonify({'success': False, 'error': f'Invalid video format. Allowed: {allowed_video}'}), 400
        
        # Create unique filenames
        task_id = str(uuid.uuid4())
        upload_dir = "uploads/face_swap"
        result_dir = "static/results"
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)
        
        source_path = os.path.join(upload_dir, f"{task_id}_source{img_ext}")
        target_path = os.path.join(upload_dir, f"{task_id}_target{video_ext}")
        output_path = os.path.join(result_dir, f"{task_id}_faceswap.mp4")
        
        # Save uploaded files
        source_img.save(source_path)
        target_video.save(target_path)
        
        # Start face swap processing
        from face_swap import start_face_swap
        start_face_swap(source_path, target_path, output_path, task_id)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Face swap processing started',
            'status': 'processing'
        }), 200
        
    except Exception as e:
        print(f"[Face Swap API Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/face-swap/<task_id>/status', methods=['GET'])
@require_auth
def api_face_swap_status(task_id):
    """Get face swap processing status"""
    try:
        from face_swap import get_task_status
        status = get_task_status(task_id)
        
        if status is None:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': status['status'],
            'progress': status['progress'],
            'error': status['error'],
            'output_url': f'/static/results/{os.path.basename(status["output_path"])}' if status['status'] == 'completed' and os.path.exists(status['output_path']) else None
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/face-swap/models/check', methods=['GET'])
def api_face_swap_check_models():
    """Check if face swap models are available"""
    try:
        # MediaPipe models are included in the package, no download needed
        return jsonify({
            'success': True,
            'models_ready': True,
            'message': 'MediaPipe models are ready (included in package)'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HEALTH CHECK ====================

@api_bp.route('/health', methods=['GET'])
def api_health_check():
    """API health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200


# ==================== ERROR HANDLERS ====================

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500