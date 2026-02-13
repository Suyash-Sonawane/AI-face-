"""
SadTalker API Routes Module
RESTful API endpoints for authentication, videos, audio, and system management
"""

import os
import uuid
import json
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from database import (
    register_user, login_user, logout_user, validate_session,
    create_video_project, update_video_progress, complete_video_project, fail_video_project,
    get_user_videos, get_video_by_id, delete_video, rename_video,
    get_all_users, get_all_videos, toggle_user_active, delete_user, update_user_role, update_user_email, get_system_stats,
    get_user_preferences, update_user_preferences,
    get_system_config, update_system_config, log_usage_stat
)

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


@api_bp.route('/videos/<video_id>', methods=['DELETE'])
@require_auth
def api_delete_video(video_id):
    """Delete a video"""
    user = request.current_user
    success = delete_video(video_id, user['id'])
    
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