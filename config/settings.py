"""
Graphico Pro - Centralized Configuration Settings
Production-grade settings management with environment variable support.

SECURITY WARNING:
    This file contains default values for development ONLY.
    In production, ALL secret keys and credentials MUST be set via
    environment variables. Never commit real secrets to version control.

Usage:
    All settings can be overridden by setting environment variables
    before starting the server. Use the .env file for local development.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
# .env should NEVER be committed to version control
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to load from current working directory as fallback
    load_dotenv()

# ============================================================================
# BASE DIRECTORY
# ============================================================================

# Absolute path to the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8501"))

# WARNING: Never enable DEBUG in production
SERVER_DEBUG = os.getenv("SERVER_DEBUG", "False").lower() == "true"

# Number of worker threads for the development server
SERVER_WORKERS = int(os.getenv("SERVER_WORKERS", "4"))

# Secret key for Flask session signing
# WARNING: CHANGE THIS IN PRODUCTION - Use a strong random value
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY = os.getenv(
    "FLASK_SECRET_KEY",
    "graphico-pro-flask-secret-key-DEV-ONLY-change-in-production"
)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

# Origins allowed to make cross-origin requests to the API
ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://graphico.streamlit.app",
    "https://graphico-backend.streamlit.app"
]

# HTTP methods allowed for CORS requests
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

# HTTP headers allowed for CORS requests
ALLOWED_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "X-Session-Token",
    "X-Request-ID",
]

# Allow credentials (cookies, authorization headers) in CORS requests
ALLOWED_CREDENTIALS = True

# ============================================================================
# GOOGLE OAUTH CONFIGURATION
# ============================================================================

# Google OAuth 2.0 Client ID
# This is public and can be in version control
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "578730974907-criqtv67ocspqdo84b568sj13tiqgv1t.apps.googleusercontent.com"
)

# Google OAuth 2.0 Client Secret
# WARNING: THIS MUST BE SET VIA ENVIRONMENT VARIABLE IN PRODUCTION
# NEVER commit the actual secret to version control
# Get it from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Allowed redirect URIs (must match Google Cloud Console configuration)
GOOGLE_REDIRECT_URIS = [
    "http://localhost:5500",
    "https://graphico.streamlit.app",
    "https://graphico-backend.streamlit.app"
]

# Google OAuth 2.0 endpoints
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_CERTS_URI = "https://www.googleapis.com/oauth2/v3/certs"

# OAuth scopes requested from Google
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# ============================================================================
# CSRF / STATE PROTECTION
# ============================================================================

# Secret used to sign OAuth state tokens for CSRF protection
# WARNING: CHANGE THIS IN PRODUCTION - Use a strong random value
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
OAUTH_STATE_SECRET = os.getenv(
    "OAUTH_STATE_SECRET",
    "graphico-oauth-state-secret-DEV-ONLY-change-in-production"
)

# Maximum age of OAuth state tokens in seconds (10 minutes)
OAUTH_STATE_MAX_AGE_SECONDS = int(os.getenv("OAUTH_STATE_MAX_AGE_SECONDS", "600"))

# ============================================================================
# SESSION CONFIGURATION
# ============================================================================

# Secret key for signing session tokens
# WARNING: CHANGE THIS IN PRODUCTION - Use a strong random value
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET_KEY = os.getenv(
    "SESSION_SECRET_KEY",
    "graphico-pro-session-secret-DEV-ONLY-change-in-production"
)

# Session expiration time in hours (default: 24 hours)
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# Session cookie name
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "graphico_session")

# Cookie security settings
# WARNING: Set SESSION_COOKIE_SECURE=True in production (HTTPS only)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_HTTPONLY = True  # Always True - prevent JavaScript access
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

# Maximum sessions per user (prevents session flooding)
MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", "10"))

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database backend type: "json" | "sqlite" | "postgresql"
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "json")

# Base directory for all database files
DATABASE_PATH = BASE_DIR / "database" / "data"

# JSON Database file paths (current default)
JSON_USERS_FILE = DATABASE_PATH / "users.json"
JSON_PROJECTS_FILE = DATABASE_PATH / "projects.json"
JSON_HISTORY_FILE = DATABASE_PATH / "history.json"
JSON_SESSIONS_FILE = DATABASE_PATH / "sessions.json"
JSON_OAUTH_STATES_FILE = DATABASE_PATH / "oauth_states.json"

# SQLite configuration (future)
SQLITE_DATABASE_PATH = DATABASE_PATH / "graphico.db"

# PostgreSQL configuration (future)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "graphico")
POSTGRES_USER = os.getenv("POSTGRES_USER", "graphico_user")
# WARNING: NEVER set a default PostgreSQL password - must be set via env
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# ============================================================================
# AI PROVIDER CONFIGURATION
# ============================================================================

# WARNING: API keys must ALWAYS be set via environment variables
# Never hardcode API keys or commit them to version control

# GitHub Models (free GPT-4o via Azure)
GITHUB_MODELS_API_KEY = os.getenv("GITHUB_MODELS_API_KEY", "")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Anthropic (Claude) API key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Google AI (Gemini) API key
GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")

# Stability AI API key (image generation)
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# Replicate API key
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# DeepSeek API key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================

# Maximum allowed file upload size in megabytes
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Allowed file extensions for upload
ALLOWED_UPLOAD_EXTENSIONS = [
    # Documents
    ".pdf", ".docx", ".txt", ".rtf", ".odt",
    # Spreadsheets
    ".csv", ".xlsx", ".ods",
    # Presentations
    ".pptx", ".odp",
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    # Code
    ".py", ".js", ".html", ".css", ".json", ".xml", ".yaml", ".yml",
    # Archives
    ".zip", ".tar", ".gz",
]

# Upload storage directory
UPLOAD_DIRECTORY = BASE_DIR / "uploads"

# Temporary files directory (cleaned periodically)
TEMP_DIRECTORY = BASE_DIR / "temp"

# ============================================================================
# EXPORT CONFIGURATION
# ============================================================================

# Export output directory
EXPORT_DIRECTORY = BASE_DIR / "exports"

# Supported export formats
EXPORT_FORMATS = ["pdf", "pptx", "docx", "txt", "json", "csv", "markdown", "html"]

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log level: DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Log message format
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)

# Log file path
LOG_FILE = BASE_DIR / "logs" / "graphico.log"

# Log rotation: maximum file size before rotation (10 MB)
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))

# Log rotation: number of backup files to keep
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# ============================================================================
# RATE LIMITING
# ============================================================================

# Enable or disable rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"

# Number of requests allowed per time window
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))

# Time window in seconds
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# ============================================================================
# CACHE CONFIGURATION
# ============================================================================

# Enable or disable caching
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"

# Cache time-to-live in seconds (default: 5 minutes)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

# Maximum number of cache entries
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# Bcrypt hashing rounds for password hashing (if needed in future)
BCRYPT_ROUNDS = 12

# Enable CSRF protection
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "True").lower() == "true"

# Maximum request body size (10 MB)
MAX_REQUEST_SIZE_BYTES = int(os.getenv(
    "MAX_REQUEST_SIZE_BYTES",
    str(10 * 1024 * 1024)
))

# Request timeout in seconds
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

# ============================================================================
# BUSINESS LOGIC CONSTANTS
# ============================================================================

# Maximum number of projects per user
MAX_PROJECTS_PER_USER = int(os.getenv("MAX_PROJECTS_PER_USER", "50"))

# Maximum number of files per project
MAX_FILES_PER_PROJECT = int(os.getenv("MAX_FILES_PER_PROJECT", "100"))

# Maximum chat history messages per project
MAX_CHAT_HISTORY_LENGTH = int(os.getenv("MAX_CHAT_HISTORY_LENGTH", "500"))

# Maximum PDF file size for analysis in megabytes
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "25"))

# Maximum image generation resolution
MAX_IMAGE_GENERATION_RESOLUTION = os.getenv(
    "MAX_IMAGE_GENERATION_RESOLUTION",
    "2048x2048"
)

# Maximum AI prompt length in characters
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "4000"))

# ============================================================================
# DIRECTORY MANAGEMENT
# ============================================================================

# List of all directories that must exist for the application to function
REQUIRED_DIRECTORIES = [
    DATABASE_PATH,
    UPLOAD_DIRECTORY,
    TEMP_DIRECTORY,
    EXPORT_DIRECTORY,
    BASE_DIR / "logs",
    BASE_DIR / "models",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_database_config() -> dict:
    """
    Return the current database configuration as a dictionary.
    
    Returns:
        Dictionary with database type and connection details
    """
    config = {
        "type": DATABASE_TYPE,
        "path": str(DATABASE_PATH),
    }
    
    if DATABASE_TYPE == "json":
        config["json"] = {
            "users_file": str(JSON_USERS_FILE),
            "projects_file": str(JSON_PROJECTS_FILE),
            "history_file": str(JSON_HISTORY_FILE),
            "sessions_file": str(JSON_SESSIONS_FILE),
            "oauth_states_file": str(JSON_OAUTH_STATES_FILE),
        }
    elif DATABASE_TYPE == "sqlite":
        config["sqlite"] = {
            "path": str(SQLITE_DATABASE_PATH),
        }
    elif DATABASE_TYPE == "postgresql":
        config["postgresql"] = {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "database": POSTGRES_DATABASE,
            "user": POSTGRES_USER,
            "password_set": bool(POSTGRES_PASSWORD),
        }
    
    return config


def get_ai_providers() -> dict:
    """
    Return available AI providers and their configuration status.
    
    Returns:
        Dictionary mapping provider names to boolean (configured or not)
    """
    return {
        "github_models": bool(GITHUB_MODELS_API_KEY),
        "deepseek": bool(DEEPSEEK_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "google_ai": bool(GOOGLE_AI_API_KEY),
        "stability": bool(STABILITY_API_KEY),
        "replicate": bool(REPLICATE_API_KEY),
    }


def get_configured_ai_providers() -> list:
    """
    Return list of configured AI provider names.
    
    Returns:
        List of provider name strings that have API keys set
    """
    providers = get_ai_providers()
    return [name for name, configured in providers.items() if configured]


def ensure_directories_exist() -> bool:
    """
    Create all required directories if they don't exist.
    
    Returns:
        True if all directories exist or were created successfully,
        False if any directory creation failed
    """
    all_ok = True
    
    for directory in REQUIRED_DIRECTORIES:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"ERROR: Failed to create directory {directory}: {e}")
            all_ok = False
    
    # Also ensure .gitkeep files exist to track empty directories
    for directory in REQUIRED_DIRECTORIES:
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            try:
                gitkeep.touch()
            except OSError:
                pass  # Not critical
    
    return all_ok


def is_production() -> bool:
    """
    Check if the server is running in production mode.
    
    Returns:
        True if SERVER_DEBUG is False (production), False otherwise
    """
    return not SERVER_DEBUG


def validate_configuration() -> list:
    """
    Validate the current configuration and return a list of issues.
    
    Checks for:
    - Missing or default secret keys (critical in production)
    - Missing API credentials
    - Directory existence
    - Configuration consistency
    
    Returns:
        List of warning/error message strings
        Messages prefixed with "ERROR:" indicate critical issues
        Messages prefixed with "WARNING:" indicate non-critical issues
    """
    issues = []
    
    # Check for default secret keys (critical in production)
    default_secrets = {
        "FLASK_SECRET_KEY": "graphico-pro-flask-secret-key-DEV-ONLY-change-in-production",
        "SESSION_SECRET_KEY": "graphico-pro-session-secret-DEV-ONLY-change-in-production",
        "OAUTH_STATE_SECRET": "graphico-oauth-state-secret-DEV-ONLY-change-in-production",
    }
    
    for key_name, default_value in default_secrets.items():
        current_value = globals().get(key_name, "")
        if current_value == default_value:
            if is_production():
                issues.append(
                    f"ERROR: {key_name} is using the default value. "
                    f"This is a critical security risk in production."
                )
            else:
                issues.append(
                    f"WARNING: {key_name} is using the default value. "
                    f"Change this before deploying to production."
                )
    
    # Check Google OAuth configuration
    if not GOOGLE_CLIENT_SECRET:
        if is_production():
            issues.append(
                "ERROR: GOOGLE_CLIENT_SECRET is not set. "
                "Google OAuth will not work."
            )
        else:
            issues.append(
                "WARNING: GOOGLE_CLIENT_SECRET is not set. "
                "Google OAuth will not work until configured."
            )
    
    if not GOOGLE_CLIENT_ID:
        issues.append("ERROR: GOOGLE_CLIENT_ID is not configured.")
    
    # Check AI provider configuration
    providers = get_ai_providers()
    configured_providers = [name for name, ok in providers.items() if ok]
    
    if not configured_providers:
        issues.append(
            "WARNING: No AI providers are configured. "
            "AI features (chat, image generation, etc.) will not work. "
            "Set at least one API key."
        )
    
    # Check directory existence
    missing_dirs = []
    for directory in REQUIRED_DIRECTORIES:
        if not directory.exists():
            missing_dirs.append(str(directory))
    
    if missing_dirs:
        issues.append(
            f"WARNING: Some directories are missing and will be created: "
            f"{', '.join(missing_dirs)}"
        )
    
    # Check database configuration
    if DATABASE_TYPE == "postgresql" and not POSTGRES_PASSWORD:
        issues.append(
            "WARNING: PostgreSQL is selected but POSTGRES_PASSWORD is not set."
        )
    
    # Check session security in production
    if is_production():
        if not SESSION_COOKIE_SECURE:
            issues.append(
                "WARNING: SESSION_COOKIE_SECURE is False. "
                "Session cookies will be sent over HTTP. "
                "Enable this in production with HTTPS."
            )
    
    return issues


def get_config_summary() -> dict:
    """
    Get a summary of the current configuration for display purposes.
    Sensitive values are masked.
    
    Returns:
        Dictionary with configuration summary
    """
    return {
        "server": {
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "debug": SERVER_DEBUG,
            "production": is_production(),
        },
        "database": {
            "type": DATABASE_TYPE,
            "path": str(DATABASE_PATH),
        },
        "ai_providers": get_ai_providers(),
        "oauth": {
            "client_id_configured": bool(GOOGLE_CLIENT_ID),
            "client_secret_configured": bool(GOOGLE_CLIENT_SECRET),
            "redirect_uris": GOOGLE_REDIRECT_URIS,
        },
        "session": {
            "expiry_hours": SESSION_EXPIRY_HOURS,
            "cookie_secure": SESSION_COOKIE_SECURE,
            "cookie_samesite": SESSION_COOKIE_SAMESITE,
        },
        "uploads": {
            "max_size_mb": MAX_UPLOAD_SIZE_MB,
            "allowed_extensions_count": len(ALLOWED_UPLOAD_EXTENSIONS),
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": str(LOG_FILE),
        },
        "rate_limiting": {
            "enabled": RATE_LIMIT_ENABLED,
            "requests_per_window": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
        },
    }


def print_configuration_report() -> None:
    """
    Print a formatted configuration report to the console.
    Useful for debugging and deployment verification.
    """
    summary = get_config_summary()
    configured_providers = get_configured_ai_providers()
    
    print("\n" + "=" * 60)
    print("GRAPHICO PRO - CONFIGURATION REPORT")
    print("=" * 60)
    print(f"  Environment:     {'PRODUCTION' if is_production() else 'DEVELOPMENT'}")
    print(f"  Server:          {summary['server']['host']}:{summary['server']['port']}")
    print(f"  Database:        {summary['database']['type']}")
    print(f"  AI Providers:    {len(configured_providers)} configured")
    for provider in configured_providers:
        print(f"    - {provider}")
    print(f"  OAuth Client ID: {'Configured' if summary['oauth']['client_id_configured'] else 'MISSING'}")
    print(f"  OAuth Secret:    {'Configured' if summary['oauth']['client_secret_configured'] else 'MISSING'}")
    print(f"  Session Expiry:  {summary['session']['expiry_hours']} hours")
    print(f"  Max Upload:      {summary['uploads']['max_size_mb']} MB")
    print(f"  Log Level:       {summary['logging']['level']}")
    print("=" * 60)
    
    issues = validate_configuration()
    if issues:
        print("\nCONFIGURATION ISSUES:")
        for issue in issues:
            print(f"  {issue}")
        print("")
