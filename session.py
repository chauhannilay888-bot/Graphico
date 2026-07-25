"""
Graphico Pro - Session Management
Handles user sessions, authentication state, and session persistence.
Provides decorators for route protection with reliable request detection.
"""

import json
import logging
import inspect
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from functools import wraps

from flask import request, g, has_request_context

from config.settings import (
    SESSION_SECRET_KEY,
    SESSION_EXPIRY_HOURS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    DATABASE_PATH,
)
from config.constants import (
    HttpStatus,
    ApiMessage,
    ErrorCode,
    HeaderNames,
)
from backend.utils import (
    generate_token,
    hash_string,
    get_utc_now,
    get_timestamp,
    read_json_file,
    write_json_file,
    create_response,
    success_response,
    error_response,
    ensure_directory,
    logger as utils_logger,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SESSION STORAGE
# ============================================================================

class SessionStore:
    """
    Manages session persistence using JSON file storage.
    Provides thread-safe session creation, retrieval, validation, and deletion.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize session store.
        
        Args:
            storage_path: Path to session storage file.
                         Defaults to database/sessions.json
        """
        if storage_path is None:
            storage_path = DATABASE_PATH / "sessions.json"
        
        self.storage_path = storage_path
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._load_sessions()
    
    def _load_sessions(self) -> None:
        """Load sessions from disk into memory and clean expired ones."""
        try:
            ensure_directory(self.storage_path.parent)
            self._sessions = read_json_file(self.storage_path, {})
            self._clean_expired_sessions()
            logger.info(f"Loaded {len(self._sessions)} active sessions from storage")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            self._sessions = {}
    
    def _save_sessions(self) -> bool:
        """
        Persist sessions to disk atomically.
        
        Returns:
            True if successful, False otherwise
        """
        ensure_directory(self.storage_path.parent)
        success = write_json_file(self.storage_path, self._sessions)
        if not success:
            logger.error("Failed to save sessions to disk")
        return success
    
    def _parse_expiry(self, expires_at_str: Optional[str]) -> Optional[datetime]:
        """
        Parse an ISO format expiration string to timezone-aware datetime.
        
        Args:
            expires_at_str: ISO 8601 datetime string
        
        Returns:
            Timezone-aware datetime or None if parsing fails
        """
        if not expires_at_str:
            return None
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return expires_at
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse expiry timestamp '{expires_at_str}': {e}")
            return None
    
    def _clean_expired_sessions(self) -> None:
        """Remove expired sessions from memory and persist changes."""
        now = get_utc_now()
        expired_tokens = []
        
        for token, session_data in self._sessions.items():
            expires_at = self._parse_expiry(session_data.get("expires_at"))
            
            if expires_at is None:
                # Invalid expiry format - remove session
                expired_tokens.append(token)
            elif now >= expires_at:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self._sessions[token]
        
        if expired_tokens:
            logger.info(f"Cleaned {len(expired_tokens)} expired sessions")
            self._save_sessions()
    
    def create_session(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new session for a user.
        
        Args:
            user_data: User information dictionary with:
                - user_id (required)
                - email (required)
                - name (optional)
                - picture (optional)
                - role (optional, default 'user')
                - provider (optional, default 'google')
                - ip_address (optional)
                - user_agent (optional)
        
        Returns:
            Session token string if successful, None otherwise
        """
        try:
            # Validate required fields
            if not user_data.get("user_id") or not user_data.get("email"):
                logger.error("Cannot create session: missing user_id or email")
                return None
            
            # Generate unique session token (96 character hex = 48 bytes)
            token = generate_token(48)
            
            # Set expiration
            now = get_utc_now()
            expires_at = now + timedelta(hours=SESSION_EXPIRY_HOURS)
            
            # Create session record
            session_data = {
                "token": token,
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "name": user_data.get("name", ""),
                "picture": user_data.get("picture", ""),
                "role": user_data.get("role", "user"),
                "provider": user_data.get("provider", "google"),
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_activity": now.isoformat(),
                "ip_address": user_data.get("ip_address", ""),
                "user_agent": user_data.get("user_agent", ""),
                "is_active": True,
            }
            
            # Store session
            self._sessions[token] = session_data
            self._save_sessions()
            
            logger.info(
                f"Session created for user: {user_data.get('email')} "
                f"(expires: {expires_at.isoformat()})"
            )
            return token
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}", exc_info=True)
            return None
    
    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and validate a session by token.
        Automatically updates last activity timestamp.
        
        Args:
            token: Session token string
        
        Returns:
            Session data copy if valid and active, None otherwise
        """
        if not token:
            return None
        
        # Get session from memory
        session_data = self._sessions.get(token)
        
        if not session_data:
            logger.debug(f"Session not found: {token[:16]}...")
            return None
        
        # Check if session is marked inactive
        if not session_data.get("is_active", False):
            logger.debug(f"Session is inactive: {token[:16]}...")
            return None
        
        # Check expiration
        expires_at = self._parse_expiry(session_data.get("expires_at"))
        
        if expires_at is None:
            # Invalid expiry - delete session
            logger.warning(f"Session has invalid expiry: {token[:16]}...")
            self.delete_session(token)
            return None
        
        if get_utc_now() >= expires_at:
            logger.debug(f"Session expired: {token[:16]}...")
            self.delete_session(token)
            return None
        
        # Update last activity timestamp
        session_data["last_activity"] = get_utc_now().isoformat()
        self._sessions[token] = session_data
        
        # Periodically save (every ~10 updates) to reduce disk I/O
        # For simplicity, we save on every read - atomic writes handle this well
        
        return session_data.copy()
    
    def refresh_session(self, token: str) -> bool:
        """
        Extend session expiration time from now.
        
        Args:
            token: Session token string
        
        Returns:
            True if refreshed successfully, False otherwise
        """
        session_data = self._sessions.get(token)
        
        if not session_data:
            return False
        
        if not session_data.get("is_active", False):
            return False
        
        # Check if session is already expired
        expires_at = self._parse_expiry(session_data.get("expires_at"))
        if expires_at and get_utc_now() >= expires_at:
            self.delete_session(token)
            return False
        
        # Extend expiration
        new_expires_at = get_utc_now() + timedelta(hours=SESSION_EXPIRY_HOURS)
        session_data["expires_at"] = new_expires_at.isoformat()
        session_data["last_activity"] = get_utc_now().isoformat()
        
        self._sessions[token] = session_data
        self._save_sessions()
        
        logger.debug(f"Session refreshed: {token[:16]}... (expires: {new_expires_at.isoformat()})")
        return True
    
    def delete_session(self, token: str) -> bool:
        """
        Delete a session (logout).
        
        Args:
            token: Session token string
        
        Returns:
            True if deleted, False if not found
        """
        if token in self._sessions:
            del self._sessions[token]
            self._save_sessions()
            logger.info(f"Session deleted: {token[:16]}...")
            return True
        
        return False
    
    def deactivate_session(self, token: str) -> bool:
        """
        Mark a session as inactive without deleting it.
        
        Args:
            token: Session token string
        
        Returns:
            True if deactivated successfully
        """
        session_data = self._sessions.get(token)
        
        if not session_data:
            return False
        
        session_data["is_active"] = False
        session_data["deactivated_at"] = get_utc_now().isoformat()
        
        self._sessions[token] = session_data
        self._save_sessions()
        
        return True
    
    def delete_all_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a specific user (logout from all devices).
        
        Args:
            user_id: User ID
        
        Returns:
            Number of sessions deleted
        """
        tokens_to_delete = []
        
        for token, session_data in self._sessions.items():
            if session_data.get("user_id") == user_id:
                tokens_to_delete.append(token)
        
        for token in tokens_to_delete:
            del self._sessions[token]
        
        if tokens_to_delete:
            self._save_sessions()
            logger.info(
                f"Deleted {len(tokens_to_delete)} sessions for user: {user_id}"
            )
        
        return len(tokens_to_delete)
    
    def get_active_sessions_count(self) -> int:
        """
        Get count of currently active sessions.
        
        Returns:
            Number of active, non-expired sessions
        """
        self._clean_expired_sessions()
        return len(self._sessions)
    
    def get_user_session_count(self, user_id: str) -> int:
        """
        Get count of active sessions for a specific user.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of active sessions for the user
        """
        count = 0
        for session_data in self._sessions.values():
            if (session_data.get("user_id") == user_id and 
                session_data.get("is_active", False)):
                count += 1
        return count
    
    def get_user_sessions(self, user_id: str) -> list:
        """
        Get all active sessions for a user (for session management UI).
        
        Args:
            user_id: User ID
        
        Returns:
            List of sanitized session data (no tokens)
        """
        sessions = []
        for session_data in self._sessions.values():
            if (session_data.get("user_id") == user_id and 
                session_data.get("is_active", False)):
                # Return sanitized session info (no full token)
                sessions.append({
                    "created_at": session_data.get("created_at"),
                    "expires_at": session_data.get("expires_at"),
                    "last_activity": session_data.get("last_activity"),
                    "ip_address": session_data.get("ip_address"),
                    "user_agent": session_data.get("user_agent", "")[:100],
                })
        
        # Sort by last activity, most recent first
        sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        return sessions


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Manages session lifecycle and provides authentication middleware.
    Singleton pattern ensures consistent session management across the app.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize session manager (only once)."""
        if self._initialized:
            return
        
        self._store = SessionStore()
        self._initialized = True
        logger.info("SessionManager initialized")
    
    @property
    def store(self) -> SessionStore:
        """Get the session store instance."""
        return self._store
    
    def create_session(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new session for a user.
        
        Args:
            user_data: User information dictionary
        
        Returns:
            Session token if successful, None otherwise
        """
        return self.store.create_session(user_data)
    
    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get validated session by token.
        
        Args:
            token: Session token
        
        Returns:
            Session data if valid, None otherwise
        """
        return self.store.get_session(token)
    
    def delete_session(self, token: str) -> bool:
        """
        Delete a session.
        
        Args:
            token: Session token
        
        Returns:
            True if deleted successfully
        """
        return self.store.delete_session(token)
    
    def refresh_session(self, token: str) -> bool:
        """
        Refresh session expiration.
        
        Args:
            token: Session token
        
        Returns:
            True if refreshed successfully
        """
        return self.store.refresh_session(token)
    
    def extract_token(self, request_obj=None) -> Optional[str]:
        """
        Extract session token from Flask request.
        Checks multiple locations in order of priority.
        
        Priority:
        1. Authorization: Bearer <token> header
        2. X-Session-Token header
        3. Session cookie
        
        Args:
            request_obj: Flask request object (uses global request if None)
        
        Returns:
            Session token string if found, None otherwise
        """
        if request_obj is None:
            if not has_request_context():
                logger.debug("No Flask request context available for token extraction")
                return None
            request_obj = request
        
        # 1. Check Authorization header (Bearer token)
        auth_header = request_obj.headers.get(HeaderNames.AUTHORIZATION, "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                logger.debug("Token extracted from Authorization header")
                return token
        
        # 2. Check custom session header
        session_header = request_obj.headers.get(HeaderNames.X_SESSION_TOKEN, "")
        if session_header:
            token = session_header.strip()
            if token:
                logger.debug("Token extracted from X-Session-Token header")
                return token
        
        # 3. Check cookies
        cookie_token = request_obj.cookies.get(SESSION_COOKIE_NAME, "")
        if cookie_token:
            token = cookie_token.strip()
            if token:
                logger.debug("Token extracted from session cookie")
                return token
        
        logger.debug("No session token found in request")
        return None
    
    def authenticate_request(self, request_obj=None) -> tuple:
        """
        Authenticate a request and return user session.
        
        Args:
            request_obj: Flask request object (uses global request if None)
        
        Returns:
            Tuple of (session_data_dict, error_response_tuple)
            - If authenticated: (session_data, None)
            - If not authenticated: (None, (error_dict, status_code))
        """
        token = self.extract_token(request_obj)
        
        if not token:
            return None, error_response(
                message=ApiMessage.UNAUTHORIZED,
                error_code=ErrorCode.AUTH_MISSING_TOKEN,
                status_code=HttpStatus.UNAUTHORIZED,
            )
        
        session_data = self.get_session(token)
        
        if not session_data:
            return None, error_response(
                message=ApiMessage.SESSION_EXPIRED,
                error_code=ErrorCode.AUTH_EXPIRED_TOKEN,
                status_code=HttpStatus.UNAUTHORIZED,
            )
        
        # Store session in Flask g for request duration
        if has_request_context():
            g.session_token = token
            g.user_session = session_data
        
        return session_data, None
    
    def set_session_cookie(self, response, token: str) -> None:
        """
        Set session cookie on a Flask response object.
        
        Args:
            response: Flask response object
            token: Session token to set in cookie
        """
        response.set_cookie(
            SESSION_COOKIE_NAME,
            token,
            max_age=SESSION_EXPIRY_HOURS * 3600,
            secure=SESSION_COOKIE_SECURE,
            httponly=SESSION_COOKIE_HTTPONLY,
            samesite=SESSION_COOKIE_SAMESITE,
            path="/",
        )
    
    def clear_session_cookie(self, response) -> None:
        """
        Clear session cookie from a Flask response object.
        
        Args:
            response: Flask response object
        """
        response.delete_cookie(
            SESSION_COOKIE_NAME,
            path="/",
            secure=SESSION_COOKIE_SECURE,
            httponly=SESSION_COOKIE_HTTPONLY,
            samesite=SESSION_COOKIE_SAMESITE,
        )


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def _get_request_from_args(args, kwargs) -> Optional[Any]:
    """
    Extract Flask request object from function arguments.
    
    Tries multiple strategies to find the request:
    1. Check if 'request' is in kwargs
    2. Check if any arg is a Flask request object
    3. Use Flask's global request proxy
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
    
    Returns:
        Flask request object or None
    """
    # Strategy 1: Check kwargs for 'request'
    if 'request' in kwargs:
        return kwargs['request']
    
    # Strategy 2: Check positional args for a Flask request-like object
    for arg in args:
        if hasattr(arg, 'headers') and hasattr(arg, 'cookies') and hasattr(arg, 'method'):
            return arg
    
    # Strategy 3: Use Flask's global request context
    if has_request_context():
        return request
    
    return None


def _extract_request_from_flask_context() -> Optional[Any]:
    """
    Extract request from Flask's application context.
    
    This is the most reliable method as it uses Flask's built-in
    request proxy which is always available during request handling.
    
    Returns:
        Flask request object or None
    """
    try:
        if has_request_context():
            return request
    except RuntimeError:
        pass
    
    return None


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for route handlers.
    
    Authenticates the request and injects the user session as a
    keyword argument 'user_session' into the decorated function.
    
    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route(user_session=None):
            user_id = user_session.get('user_id')
            ...
    
    The Flask route decorator must be applied BEFORE this decorator:
        Correct:   @app.route(...) then @require_auth
        Incorrect: @require_auth then @app.route(...)
    
    Args:
        func: Route handler function to wrap
    
    Returns:
        Wrapped function with authentication check
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get request from Flask context (most reliable method)
        flask_request = _extract_request_from_flask_context()
        
        if flask_request is None:
            logger.error(
                f"@require_auth: No Flask request context available for {func.__name__}"
            )
            return error_response(
                message="Internal server error: No request context",
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
        
        # Check if this is an OPTIONS request (CORS preflight)
        if flask_request.method == "OPTIONS":
            # Skip authentication for preflight requests
            return func(*args, **kwargs)
        
        # Authenticate the request
        session_manager = get_session_manager()
        user_session, error = session_manager.authenticate_request(flask_request)
        
        if error:
            return error
        
        # Inject user_session as keyword argument
        kwargs['user_session'] = user_session
        
        return func(*args, **kwargs)
    
    # Store reference to original function for debugging
    wrapper.__wrapped__ = func
    wrapper._require_auth = True
    
    return wrapper


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for routes that work with or without authentication.
    
    Attempts to authenticate the request. If successful, injects
    'user_session' with user data. If not, 'user_session' will be None.
    
    Usage:
        @app.route('/api/content')
        @optional_auth
        def content_route(user_session=None):
            if user_session:
                # Handle authenticated user
                ...
            else:
                # Handle anonymous user
                ...
    
    Args:
        func: Route handler function to wrap
    
    Returns:
        Wrapped function with optional authentication
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get request from Flask context
        flask_request = _extract_request_from_flask_context()
        
        if flask_request is None:
            logger.error(
                f"@optional_auth: No Flask request context available for {func.__name__}"
            )
            # Continue without auth since it's optional
            kwargs['user_session'] = None
            return func(*args, **kwargs)
        
        # Check if this is an OPTIONS request (CORS preflight)
        if flask_request.method == "OPTIONS":
            kwargs['user_session'] = None
            return func(*args, **kwargs)
        
        # Attempt authentication
        session_manager = get_session_manager()
        user_session, _ = session_manager.authenticate_request(flask_request)
        
        # user_session will be None if authentication fails (expected)
        kwargs['user_session'] = user_session
        
        return func(*args, **kwargs)
    
    # Store reference to original function for debugging
    wrapper.__wrapped__ = func
    wrapper._optional_auth = True
    
    return wrapper


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin-level authentication.
    
    Must be used together with @require_auth (stacked).
    
    Usage:
        @app.route('/api/admin/users')
        @require_admin
        @require_auth
        def admin_route(user_session=None):
            ...
    
    Args:
        func: Route handler function to wrap
    
    Returns:
        Wrapped function with admin check
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_session = kwargs.get('user_session')
        
        if not user_session:
            return error_response(
                message=ApiMessage.UNAUTHORIZED,
                error_code=ErrorCode.AUTH_MISSING_TOKEN,
                status_code=HttpStatus.UNAUTHORIZED,
            )
        
        if user_session.get('role') != 'admin':
            return error_response(
                message="Admin access required",
                error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                status_code=HttpStatus.FORBIDDEN,
            )
        
        return func(*args, **kwargs)
    
    wrapper.__wrapped__ = func
    wrapper._require_admin = True
    
    return wrapper


# ============================================================================
# SESSION UTILITY FUNCTIONS
# ============================================================================

def get_session_user_id(session_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Safely extract user ID from session data.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        User ID string or None
    """
    return session_data.get("user_id") if session_data else None


def get_session_email(session_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Safely extract email from session data.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        Email string or None
    """
    return session_data.get("email") if session_data else None


def get_session_name(session_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Safely extract user display name from session data.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        User name string or None
    """
    return session_data.get("name") if session_data else None


def get_session_role(session_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Safely extract user role from session data.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        Role string or None
    """
    return session_data.get("role") if session_data else None


def is_session_admin(session_data: Optional[Dict[str, Any]]) -> bool:
    """
    Check if session belongs to an admin user.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        True if user is admin
    """
    if not session_data:
        return False
    return session_data.get("role") == "admin"


def is_authenticated(session_data: Optional[Dict[str, Any]]) -> bool:
    """
    Check if session data indicates an authenticated user.
    
    Args:
        session_data: Session data dictionary or None
    
    Returns:
        True if user is authenticated
    """
    return session_data is not None and "user_id" in session_data


def sanitize_session_for_client(session_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Remove sensitive/internal fields from session data for client transmission.
    
    Args:
        session_data: Full session data dictionary
    
    Returns:
        Sanitized dictionary safe for sending to frontend
    """
    if not session_data:
        return {}
    
    # Only include fields that are safe for the client
    safe_fields = [
        "user_id",
        "email",
        "name",
        "picture",
        "role",
        "provider",
        "created_at",
    ]
    
    sanitized = {}
    for field in safe_fields:
        if field in session_data:
            sanitized[field] = session_data[field]
    
    return sanitized


def get_current_user_from_g() -> Optional[Dict[str, Any]]:
    """
    Get the current user session from Flask's g object.
    This is set by authenticate_request() when authentication succeeds.
    
    Returns:
        User session data if authenticated, None otherwise
    """
    if has_request_context():
        return getattr(g, 'user_session', None)
    return None


def get_current_token_from_g() -> Optional[str]:
    """
    Get the current session token from Flask's g object.
    
    Returns:
        Session token if authenticated, None otherwise
    """
    if has_request_context():
        return getattr(g, 'session_token', None)
    return None


# ============================================================================
# GLOBAL SESSION MANAGER
# ============================================================================

# Lazy-loaded global session manager instance
_session_manager_instance = None


def get_session_manager() -> SessionManager:
    """
    Get or create the global SessionManager singleton.
    
    Returns:
        SessionManager instance
    """
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance


# Pre-initialize for backward compatibility
session_manager = get_session_manager()