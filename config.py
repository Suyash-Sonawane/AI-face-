"""
SadTalker Configuration Module
Manages environment-based configuration for local and cloud development
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).parent.absolute()

# ==================== DATABASE CONFIGURATION ====================

def get_database_config():
    """
    Get database configuration based on environment.
    Priority: Environment Variables > Config File > Defaults
    """
    # Check if running in cloud/tunnel environment
    is_cloud = os.getenv('CLOUD_ENV', 'false').lower() == 'true'
    
    # Check for explicit database type preference
    db_type = os.getenv('DB_TYPE', 'mysql' if is_cloud else 'sqlite')
    
    config = {
        'DB_TYPE': db_type,
        'IS_CLOUD': is_cloud
    }
    
    if db_type == 'mysql':
        # MySQL Configuration (for cloud/shared environments)
        config.update({
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'Suyash@261$'),
            'database': os.getenv('DB_NAME', 'sadtalker_db'),
            'autocommit': True,
            # Connection pooling settings
            'pool_name': 'sadtalker_pool',
            'pool_size': 5,
            'pool_reset_session': True,
        })
    else:
        # SQLite Configuration (for local development)
        # Store in a persistent location that won't be reset
        db_path = os.getenv('SQLITE_PATH', str(BASE_DIR / 'data' / 'sadtalker.db'))
        config['DB_PATH'] = db_path
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return config


# ==================== FILE STORAGE CONFIGURATION ====================

def get_storage_config():
    """
    Get file storage configuration.
    Uses persistent paths that won't be reset across sessions.
    """
    # Base storage directory - use a persistent location
    if os.getenv('CLOUD_ENV', 'false').lower() == 'true':
        # Cloud environment - use persistent storage path
        base_storage = Path(os.getenv('STORAGE_PATH', '/var/lib/sadtalker'))
    else:
        # Local development - use project directory but in a 'data' subfolder
        base_storage = Path(os.getenv('STORAGE_PATH', str(BASE_DIR / 'data')))
    
    # Ensure base directory exists
    base_storage.mkdir(parents=True, exist_ok=True)
    
    config = {
        'BASE_STORAGE': str(base_storage),
        'UPLOAD_DIR': str(base_storage / 'uploads'),
        'RESULT_DIR': str(base_storage / 'results'),
        'PREVIEW_DIR': str(base_storage / 'previews'),
        'TEMP_DIR': str(base_storage / 'temp'),
    }
    
    # Create all directories
    for path in config.values():
        if path != str(base_storage):  # Skip base, already created
            os.makedirs(path, exist_ok=True)
    
    return config


# ==================== SESSION CONFIGURATION ====================

def get_session_config():
    """Get session and authentication configuration"""
    return {
        'SESSION_TIMEOUT_DAYS': int(os.getenv('SESSION_TIMEOUT_DAYS', 7)),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'sadtalker-dev-secret-key-change-in-production'),
        'TOKEN_LENGTH': 32,
    }


# ==================== APPLICATION CONFIGURATION ====================

def get_app_config():
    """Get general application configuration"""
    return {
        'DEBUG': os.getenv('DEBUG', 'true').lower() == 'true',
        'HOST': os.getenv('HOST', '0.0.0.0'),  # Allow external connections for tunnels
        'PORT': int(os.getenv('PORT', 7860)),
        'MAX_CONTENT_LENGTH': int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024)),  # 500MB
    }


# ==================== INITIALIZATION CHECK ====================

def check_environment():
    """
    Check and display current environment configuration
    """
    db_config = get_database_config()
    storage_config = get_storage_config()
    
    print("\n" + "="*70)
    print(" SadTalker Environment Configuration")
    print("="*70)
    print(f"\n[ENV] Database Type: {db_config['DB_TYPE'].upper()}")
    print(f"[ENV] Cloud Environment: {'Yes' if db_config['IS_CLOUD'] else 'No'}")
    
    if db_config['DB_TYPE'] == 'mysql':
        print(f"[ENV] MySQL Host: {db_config['host']}:{db_config['port']}")
        print(f"[ENV] MySQL Database: {db_config['database']}")
    else:
        print(f"[ENV] SQLite Path: {db_config['DB_PATH']}")
    
    print(f"\n[ENV] Storage Base: {storage_config['BASE_STORAGE']}")
    print(f"[ENV] Uploads: {storage_config['UPLOAD_DIR']}")
    print(f"[ENV] Results: {storage_config['RESULT_DIR']}")
    print("="*70 + "\n")
    
    return db_config, storage_config


# Load configurations
DB_CONFIG = get_database_config()
STORAGE_CONFIG = get_storage_config()
SESSION_CONFIG = get_session_config()
APP_CONFIG = get_app_config()

if __name__ == "__main__":
    check_environment()