"""
SadTalker Database Module
Handles all database operations with support for SQLite (development) and MySQL (production)
"""

import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

# Try to import MySQL connector
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("[DB] MySQL connector not available. Using SQLite only.")

# Database Configuration - USING MYSQL AS PRIMARY
DB_TYPE = os.getenv('DB_TYPE', 'mysql')  # Default to MySQL as requested
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Suyash@261$'),
    'database': os.getenv('DB_NAME', 'sadtalker_db'),
    'autocommit': True
}

SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sadtalker.db')


class DatabaseError(Exception):
    """Custom database exception"""
    pass


@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic type handling"""
    conn = None
    try:
        if DB_TYPE == 'mysql' and MYSQL_AVAILABLE:
            conn = mysql.connector.connect(**DB_CONFIG)
        else:
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database connection error: {e}")
    finally:
        if conn:
            conn.close()


def init_database():
    """Initialize database with all required tables"""
    print(f"[DB] Initializing {DB_TYPE} database...")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Users table - stores authentication and profile info
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) DEFAULT '',
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    avatar_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT 1,
                    auth_provider VARCHAR(50) DEFAULT 'local',
                    google_id VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) DEFAULT '',
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'user',
                    avatar_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT TRUE,
                    auth_provider VARCHAR(50) DEFAULT 'local',
                    google_id VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL
                )
            """)
            
            # Session tokens table - for secure session management
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_valid BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_valid BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Videos table - stores video project metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    display_name VARCHAR(255),
                    filename VARCHAR(255) NOT NULL,
                    original_image VARCHAR(500),
                    original_audio VARCHAR(500),
                    ref_video VARCHAR(500),
                    status VARCHAR(50) DEFAULT 'processing',
                    progress INTEGER DEFAULT 0,
                    message TEXT,
                    settings JSON,
                    result_path VARCHAR(500),
                    file_size BIGINT,
                    duration INTEGER,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS videos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    video_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id INT NOT NULL,
                    display_name VARCHAR(255),
                    filename VARCHAR(255) NOT NULL,
                    original_image VARCHAR(500),
                    original_audio VARCHAR(500),
                    ref_video VARCHAR(500),
                    status VARCHAR(50) DEFAULT 'processing',
                    progress INT DEFAULT 0,
                    message TEXT,
                    settings JSON,
                    result_path VARCHAR(500),
                    file_size BIGINT,
                    duration INT,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Audio samples table - stores uploaded/generated audio
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audio_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size BIGINT,
                    duration INTEGER,
                    sample_type VARCHAR(50) DEFAULT 'upload',  -- 'upload', 'generated', 'cloned'
                    source_text TEXT,  -- For generated speech
                    voice_id VARCHAR(255),  -- For voice cloning
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS audio_samples (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size BIGINT,
                    duration INT,
                    sample_type VARCHAR(50) DEFAULT 'upload',
                    source_text TEXT,
                    voice_id VARCHAR(255),
                    is_favorite BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    default_preprocess VARCHAR(50) DEFAULT 'crop',
                    default_size INTEGER DEFAULT 256,
                    default_batch_size INTEGER DEFAULT 1,
                    default_pose_style INTEGER DEFAULT 0,
                    default_exp_scale DECIMAL(3,2) DEFAULT 1.0,
                    default_use_enhancer BOOLEAN DEFAULT 0,
                    default_use_blink BOOLEAN DEFAULT 1,
                    theme VARCHAR(20) DEFAULT 'dark',
                    language VARCHAR(10) DEFAULT 'en',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    default_preprocess VARCHAR(50) DEFAULT 'crop',
                    default_size INT DEFAULT 256,
                    default_batch_size INT DEFAULT 1,
                    default_pose_style INT DEFAULT 0,
                    default_exp_scale DECIMAL(3,2) DEFAULT 1.0,
                    default_use_enhancer BOOLEAN DEFAULT FALSE,
                    default_use_blink BOOLEAN DEFAULT TRUE,
                    theme VARCHAR(20) DEFAULT 'dark',
                    language VARCHAR(10) DEFAULT 'en',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # System configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value TEXT,
                    config_type VARCHAR(50) DEFAULT 'string',  -- 'string', 'int', 'float', 'bool', 'json'
                    description TEXT,
                    is_editable BOOLEAN DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS system_configs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value TEXT,
                    config_type VARCHAR(50) DEFAULT 'string',
                    description TEXT,
                    is_editable BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Usage statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    video_id VARCHAR(255),
                    action VARCHAR(100) NOT NULL,
                    processing_time FLOAT,
                    gpu_memory_used FLOAT,
                    cpu_percent FLOAT,
                    memory_percent FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """ if DB_TYPE == 'sqlite' else """
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    video_id VARCHAR(255),
                    action VARCHAR(100) NOT NULL,
                    processing_time FLOAT,
                    gpu_memory_used FLOAT,
                    cpu_percent FLOAT,
                    memory_percent FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            
            # Insert default admin user if not exists
            cursor.execute("SELECT id FROM users WHERE email = 'admin@sadtalker.com'")
            if not cursor.fetchone():
                admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO users (email, password_hash, name, role, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """ if DB_TYPE == 'sqlite' else """
                    INSERT INTO users (email, password_hash, name, role, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('admin@sadtalker.com', admin_hash, 'Administrator', 'admin', True))
                print("[DB] Default admin user created: admin@sadtalker.com / admin123")
            
            # Insert default system configs
            default_configs = [
                ('max_file_size', '104857600', 'int', 'Maximum upload file size in bytes (100MB)', False),
                ('max_video_duration', '300', 'int', 'Maximum video duration in seconds', True),
                ('allowed_image_formats', '["jpg", "jpeg", "png", "webp"]', 'json', 'Allowed image upload formats', True),
                ('allowed_audio_formats', '["wav", "mp3", "aac", "flac"]', 'json', 'Allowed audio upload formats', True),
                ('enable_registration', 'true', 'bool', 'Allow new user registration', True),
                ('maintenance_mode', 'false', 'bool', 'Enable maintenance mode', True),
                ('default_model', 'sadtalker', 'string', 'Default AI model to use', True),
            ]
            
            for config in default_configs:
                cursor.execute("SELECT id FROM system_configs WHERE config_key = ?" if DB_TYPE == 'sqlite' 
                              else "SELECT id FROM system_configs WHERE config_key = %s", (config[0],))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO system_configs (config_key, config_value, config_type, description, is_editable)
                        VALUES (?, ?, ?, ?, ?)
                    """ if DB_TYPE == 'sqlite' else """
                        INSERT INTO system_configs (config_key, config_value, config_type, description, is_editable)
                        VALUES (%s, %s, %s, %s, %s)
                    """, config)
            
            conn.commit()
            cursor.close()
            
        print(f"[DB] Database initialized successfully!")
        print(f"[DB] Tables created: users, user_sessions, videos, audio_samples, user_preferences, system_configs, usage_stats")
        return True
        
    except Exception as e:
        print(f"[DB ERROR] Failed to initialize database: {e}")
        return False


def migrate_database():
    """Migrate existing database to add new columns"""
    print(f"[DB] Checking for database migrations...")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if auth_provider column exists in users table
            try:
                if DB_TYPE == 'sqlite':
                    cursor.execute("PRAGMA table_info(users)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'auth_provider' not in columns:
                        print("[DB] Adding auth_provider column to users table...")
                        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'")
                        cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE")
                        conn.commit()
                        print("[DB] Migration completed: added auth_provider and google_id columns")
                else:
                    # MySQL - check if column exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'auth_provider'
                    """)
                    if cursor.fetchone()[0] == 0:
                        print("[DB] Adding auth_provider column to users table...")
                        cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'")
                        cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE")
                        conn.commit()
                        print("[DB] Migration completed: added auth_provider and google_id columns")
                    else:
                        print("[DB] Columns already exist, skipping migration")
                        
            except Exception as e:
                print(f"[DB WARNING] Migration check failed: {e}")
            
            # Also update password_hash to allow empty strings for OAuth users
            try:
                if DB_TYPE == 'mysql':
                    # Check if password_hash has NOT NULL constraint
                    cursor.execute("""
                        SELECT is_nullable, column_default 
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'password_hash'
                    """)
                    row = cursor.fetchone()
                    if row and row[0] == 'NO' and (row[1] is None or row[1] == ''):
                        print("[DB] Updating password_hash to allow NULL/empty values...")
                        cursor.execute("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) DEFAULT ''")
                        conn.commit()
                        print("[DB] Migration completed: password_hash can now be empty")
            except Exception as e:
                print(f"[DB WARNING] Password hash migration failed: {e}")
                
            cursor.close()
            
    except Exception as e:
        print(f"[DB ERROR] Migration failed: {e}")


# ==================== USER AUTHENTICATION ====================

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_session_token() -> str:
    """Generate secure random session token"""
    return secrets.token_urlsafe(32)


def register_user(email: str, password: str, name: str) -> Tuple[bool, str, Optional[int]]:
    """Register a new user"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if email exists
            cursor.execute(
                "SELECT id FROM users WHERE email = ?" if DB_TYPE == 'sqlite' else "SELECT id FROM users WHERE email = %s",
                (email,)
            )
            if cursor.fetchone():
                return False, "Email already registered", None
            
            # Hash password and insert user
            password_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, auth_provider)
                VALUES (?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO users (email, password_hash, name, role, auth_provider)
                VALUES (%s, %s, %s, %s, %s)
            """, (email, password_hash, name, 'user', 'local'))
            
            user_id = cursor.lastrowid
            
            # Create default preferences for user
            cursor.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO user_preferences (user_id)
                VALUES (%s)
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            
            return True, "User registered successfully", user_id
            
    except Exception as e:
        return False, f"Registration failed: {e}", None


def register_oauth_user(email: str, name: str, google_id: str, avatar_url: str = None) -> Tuple[bool, str, Optional[Dict]]:
    """Register or get existing OAuth user (Google)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists by google_id
            cursor.execute(
                "SELECT id, email, name, role, avatar_url, is_active FROM users WHERE google_id = ?" if DB_TYPE == 'sqlite' else 
                "SELECT id, email, name, role, avatar_url, is_active FROM users WHERE google_id = %s",
                (google_id,)
            )
            row = cursor.fetchone()
            
            if row:
                user = dict(row) if DB_TYPE == 'sqlite' else {
                    'id': row[0], 'email': row[1], 'name': row[2],
                    'role': row[3], 'avatar_url': row[4], 'is_active': row[5]
                }
                if not user['is_active']:
                    return False, "Account is deactivated", None
                return True, "User found", user
            
            # Check if email exists with local auth
            cursor.execute(
                "SELECT id FROM users WHERE email = ? AND auth_provider = 'local'" if DB_TYPE == 'sqlite' else 
                "SELECT id FROM users WHERE email = %s AND auth_provider = 'local'",
                (email,)
            )
            if cursor.fetchone():
                return False, "Email already registered with password. Please sign in with password.", None
            
            # Create new OAuth user
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, avatar_url, auth_provider, google_id)
                VALUES (?, NULL, ?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO users (email, password_hash, name, role, avatar_url, auth_provider, google_id)
                VALUES (%s, NULL, %s, %s, %s, %s, %s)
            """, (email, name, 'user', avatar_url, 'google', google_id))
            
            user_id = cursor.lastrowid
            
            # Create default preferences for user
            cursor.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO user_preferences (user_id)
                VALUES (%s)
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            
            user = {
                'id': user_id,
                'email': email,
                'name': name,
                'role': 'user',
                'avatar_url': avatar_url,
                'is_active': True
            }
            
            return True, "User registered successfully", user
            
    except Exception as e:
        return False, f"OAuth registration failed: {e}", None


def login_user(email: str, password: str, ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Optional[Dict]]:
    """Authenticate user and create session"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get user by email
            cursor.execute("""
                SELECT id, email, password_hash, name, role, is_active, avatar_url, auth_provider
                FROM users WHERE email = ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT id, email, password_hash, name, role, is_active, avatar_url, auth_provider
                FROM users WHERE email = %s
            """, (email,))
            
            row = cursor.fetchone()
            if not row:
                return False, "Invalid email or password", None
            
            user = dict(row) if DB_TYPE == 'sqlite' else {
                'id': row[0], 'email': row[1], 'password_hash': row[2],
                'name': row[3], 'role': row[4], 'is_active': row[5], 'avatar_url': row[6], 'auth_provider': row[7]
            }
            
            if not user['is_active']:
                return False, "Account is deactivated", None
            
            # Check if user is OAuth user
            if user['auth_provider'] != 'local':
                return False, f"This account uses {user['auth_provider']} sign-in. Please use that method.", None
            
            # Verify password
            if not user['password_hash'] or hash_password(password) != user['password_hash']:
                return False, "Invalid email or password", None
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
            """, (user['id'],))
            
            # Create session token
            session_token = generate_session_token()
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(days=7)  # 7 day session
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            """, (user['id'], session_token, expires_at, ip_address, user_agent))
            
            conn.commit()
            cursor.close()
            
            # Return user data (without password)
            user_data = {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'avatar_url': user['avatar_url'],
                'session_token': session_token
            }
            
            return True, "Login successful", user_data
            
    except Exception as e:
        return False, f"Login failed: {e}", None


def create_session_for_user(user_id: int, ip_address: str = None, user_agent: str = None) -> str:
    """Create a session token for a user (used for OAuth login)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
            """, (user_id,))
            
            # Create session token
            session_token = generate_session_token()
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(days=7)  # 7 day session
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, session_token, expires_at, ip_address, user_agent))
            
            conn.commit()
            cursor.close()
            
            return session_token
            
    except Exception as e:
        print(f"[DB ERROR] Failed to create session: {e}")
        return None


def validate_session(session_token: str) -> Tuple[bool, Optional[Dict]]:
    """Validate session token and return user data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.email, u.name, u.role, u.avatar_url
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.is_valid = 1 AND s.expires_at > CURRENT_TIMESTAMP
            """ if DB_TYPE == 'sqlite' else """
                SELECT u.id, u.email, u.name, u.role, u.avatar_url
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = %s AND s.is_valid = TRUE AND s.expires_at > CURRENT_TIMESTAMP
            """, (session_token,))
            
            row = cursor.fetchone()
            if not row:
                return False, None
            
            user = dict(row) if DB_TYPE == 'sqlite' else {
                'id': row[0], 'email': row[1], 'name': row[2], 'role': row[3], 'avatar_url': row[4]
            }
            
            cursor.close()
            return True, user
            
    except Exception as e:
        print(f"[DB ERROR] Session validation failed: {e}")
        return False, None


def logout_user(session_token: str) -> bool:
    """Invalidate user session"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_sessions SET is_valid = 0 WHERE session_token = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE user_sessions SET is_valid = FALSE WHERE session_token = %s
            """, (session_token,))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Logout failed: {e}")
        return False


# ==================== VIDEO OPERATIONS ====================

def create_video_project(user_id: int, video_id: str, display_name: str, filename: str,
                         original_image: str = None, original_audio: str = None,
                         ref_video: str = None, settings: dict = None) -> bool:
    """Create a new video project record"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO videos (user_id, video_id, display_name, filename, original_image,
                                  original_audio, ref_video, settings, status, progress)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO videos (user_id, video_id, display_name, filename, original_image,
                                  original_audio, ref_video, settings, status, progress)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, video_id, display_name, filename, original_image,
                  original_audio, ref_video, json.dumps(settings) if settings else None,
                  'processing', 0))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to create video project: {e}")
        return False


def update_video_progress(video_id: str, progress: int, message: str = None) -> bool:
    """Update video processing progress"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos SET progress = ?, message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE video_id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE videos SET progress = %s, message = %s
                WHERE video_id = %s
            """, (progress, message, video_id))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to update video progress: {e}")
        return False


def complete_video_project(video_id: str, result_path: str, file_size: int = None, duration: int = None) -> bool:
    """Mark video project as completed"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos 
                SET status = 'completed', progress = 100, result_path = ?, 
                    file_size = ?, duration = ?, completed_at = CURRENT_TIMESTAMP
                WHERE video_id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE videos 
                SET status = 'completed', progress = 100, result_path = %s,
                    file_size = %s, duration = %s, completed_at = CURRENT_TIMESTAMP
                WHERE video_id = %s
            """, (result_path, file_size, duration, video_id))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to complete video project: {e}")
        return False


def fail_video_project(video_id: str, error_message: str) -> bool:
    """Mark video project as failed"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos 
                SET status = 'failed', progress = -1, message = ?
                WHERE video_id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE videos 
                SET status = 'failed', progress = -1, message = %s
                WHERE video_id = %s
            """, (error_message, video_id))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to mark video as failed: {e}")
        return False


def get_user_videos(user_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all videos for a user"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, video_id, display_name, filename, status, progress, message,
                       result_path, file_size, duration, is_favorite, created_at, completed_at
                FROM videos WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT id, video_id, display_name, filename, status, progress, message,
                       result_path, file_size, duration, is_favorite, created_at, completed_at
                FROM videos WHERE user_id = %s
                ORDER BY created_at DESC LIMIT %s OFFSET %s
            """, (user_id, limit, offset))
            
            rows = cursor.fetchall()
            videos = []
            for row in rows:
                if DB_TYPE == 'sqlite':
                    videos.append(dict(row))
                else:
                    videos.append({
                        'id': row[0], 'video_id': row[1], 'display_name': row[2],
                        'filename': row[3], 'status': row[4], 'progress': row[5],
                        'message': row[6], 'result_path': row[7], 'file_size': row[8],
                        'duration': row[9], 'is_favorite': row[10],
                        'created_at': row[11], 'completed_at': row[12]
                    })
            cursor.close()
            return videos
    except Exception as e:
        print(f"[DB ERROR] Failed to get user videos: {e}")
        return []


def get_video_by_id(video_id: str, user_id: int = None) -> Optional[Dict]:
    """Get video by ID, optionally checking user ownership"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    SELECT * FROM videos WHERE video_id = ? AND user_id = ?
                """ if DB_TYPE == 'sqlite' else """
                    SELECT * FROM videos WHERE video_id = %s AND user_id = %s
                """, (video_id, user_id))
            else:
                cursor.execute("""
                    SELECT * FROM videos WHERE video_id = ?
                """ if DB_TYPE == 'sqlite' else """
                    SELECT * FROM videos WHERE video_id = %s
                """, (video_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return dict(row) if DB_TYPE == 'sqlite' else {
                    'id': row[0], 'video_id': row[1], 'user_id': row[2],
                    'display_name': row[3], 'filename': row[4],
                    'status': row[8], 'progress': row[9], 'result_path': row[12]
                }
            return None
    except Exception as e:
        print(f"[DB ERROR] Failed to get video: {e}")
        return None


def delete_video(video_id: str, user_id: int) -> bool:
    """Delete a video project (only if owned by user)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Handle video_id with or without .mp4 extension
            # Strip extension for consistent lookup since DB may store with or without
            video_id_clean = video_id.replace('.mp4', '')
            video_id_with_ext = video_id_clean + '.mp4'

            # First check if video exists and get its info (try both with and without extension)
            cursor.execute("""
                SELECT id, video_id, result_path FROM videos
                WHERE (video_id = ? OR video_id = ?) AND user_id = ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT id, video_id, result_path FROM videos
                WHERE (video_id = %s OR video_id = %s) AND user_id = %s
            """, (video_id_clean, video_id_with_ext, user_id))

            row = cursor.fetchone()
            if not row:
                print(f"[DB] Video not found: {video_id} (tried: {video_id_clean}, {video_id_with_ext}) for user {user_id}")
                cursor.close()
                return False

            # Get the actual video_id from the database for deletion
            actual_video_id = row[1]

            # Delete the video record using the actual ID from DB
            cursor.execute("""
                DELETE FROM videos WHERE video_id = ? AND user_id = ?
            """ if DB_TYPE == 'sqlite' else """
                DELETE FROM videos WHERE video_id = %s AND user_id = %s
            """, (actual_video_id, user_id))
            conn.commit()
            deleted = cursor.rowcount > 0
            cursor.close()

            if deleted:
                print(f"[DB] Video deleted successfully: {actual_video_id}")
            else:
                print(f"[DB] Video deletion failed (no rows affected): {actual_video_id}")

            return deleted
    except Exception as e:
        print(f"[DB ERROR] Failed to delete video: {e}")
        return False


def rename_video(video_id: str, user_id: int, new_name: str) -> bool:
    """Rename a video's display name (only if owned by user)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE videos SET display_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE video_id = ? AND user_id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE videos SET display_name = %s, updated_at = CURRENT_TIMESTAMP
                WHERE video_id = %s AND user_id = %s
            """, (new_name, video_id, user_id))
            conn.commit()
            updated = cursor.rowcount > 0
            cursor.close()
            return updated
    except Exception as e:
        print(f"[DB ERROR] Failed to rename video: {e}")
        return False


# ==================== ADMIN OPERATIONS ====================

def get_all_users() -> List[Dict]:
    """Get all users (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, role, is_active, created_at, last_login, avatar_url,
                       (SELECT COUNT(*) FROM videos WHERE user_id = users.id) as video_count
                FROM users ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            users = []
            for row in rows:
                if DB_TYPE == 'sqlite':
                    users.append(dict(row))
                else:
                    users.append({
                        'id': row[0], 'email': row[1], 'name': row[2],
                        'role': row[3], 'is_active': row[4],
                        'created_at': row[5], 'last_login': row[6],
                        'avatar_url': row[7], 'video_count': row[8]
                    })
            cursor.close()
            return users
    except Exception as e:
        print(f"[DB ERROR] Failed to get users: {e}")
        return []


def get_all_videos(limit: int = 100) -> List[Dict]:
    """Get all videos with user info (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, u.name as user_name, u.email as user_email
                FROM videos v
                JOIN users u ON v.user_id = u.id
                ORDER BY v.created_at DESC LIMIT ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT v.*, u.name as user_name, u.email as user_email
                FROM videos v
                JOIN users u ON v.user_id = u.id
                ORDER BY v.created_at DESC LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            videos = []
            for row in rows:
                if DB_TYPE == 'sqlite':
                    videos.append(dict(row))
                else:
                    videos.append({
                        'id': row[0], 'video_id': row[1], 'user_id': row[2],
                        'display_name': row[3], 'filename': row[4],
                        'original_image': row[5], 'original_audio': row[6],
                        'ref_video': row[7], 'status': row[8],
                        'progress': row[9], 'message': row[10],
                        'settings': row[11], 'result_path': row[12],
                        'file_size': row[13], 'duration': row[14],
                        'is_favorite': row[15], 'created_at': row[16],
                        'updated_at': row[17], 'completed_at': row[18],
                        'user_name': row[19], 'user_email': row[20]
                    })
            cursor.close()
            return videos
    except Exception as e:
        print(f"[DB ERROR] Failed to get all videos: {e}")
        return []


def toggle_user_active(user_id: int, is_active: bool) -> bool:
    """Activate/deactivate user account (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = ? WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET is_active = %s WHERE id = %s
            """, (is_active, user_id))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to toggle user status: {e}")
        return False


def delete_user(user_id: int) -> bool:
    """Delete a user and all their data (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete user (cascading will handle related records)
            cursor.execute("""
                DELETE FROM users WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                DELETE FROM users WHERE id = %s
            """, (user_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            cursor.close()
            return deleted
    except Exception as e:
        print(f"[DB ERROR] Failed to delete user: {e}")
        return False


def update_user_role(user_id: int, role: str) -> bool:
    """Update user role (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET role = ? WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET role = %s WHERE id = %s
            """, (role, user_id))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to update user role: {e}")
        return False


def update_user_email(user_id: int, email: str) -> Tuple[bool, str]:
    """Update user email (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Check if email already exists for another user
            cursor.execute("""
                SELECT id FROM users WHERE email = ? AND id != ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT id FROM users WHERE email = %s AND id != %s
            """, (email, user_id))
            if cursor.fetchone():
                return False, "Email already in use by another user"
            
            cursor.execute("""
                UPDATE users SET email = ? WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET email = %s WHERE id = %s
            """, (email, user_id))
            conn.commit()
            cursor.close()
            return True, "Email updated successfully"
    except Exception as e:
        print(f"[DB ERROR] Failed to update user email: {e}")
        return False, f"Database error: {e}"


def update_user_avatar(user_id: int, avatar_url: str) -> Tuple[bool, str]:
    """Update user avatar URL"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET avatar_url = ? WHERE id = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE users SET avatar_url = %s WHERE id = %s
            """, (avatar_url, user_id))
            conn.commit()
            cursor.close()
            return True, "Avatar updated successfully"
    except Exception as e:
        print(f"[DB ERROR] Failed to update user avatar: {e}")
        return False, f"Database error: {e}"


def update_user_profile(user_id: int, name: str = None, avatar_url: str = None) -> Tuple[bool, str]:
    """Update user profile (name and/or avatar)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?" if DB_TYPE == 'sqlite' else "name = %s")
                params.append(name)
            
            if avatar_url is not None:
                updates.append("avatar_url = ?" if DB_TYPE == 'sqlite' else "avatar_url = %s")
                params.append(avatar_url)
            
            if not updates:
                return False, "No fields to update"
            
            params.append(user_id)
            
            query = f"""
                UPDATE users SET {', '.join(updates)}
                WHERE id = {'?' if DB_TYPE == 'sqlite' else '%s'}
            """
            
            cursor.execute(query, tuple(params))
            conn.commit()
            cursor.close()
            return True, "Profile updated successfully"
    except Exception as e:
        print(f"[DB ERROR] Failed to update user profile: {e}")
        return False, f"Database error: {e}"


def get_system_stats() -> Dict:
    """Get comprehensive system statistics (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # User statistics
            cursor.execute("""
                SELECT COUNT(*) as total_users,
                       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_users,
                       SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_count
                FROM users
            """ if DB_TYPE == 'sqlite' else """
                SELECT COUNT(*) as total_users,
                       SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active_users,
                       SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admin_count
                FROM users
            """)
            row = cursor.fetchone()
            if DB_TYPE == 'sqlite':
                user_stats = dict(row)
            else:
                user_stats = {'total_users': row[0], 'active_users': row[1], 'admin_count': row[2]}
            
            # Video statistics
            cursor.execute("""
                SELECT COUNT(*) as total_videos,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_videos,
                       SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing_videos,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_videos,
                       SUM(file_size) as total_storage
                FROM videos
            """)
            row = cursor.fetchone()
            if DB_TYPE == 'sqlite':
                video_stats = dict(row)
            else:
                video_stats = {
                    'total_videos': row[0], 'completed_videos': row[1],
                    'processing_videos': row[2], 'failed_videos': row[3],
                    'total_storage': row[4] or 0
                }
            
            # Recent activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as recent_videos
                FROM videos
                WHERE created_at >= datetime('now', '-1 day')
            """ if DB_TYPE == 'sqlite' else """
                SELECT COUNT(*) as recent_videos
                FROM videos
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            """)
            row = cursor.fetchone()
            recent_videos = row[0] if DB_TYPE == 'sqlite' else row[0]
            
            # Recent users (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as recent_users
                FROM users
                WHERE created_at >= datetime('now', '-1 day')
            """ if DB_TYPE == 'sqlite' else """
                SELECT COUNT(*) as recent_users
                FROM users
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            """)
            row = cursor.fetchone()
            recent_users = row[0] if DB_TYPE == 'sqlite' else row[0]
            
            cursor.close()
            
            return {
                'users': user_stats,
                'videos': video_stats,
                'recent_videos': recent_videos,
                'recent_users': recent_users
            }
    except Exception as e:
        print(f"[DB ERROR] Failed to get system stats: {e}")
        return {}


# ==================== USER PREFERENCES ====================

def get_user_preferences(user_id: int) -> Dict:
    """Get user preferences"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM user_preferences WHERE user_id = ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT * FROM user_preferences WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return dict(row) if DB_TYPE == 'sqlite' else {
                    'default_preprocess': row[2], 'default_size': row[3],
                    'default_batch_size': row[4], 'default_pose_style': row[5],
                    'default_exp_scale': row[6], 'default_use_enhancer': row[7],
                    'default_use_blink': row[8], 'theme': row[9], 'language': row[10]
                }
            return {}
    except Exception as e:
        print(f"[DB ERROR] Failed to get preferences: {e}")
        return {}


def update_user_preferences(user_id: int, preferences: Dict) -> bool:
    """Update user preferences"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            fields = []
            values = []
            for key, value in preferences.items():
                fields.append(f"{key} = ?" if DB_TYPE == 'sqlite' else f"{key} = %s")
                values.append(value)
            
            if not fields:
                return False
            
            values.append(user_id)
            query = f"UPDATE user_preferences SET {', '.join(fields)} WHERE user_id = ?" if DB_TYPE == 'sqlite' else f"UPDATE user_preferences SET {', '.join(fields)} WHERE user_id = %s"
            
            cursor.execute(query, tuple(values))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to update preferences: {e}")
        return False


# ==================== SYSTEM CONFIGS ====================

def get_system_config(config_key: str) -> Optional[str]:
    """Get system configuration value"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config_value FROM system_configs WHERE config_key = ?
            """ if DB_TYPE == 'sqlite' else """
                SELECT config_value FROM system_configs WHERE config_key = %s
            """, (config_key,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return row[0] if DB_TYPE == 'sqlite' else row[0]
            return None
    except Exception as e:
        print(f"[DB ERROR] Failed to get config: {e}")
        return None


def update_system_config(config_key: str, config_value: str) -> bool:
    """Update system configuration (admin only)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_configs SET config_value = ? WHERE config_key = ?
            """ if DB_TYPE == 'sqlite' else """
                UPDATE system_configs SET config_value = %s WHERE config_key = %s
            """, (config_value, config_key))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to update config: {e}")
        return False


# ==================== USAGE STATISTICS ====================

def log_usage_stat(user_id: int = None, video_id: str = None, action: str = None,
                   processing_time: float = None, gpu_memory_used: float = None) -> bool:
    """Log usage statistics"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
    except:
        cpu_percent = None
        memory_percent = None
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_stats (user_id, video_id, action, processing_time, 
                                        gpu_memory_used, cpu_percent, memory_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """ if DB_TYPE == 'sqlite' else """
                INSERT INTO usage_stats (user_id, video_id, action, processing_time,
                                        gpu_memory_used, cpu_percent, memory_percent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, video_id, action, processing_time, gpu_memory_used,
                  cpu_percent, memory_percent))
            conn.commit()
            cursor.close()
            return True
    except Exception as e:
        print(f"[DB ERROR] Failed to log usage stat: {e}")
        return False


if __name__ == "__main__":
    # Test database initialization
    print("Testing database initialization...")
    init_database()
    print("\nDatabase test complete!")