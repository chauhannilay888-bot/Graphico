"""
Graphico Pro - Utility Functions
Reusable helper functions for the backend application.
"""

import json
import re
import hashlib
import secrets
import logging
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional, Union
from functools import wraps
import time
import unicodedata

from config.settings import (
    MAX_UPLOAD_SIZE_BYTES,
    ALLOWED_UPLOAD_EXTENSIONS,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)
from config.constants import (
    HttpStatus,
    ApiMessage,
    ErrorCode,
    ValidationPatterns,
    ContentType,
    MIME_TYPES,
    FileCategory,
)

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(console_format)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger


# Initialize default logger
logger = setup_logger(__name__)


# ============================================================================
# JSON HELPERS
# ============================================================================

def safe_json_loads(data: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.
    
    Args:
        data: JSON string to parse
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON object or default value
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON parse error: {e}")
        return default


def safe_json_dumps(data: Any, indent: int = 2, default: Any = None) -> str:
    """
    Safely serialize to JSON string with error handling.
    
    Args:
        data: Data to serialize
        indent: JSON indentation
        default: Default value if serialization fails
    
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return default if default is not None else "{}"


def read_json_file(filepath: Path, default: Any = None) -> Any:
    """
    Read and parse a JSON file safely.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Parsed JSON content or default value
    """
    try:
        if not filepath.exists():
            return default
        
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading JSON file {filepath}: {e}")
        return default


def write_json_file(filepath: Path, data: Any) -> bool:
    """
    Write data to a JSON file safely using atomic write pattern.
    
    Args:
        filepath: Path to JSON file
        data: Data to write
    
    Returns:
        True if successful, False otherwise
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temp file first, then rename for atomicity
        temp_filepath = filepath.with_suffix(".tmp")
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        
        temp_filepath.replace(filepath)
        return True
    except (IOError, OSError) as e:
        logger.error(f"Error writing JSON file {filepath}: {e}")
        return False


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    return bool(re.match(ValidationPatterns.EMAIL, email))


def validate_username(username: str) -> bool:
    """
    Validate username format.
    
    Args:
        username: Username to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not username:
        return False
    return bool(re.match(ValidationPatterns.USERNAME, username))


def validate_project_name(name: str) -> bool:
    """
    Validate project name format.
    
    Args:
        name: Project name to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    return bool(re.match(ValidationPatterns.PROJECT_NAME, name))


def validate_file_extension(filename: str) -> bool:
    """
    Validate if file extension is allowed.
    
    Args:
        filename: Filename to check
    
    Returns:
        True if allowed, False otherwise
    """
    if not filename:
        return False
    extension = Path(filename).suffix.lower()
    return extension in ALLOWED_UPLOAD_EXTENSIONS


def validate_file_size(file_size: int) -> bool:
    """
    Validate if file size is within limits.
    
    Args:
        file_size: File size in bytes
    
    Returns:
        True if valid, False otherwise
    """
    return 0 < file_size <= MAX_UPLOAD_SIZE_BYTES


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize a string by stripping whitespace and limiting length.
    
    Args:
        text: Input string
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    return text.strip()[:max_length]


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing unsafe characters, path traversal,
    and ensuring a safe, clean filename.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
    
    Returns:
        Sanitized filename safe for all operating systems
    """
    if not filename:
        return "untitled"
    
    # Normalize unicode characters (é -> e, ü -> u, etc.)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Extract only the filename part (remove any path components)
    filename = Path(filename).name
    
    # Split name and extension
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    
    # Remove leading/trailing dots and spaces from stem
    stem = stem.strip(". ")
    
    # Replace any character that isn't alphanumeric, dash, underscore, or dot
    # with an underscore
    stem = re.sub(r'[^\w\-.]', '_', stem)
    
    # Collapse multiple underscores/dashes
    stem = re.sub(r'_{2,}', '_', stem)
    stem = re.sub(r'-{2,}', '-', stem)
    
    # Remove any path traversal sequences that might remain
    stem = stem.replace('..', '_').replace('/', '_').replace('\\', '_')
    
    # Remove leading dashes (can cause issues with some commands)
    stem = stem.lstrip('-')
    
    # Truncate stem if too long (reserve room for extension)
    max_stem_length = max_length - len(suffix) - 1
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip('_.-')
    
    # Ensure we have a valid stem
    if not stem:
        stem = "untitled"
    
    # Ensure suffix is valid
    if suffix and suffix not in ALLOWED_UPLOAD_EXTENSIONS and len(suffix) > 5:
        suffix = ""
    
    # Combine stem and suffix
    sanitized = stem + suffix
    
    # Final safety check - strip any remaining dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', sanitized)
    
    # Ensure not empty
    if not sanitized.strip('_.-'):
        sanitized = "untitled"
    
    return sanitized


# ============================================================================
# SECURITY HELPERS
# ============================================================================

def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
    
    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(length)


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
    
    Returns:
        Unique ID string (format: prefix_YYYYMMDDHHMMSS_randomhex)
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(8)
    unique_id = f"{timestamp}_{random_part}"
    
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def hash_string(data: str, algorithm: str = "sha256") -> str:
    """
    Create a hash of a string.
    
    Args:
        data: String to hash
        algorithm: Hash algorithm to use (sha256, sha512, md5)
    
    Returns:
        Hex-encoded hash string
    """
    if not data:
        return ""
    
    try:
        hasher = hashlib.new(algorithm)
        hasher.update(data.encode("utf-8"))
        return hasher.hexdigest()
    except ValueError:
        logger.warning(f"Unsupported hash algorithm: {algorithm}, falling back to sha256")
        hasher = hashlib.sha256()
        hasher.update(data.encode("utf-8"))
        return hasher.hexdigest()


def mask_email(email: str) -> str:
    """
    Mask an email address for privacy display.
    
    Args:
        email: Email address to mask
    
    Returns:
        Masked email (e.g., j***@example.com)
    """
    if not email or "@" not in email:
        return email if email else ""
    
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = local
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * min(len(local) - 2, 6) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_string(data: str, visible_start: int = 4, visible_end: int = 4) -> str:
    """
    Mask a sensitive string, showing only start and end characters.
    
    Args:
        data: String to mask
        visible_start: Number of characters visible at start
        visible_end: Number of characters visible at end
    
    Returns:
        Masked string (e.g., "1234...7890")
    """
    if not data:
        return ""
    
    if len(data) <= visible_start + visible_end:
        return "*" * len(data)
    
    return data[:visible_start] + "*" * (len(data) - visible_start - visible_end) + data[-visible_end:]


# ============================================================================
# DATE/TIME HELPERS
# ============================================================================

def get_utc_now() -> datetime:
    """
    Get current UTC datetime with timezone awareness.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


def get_timestamp() -> str:
    """
    Get ISO 8601 format timestamp with timezone.
    
    Returns:
        ISO 8601 formatted timestamp string
    """
    return get_utc_now().isoformat()


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object to string.
    
    Args:
        dt: Datetime object
        fmt: Format string
    
    Returns:
        Formatted datetime string
    """
    if not dt:
        return ""
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.strftime(fmt)


def parse_datetime(date_string: str) -> Optional[datetime]:
    """
    Parse a datetime string into a datetime object.
    Handles multiple ISO formats.
    
    Args:
        date_string: ISO format datetime string
    
    Returns:
        Datetime object or None if parsing fails
    """
    if not date_string:
        return None
    
    try:
        # Handle 'Z' suffix
        if date_string.endswith('Z'):
            date_string = date_string[:-1] + '+00:00'
        
        dt = datetime.fromisoformat(date_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse datetime '{date_string}': {e}")
        return None


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Datetime object (UTC)
    
    Returns:
        Human-readable time difference (e.g., "2 hours ago", "just now")
    """
    if not dt:
        return ""
    
    now = get_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    
    if diff.total_seconds() < 0:
        return "in the future"
    
    if diff.total_seconds() < 10:
        return "just now"
    elif diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())} seconds ago"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff.days == 0:
        hours = int(diff.seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"


def is_expired(timestamp: str, max_age_hours: int = 24) -> bool:
    """
    Check if a timestamp is older than max_age_hours.
    
    Args:
        timestamp: ISO format timestamp
        max_age_hours: Maximum age in hours
    
    Returns:
        True if expired, False otherwise
    """
    dt = parse_datetime(timestamp)
    if not dt:
        return True
    
    age = get_utc_now() - dt
    return age.total_seconds() > (max_age_hours * 3600)


# ============================================================================
# API RESPONSE HELPERS
# ============================================================================

def create_response(
    success: bool = True,
    message: str = "",
    data: Any = None,
    error: Optional[str] = None,
    error_code: Optional[str] = None,
    status_code: int = HttpStatus.OK,
) -> tuple:
    """
    Create a standardized API response tuple.
    
    Args:
        success: Whether the operation was successful
        message: Response message
        data: Response data payload
        error: Error description
        error_code: Error code for debugging
        status_code: HTTP status code
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        "success": success,
        "timestamp": get_timestamp(),
    }
    
    if message:
        response["message"] = message
    
    if data is not None:
        response["data"] = data
    
    if not success:
        if error:
            response["error"] = error
        if error_code:
            response["error_code"] = error_code
    
    return response, status_code


def success_response(
    data: Any = None,
    message: str = ApiMessage.SUCCESS,
    status_code: int = HttpStatus.OK,
) -> tuple:
    """
    Create a standardized success response.
    
    Args:
        data: Response data payload
        message: Success message
        status_code: HTTP status code
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    return create_response(
        success=True,
        message=message,
        data=data,
        status_code=status_code,
    )


def error_response(
    message: str = ApiMessage.INTERNAL_ERROR,
    error_code: Optional[str] = None,
    status_code: int = HttpStatus.INTERNAL_SERVER_ERROR,
    error: Optional[str] = None,
) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        message: User-facing error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        error: Detailed error description
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    return create_response(
        success=False,
        message=message,
        error=error or message,
        error_code=error_code,
        status_code=status_code,
    )


def paginated_response(
    items: list,
    total: int,
    page: int,
    per_page: int,
    message: str = ApiMessage.SUCCESS,
) -> tuple:
    """
    Create a paginated API response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        per_page: Items per page
        message: Response message
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    if per_page <= 0:
        per_page = 20
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    data = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
        },
    }
    
    return success_response(data=data, message=message)


# ============================================================================
# DECORATORS
# ============================================================================

def log_execution_time(func):
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to wrap
    
    Returns:
        Wrapped function with execution timing
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(
                f"{func.__name__} failed after {execution_time:.4f}s: {str(e)}"
            )
            raise
    
    return wrapper


def handle_errors(func):
    """
    Decorator to catch and handle exceptions in route handlers.
    Returns standardized error responses for known exception types.
    
    Args:
        func: Route handler function to wrap
    
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return error_response(
                message=str(e),
                error_code=ErrorCode.VALIDATION_INVALID_FORMAT,
                status_code=HttpStatus.BAD_REQUEST,
            )
        except FileNotFoundError as e:
            logger.warning(f"File not found in {func.__name__}: {str(e)}")
            return error_response(
                message=ApiMessage.FILE_NOT_FOUND,
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                status_code=HttpStatus.NOT_FOUND,
            )
        except PermissionError as e:
            logger.warning(f"Permission error in {func.__name__}: {str(e)}")
            return error_response(
                message=ApiMessage.FORBIDDEN,
                error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                status_code=HttpStatus.FORBIDDEN,
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            return error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
    
    return wrapper


def retry_on_failure(max_retries: int = 3, delay_seconds: float = 1.0, backoff_multiplier: float = 2.0):
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff_multiplier: Multiplier for delay after each retry
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay_seconds
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_multiplier
                    else:
                        logger.error(
                            f"All {max_retries} retries failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    
    return decorator


# ============================================================================
# STRING HELPERS
# ============================================================================

def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated
    
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


def slugify(text: str, max_length: int = 100) -> str:
    """
    Convert text to a URL-friendly slug.
    
    Args:
        text: Text to slugify
        max_length: Maximum slug length
    
    Returns:
        Slugified text (lowercase, hyphen-separated)
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace special characters and spaces with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    # Strip hyphens from ends and limit length
    text = text.strip('-')[:max_length]
    
    return text.strip('-') or "untitled"


def humanize_bytes(bytes_count: int) -> str:
    """
    Convert bytes to human-readable format.
    
    Args:
        bytes_count: Number of bytes
    
    Returns:
        Human-readable string (e.g., "1.5 MB", "512 B")
    """
    if bytes_count is None or bytes_count < 0:
        return "0 B"
    
    if bytes_count == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_count)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    
    return f"{size:.1f} {units[unit_index]}"


def humanize_number(number: int) -> str:
    """
    Convert large numbers to human-readable format with suffixes.
    
    Args:
        number: Number to humanize
    
    Returns:
        Human-readable string (e.g., "1.2K", "3.5M")
    """
    if number is None:
        return "0"
    
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f"{number / 1000:.1f}K"
    elif number < 1000000000:
        return f"{number / 1000000:.1f}M"
    else:
        return f"{number / 1000000000:.1f}B"


def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    Extract basic keywords from text.
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to extract
    
    Returns:
        List of keyword strings
    """
    if not text:
        return []
    
    # Simple word frequency extraction
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Common stop words to exclude
    stop_words = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'are',
        'was', 'were', 'been', 'has', 'had', 'not', 'but', 'all', 'can',
        'which', 'their', 'said', 'will', 'would', 'there', 'they', 'what',
        'when', 'where', 'about', 'into', 'more', 'some', 'than', 'then',
        'also', 'very', 'just', 'like', 'other', 'only', 'new', 'such',
    }
    
    # Count word frequencies
    word_freq = {}
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


# ============================================================================
# FILE HELPERS
# ============================================================================

def get_file_extension(filename: str) -> str:
    """
    Get lowercase file extension with dot.
    
    Args:
        filename: Filename or path
    
    Returns:
        Lowercase extension with dot (e.g., '.pdf', '.docx')
        Empty string if no extension
    """
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def get_mime_type(filename: str) -> str:
    """
    Get MIME type for a file based on its extension.
    
    Args:
        filename: Filename or path
    
    Returns:
        MIME type string (e.g., 'application/pdf', 'image/png')
        'application/octet-stream' if extension not recognized
    """
    extension = get_file_extension(filename)
    
    if not extension:
        return "application/octet-stream"
    
    return MIME_TYPES.get(extension, "application/octet-stream")


def get_file_category(filename: str) -> str:
    """
    Determine file category based on extension.
    
    Args:
        filename: Filename or path
    
    Returns:
        Category string from FileCategory enum
    """
    extension = get_file_extension(filename)
    
    category_map = {
        # Documents
        ".pdf": FileCategory.DOCUMENT.value,
        ".docx": FileCategory.DOCUMENT.value,
        ".txt": FileCategory.DOCUMENT.value,
        
        # Spreadsheets
        ".csv": FileCategory.SPREADSHEET.value,
        ".xlsx": FileCategory.SPREADSHEET.value,
        
        # Presentations
        ".pptx": FileCategory.PRESENTATION.value,
        
        # Images
        ".png": FileCategory.IMAGE.value,
        ".jpg": FileCategory.IMAGE.value,
        ".jpeg": FileCategory.IMAGE.value,
        ".gif": FileCategory.IMAGE.value,
        ".webp": FileCategory.IMAGE.value,
        
        # Code
        ".py": FileCategory.CODE.value,
        ".js": FileCategory.CODE.value,
        ".html": FileCategory.CODE.value,
        ".css": FileCategory.CODE.value,
        
        # Data
        ".json": FileCategory.DATA.value,
        ".xml": FileCategory.DATA.value,
        ".zip": FileCategory.DATA.value,
    }
    
    return category_map.get(extension, FileCategory.DOCUMENT.value)


def ensure_directory(path: Path) -> bool:
    """
    Ensure a directory exists, creating it and all parent directories if necessary.
    
    Args:
        path: Directory path to ensure
    
    Returns:
        True if directory exists or was created, False on failure
    """
    if path is None:
        logger.error("ensure_directory called with None path")
        return False
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError as e:
        logger.error(f"Permission denied creating directory {path}: {e}")
        return False
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def clean_temp_files(directory: Path, max_age_hours: int = 24) -> int:
    """
    Remove temporary files older than specified age.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files in hours
    
    Returns:
        Number of files removed
    """
    if not directory or not directory.exists():
        return 0
    
    cutoff_time = get_utc_now() - timedelta(hours=max_age_hours)
    removed_count = 0
    
    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                try:
                    file_mtime = datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    )
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
                        logger.debug(f"Removed temp file: {file_path}")
                except OSError as e:
                    logger.warning(f"Could not remove temp file {file_path}: {e}")
    except OSError as e:
        logger.error(f"Error cleaning temp files in {directory}: {e}")
    
    if removed_count > 0:
        logger.info(f"Cleaned {removed_count} temporary files from {directory}")
    
    return removed_count


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
    
    Returns:
        File size in MB, or 0 if file doesn't exist
    """
    if not file_path or not file_path.exists():
        return 0.0
    
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0


def is_file_type_allowed(filename: str) -> bool:
    """
    Check if file type is in allowed extensions list.
    
    Args:
        filename: Filename to check
    
    Returns:
        True if file type is allowed
    """
    extension = get_file_extension(filename)
    return extension.lower() in ALLOWED_UPLOAD_EXTENSIONS


def safe_path_join(base_dir: Path, *paths: str) -> Optional[Path]:
    """
    Safely join paths, preventing directory traversal attacks.
    
    Args:
        base_dir: Base directory that the result must be within
        *paths: Path components to join
    
    Returns:
        Resolved path if it's within base_dir, None otherwise
    """
    if not base_dir:
        return None
    
    try:
        base_dir = base_dir.resolve()
        full_path = base_dir.joinpath(*paths).resolve()
        
        # Ensure the resolved path is within base_dir
        if str(full_path).startswith(str(base_dir)):
            return full_path
        
        logger.warning(f"Path traversal attempt blocked: {full_path} not in {base_dir}")
        return None
    except (ValueError, OSError) as e:
        logger.error(f"Invalid path: {e}")
        return None


# ============================================================================
# MISCELLANEOUS HELPERS
# ============================================================================

def get_client_ip(request) -> str:
    """
    Extract client IP address from request, checking proxy headers.
    
    Args:
        request: Flask/HTTP request object
    
    Returns:
        Client IP address string, or 'unknown' if not determinable
    """
    if request is None:
        return "unknown"
    
    # Check various proxy headers in order of trust
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        return x_forwarded_for.split(",")[0].strip()
    
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()
    
    # Fall back to direct remote address
    if hasattr(request, 'remote_addr'):
        return request.remote_addr or "unknown"
    
    return "unknown"


def merge_dicts(dict1: dict, dict2: dict, max_depth: int = 10) -> dict:
    """
    Deep merge two dictionaries. Values from dict2 override dict1.
    
    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (takes precedence)
        max_depth: Maximum recursion depth to prevent stack overflow
    
    Returns:
        Merged dictionary
    """
    if max_depth <= 0:
        return dict2 if dict2 is not None else dict1
    
    if dict1 is None:
        return dict2.copy() if dict2 else {}
    if dict2 is None:
        return dict1.copy()
    
    result = dict1.copy()
    
    for key, value in dict2.items():
        if (key in result and 
            isinstance(result[key], dict) and 
            isinstance(value, dict)):
            result[key] = merge_dicts(result[key], value, max_depth - 1)
        else:
            result[key] = value
    
    return result


def chunk_list(items: list, chunk_size: int) -> list:
    """
    Split a list into chunks of specified size.
    
    Args:
        items: List to chunk
        chunk_size: Maximum size of each chunk
    
    Returns:
        List of chunk lists
    """
    if not items or chunk_size < 1:
        return []
    
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def pluck(dict_list: list, key: str, default: Any = None) -> list:
    """
    Extract a specific key from a list of dictionaries.
    
    Args:
        dict_list: List of dictionaries
        key: Key to extract
        default: Default value if key not found
    
    Returns:
        List of values for the specified key
    """
    if not dict_list:
        return []
    
    return [d.get(key, default) for d in dict_list if isinstance(d, dict)]


def group_by(items: list, key: str) -> dict:
    """
    Group a list of dictionaries by a specific key.
    
    Args:
        items: List of dictionaries
        key: Key to group by
    
    Returns:
        Dictionary mapping key values to lists of items
    """
    if not items:
        return {}
    
    grouped = {}
    for item in items:
        if isinstance(item, dict):
            group_key = item.get(key)
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(item)
    
    return grouped


def remove_none_values(d: dict) -> dict:
    """
    Recursively remove None values from a dictionary.
    
    Args:
        d: Dictionary to clean
    
    Returns:
        Dictionary with None values removed
    """
    if not isinstance(d, dict):
        return d
    
    cleaned = {}
    for key, value in d.items():
        if isinstance(value, dict):
            nested = remove_none_values(value)
            if nested:
                cleaned[key] = nested
        elif value is not None:
            cleaned[key] = value
    
    return cleaned


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid URL
    """
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    
    return bool(url_pattern.match(url))


def safe_get(obj: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.
    
    Args:
        obj: Dictionary to traverse
        *keys: Sequence of keys to follow
        default: Default value if any key is missing
    
    Returns:
        Value at the nested key path, or default
    """
    if not obj:
        return default
    
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    
    return current


def to_bool(value: Any) -> bool:
    """
    Convert various string representations to boolean.
    
    Args:
        value: Value to convert
    
    Returns:
        Boolean interpretation of the value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    return bool(value)


def to_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default