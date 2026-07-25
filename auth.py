"""
Graphico Pro - Authentication Module
Handles Google OAuth 2.0 authentication flow with CSRF protection and user management.
"""

import json
import logging
import secrets
import hashlib
import time
import requests
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URIS,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_URI,
    GOOGLE_USERINFO_URI,
    GOOGLE_SCOPES,
    ALLOWED_ORIGINS,
    SERVER_DEBUG,
    SESSION_EXPIRY_HOURS,
)
from config.constants import (
    HttpStatus,
    ApiMessage,
    ErrorCode,
    UserRole,
    ContentType,
)
from backend.utils import (
    generate_id,
    generate_token,
    get_utc_now,
    get_timestamp,
    read_json_file,
    write_json_file,
    create_response,
    success_response,
    error_response,
    validate_email,
    hash_string,
    mask_email,
    ensure_directory,
    logger as utils_logger,
)
from backend.session import (
    session_manager,
    sanitize_session_for_client,
    get_session_manager,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CSRF STATE STORE
# ============================================================================

class CSRFStateStore:
    """
    Manages OAuth CSRF state tokens for protection against CSRF attacks.
    Stores state tokens with expiration and automatic cleanup.
    """
    
    def __init__(self):
        """Initialize CSRF state store."""
        from config.settings import DATABASE_PATH
        self.states_file = DATABASE_PATH / "oauth_states.json"
        self._states: Dict[str, Dict[str, Any]] = {}
        self._state_ttl_seconds = 600  # 10 minutes
        self._load_states()
    
    def _load_states(self) -> None:
        """Load states from disk and clean expired ones."""
        try:
            ensure_directory(self.states_file.parent)
            self._states = read_json_file(self.states_file, {})
            self._clean_expired_states()
            logger.debug(f"Loaded {len(self._states)} OAuth state tokens")
        except Exception as e:
            logger.error(f"Failed to load OAuth states: {e}")
            self._states = {}
    
    def _save_states(self) -> bool:
        """Save states to disk."""
        ensure_directory(self.states_file.parent)
        return write_json_file(self.states_file, self._states)
    
    def _clean_expired_states(self) -> None:
        """Remove expired state tokens."""
        now = time.time()
        expired_keys = []
        
        for state, state_data in self._states.items():
            created_at = state_data.get("created_at", 0)
            if now - created_at > self._state_ttl_seconds:
                expired_keys.append(state)
        
        for key in expired_keys:
            del self._states[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired OAuth state tokens")
            self._save_states()
    
    def generate_state(self, redirect_uri: Optional[str] = None) -> str:
        """
        Generate a new CSRF state token.
        
        Args:
            redirect_uri: Optional redirect URI associated with this state
        
        Returns:
            CSRF state token string
        """
        self._clean_expired_states()
        
        # Generate cryptographically secure state token
        random_bytes = secrets.token_bytes(32)
        state = hashlib.sha256(random_bytes).hexdigest()
        
        # Store state with metadata
        self._states[state] = {
            "state": state,
            "redirect_uri": redirect_uri,
            "created_at": time.time(),
            "created_at_iso": get_timestamp(),
            "used": False,
        }
        
        self._save_states()
        logger.debug(f"Generated OAuth state token (total active: {len(self._states)})")
        
        return state
    
    def validate_state(self, state: str, redirect_uri: Optional[str] = None) -> bool:
        """
        Validate a CSRF state token.
        
        Args:
            state: State token to validate
            redirect_uri: Expected redirect URI (optional)
        
        Returns:
            True if state is valid and not expired, False otherwise
        """
        if not state:
            logger.warning("CSRF validation failed: Empty state token")
            return False
        
        # Clean expired states first
        self._clean_expired_states()
        
        # Check if state exists
        state_data = self._states.get(state)
        
        if not state_data:
            logger.warning(f"CSRF validation failed: State token not found")
            return False
        
        # Check if already used (prevent replay attacks)
        if state_data.get("used", False):
            logger.warning(f"CSRF validation failed: State token already used")
            return False
        
        # Check expiration
        created_at = state_data.get("created_at", 0)
        if time.time() - created_at > self._state_ttl_seconds:
            logger.warning(f"CSRF validation failed: State token expired")
            del self._states[state]
            self._save_states()
            return False
        
        # Optional: Verify redirect URI matches
        if redirect_uri and state_data.get("redirect_uri"):
            stored_redirect = state_data["redirect_uri"]
            if stored_redirect != redirect_uri:
                logger.warning(
                    f"CSRF validation failed: Redirect URI mismatch "
                    f"(expected: {stored_redirect}, got: {redirect_uri})"
                )
                return False
        
        # Mark state as used (one-time use)
        state_data["used"] = True
        state_data["used_at"] = time.time()
        state_data["used_at_iso"] = get_timestamp()
        self._states[state] = state_data
        self._save_states()
        
        logger.info("CSRF state token validated successfully")
        return True
    
    def invalidate_state(self, state: str) -> bool:
        """
        Manually invalidate a state token.
        
        Args:
            state: State token to invalidate
        
        Returns:
            True if state was found and invalidated
        """
        if state in self._states:
            del self._states[state]
            self._save_states()
            return True
        return False
    
    def get_active_state_count(self) -> int:
        """Get count of active (unused, unexpired) state tokens."""
        self._clean_expired_states()
        return sum(1 for s in self._states.values() if not s.get("used", False))


# ============================================================================
# USER STORE
# ============================================================================

class UserStore:
    """
    Manages user persistence using JSON file storage.
    Handles user creation, retrieval, and updates.
    """
    
    def __init__(self):
        """Initialize user store."""
        from config.settings import JSON_USERS_FILE
        self.users_file = JSON_USERS_FILE
        self._users: Dict[str, Dict[str, Any]] = {}
        self._load_users()
    
    def _load_users(self) -> None:
        """Load users from disk into memory."""
        try:
            ensure_directory(self.users_file.parent)
            self._users = read_json_file(self.users_file, {})
            logger.info(f"Loaded {len(self._users)} users from storage")
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            self._users = {}
    
    def _save_users(self) -> bool:
        """
        Persist users to disk with atomic write.
        
        Returns:
            True if successful, False otherwise
        """
        ensure_directory(self.users_file.parent)
        return write_json_file(self.users_file, self._users)
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User data copy if found, None otherwise
        """
        user = self._users.get(user_id)
        return user.copy() if user else None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user by email address (case-insensitive).
        
        Args:
            email: User email address
        
        Returns:
            User data copy if found, None otherwise
        """
        if not email:
            return None
        
        email_lower = email.lower().strip()
        
        for user_data in self._users.values():
            if user_data.get("email", "").lower() == email_lower:
                return user_data.copy()
        
        return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user by Google account ID.
        
        Args:
            google_id: Google account ID (sub claim)
        
        Returns:
            User data copy if found, None otherwise
        """
        if not google_id:
            return None
        
        for user_data in self._users.values():
            if user_data.get("google_id") == google_id:
                return user_data.copy()
        
        return None
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new user account.
        
        Args:
            user_data: User information dictionary with:
                - email (required)
                - name (optional)
                - picture (optional)
                - google_id (optional)
                - provider (optional, default 'google')
        
        Returns:
            Created user data if successful, None otherwise
        """
        try:
            # Validate email
            email = user_data.get("email", "").lower().strip()
            if not email or not validate_email(email):
                logger.error(f"Invalid email for user creation: {email}")
                return None
            
            # Check for existing user
            if self.get_user_by_email(email):
                logger.warning(f"User already exists with email: {mask_email(email)}")
                return None
            
            # Generate unique user ID
            user_id = generate_id("usr")
            now = get_timestamp()
            
            # Prepare user record
            new_user = {
                "user_id": user_id,
                "email": email,
                "name": user_data.get("name", "").strip(),
                "picture": user_data.get("picture", ""),
                "google_id": user_data.get("google_id", ""),
                "role": user_data.get("role", UserRole.USER.value),
                "provider": user_data.get("provider", "google"),
                "is_active": True,
                "is_verified": user_data.get("is_verified", True),
                "created_at": now,
                "updated_at": now,
                "last_login": now,
                "login_count": 1,
                "preferences": user_data.get("preferences", {}),
                "metadata": user_data.get("metadata", {}),
            }
            
            # Store user
            self._users[user_id] = new_user
            self._save_users()
            
            logger.info(f"User created: {mask_email(email)} (ID: {user_id})")
            return new_user.copy()
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user information.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
        
        Returns:
            Updated user data if successful, None otherwise
        """
        user = self._users.get(user_id)
        
        if not user:
            logger.warning(f"User not found for update: {user_id}")
            return None
        
        # Prevent updating sensitive/protected fields
        protected_fields = ["user_id", "created_at", "google_id", "provider"]
        for field in protected_fields:
            updates.pop(field, None)
        
        # Apply updates
        user.update(updates)
        user["updated_at"] = get_timestamp()
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User updated: {user_id}")
        return user.copy()
    
    def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp and increment login count.
        
        Args:
            user_id: User ID
        
        Returns:
            True if updated successfully
        """
        user = self._users.get(user_id)
        
        if not user:
            return False
        
        user["last_login"] = get_timestamp()
        user["login_count"] = user.get("login_count", 0) + 1
        user["updated_at"] = get_timestamp()
        
        self._users[user_id] = user
        self._save_users()
        
        return True
    
    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account (soft delete).
        
        Args:
            user_id: User ID
        
        Returns:
            True if deactivated successfully
        """
        user = self._users.get(user_id)
        
        if not user:
            return False
        
        user["is_active"] = False
        user["updated_at"] = get_timestamp()
        user["deactivated_at"] = get_timestamp()
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User deactivated: {user_id}")
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """
        Reactivate a deactivated user account.
        
        Args:
            user_id: User ID
        
        Returns:
            True if activated successfully
        """
        user = self._users.get(user_id)
        
        if not user:
            return False
        
        user["is_active"] = True
        user["updated_at"] = get_timestamp()
        user.pop("deactivated_at", None)
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User activated: {user_id}")
        return True
    
    def user_exists(self, email: str) -> bool:
        """
        Check if a user exists by email.
        
        Args:
            email: User email address
        
        Returns:
            True if user exists
        """
        return self.get_user_by_email(email) is not None
    
    def get_all_users(self, include_inactive: bool = False) -> list:
        """
        Get all users.
        
        Args:
            include_inactive: Whether to include deactivated users
        
        Returns:
            List of user data dictionaries
        """
        users = []
        for user in self._users.values():
            if include_inactive or user.get("is_active", False):
                users.append(user.copy())
        return users
    
    def get_active_users_count(self) -> int:
        """
        Get count of active users.
        
        Returns:
            Number of active users
        """
        return sum(1 for user in self._users.values() if user.get("is_active", False))
    
    def get_total_users_count(self) -> int:
        """
        Get total count of all users.
        
        Returns:
            Total number of users
        """
        return len(self._users)


# ============================================================================
# GOOGLE OAUTH SERVICE
# ============================================================================

class GoogleOAuthService:
    """
    Handles Google OAuth 2.0 authentication flow.
    Manages authorization URLs, token exchange, and user info retrieval.
    """
    
    def __init__(self):
        """Initialize Google OAuth service with configuration."""
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uris = GOOGLE_REDIRECT_URIS
        self.token_uri = GOOGLE_TOKEN_URI
        self.auth_uri = GOOGLE_AUTH_URI
        self.userinfo_uri = GOOGLE_USERINFO_URI
        self.scopes = GOOGLE_SCOPES
        self.csrf_store = CSRFStateStore()
        
        # Validate configuration
        if not self.client_secret and not SERVER_DEBUG:
            logger.warning("Google Client Secret is not configured - OAuth will not work")
        if not self.client_id:
            logger.error("Google Client ID is not configured")
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        generate_state: bool = True,
    ) -> Tuple[str, Optional[str]]:
        """
        Generate Google OAuth authorization URL with CSRF protection.
        
        Args:
            state: Optional pre-generated state token
            redirect_uri: Optional custom redirect URI
            generate_state: Whether to auto-generate a CSRF state token
        
        Returns:
            Tuple of (authorization_url, state_token)
            The state_token should be stored by the client and sent back during callback
        """
        if redirect_uri is None:
            redirect_uri = self.redirect_uris[0]
        
        # Generate CSRF state token if not provided
        csrf_state = state
        if generate_state and not csrf_state:
            csrf_state = self.csrf_store.generate_state(redirect_uri)
        
        # Build authorization URL parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        
        # Add state parameter for CSRF protection
        if csrf_state:
            params["state"] = csrf_state
        
        auth_url = f"{self.auth_uri}?{urlencode(params)}"
        
        logger.debug(
            f"Generated authorization URL with redirect: {redirect_uri}, "
            f"state: {'present' if csrf_state else 'none'}"
        )
        
        return auth_url, csrf_state
    
    def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Google
            redirect_uri: Redirect URI used in authorization (must match)
        
        Returns:
            Token response dictionary if successful, None otherwise
        
        Token response contains:
            - access_token: Short-lived access token
            - refresh_token: Long-lived refresh token (only on first authorization)
            - id_token: JWT ID token
            - expires_in: Token expiration in seconds
            - token_type: Usually "Bearer"
            - scope: Granted scopes
        """
        if redirect_uri is None:
            redirect_uri = self.redirect_uris[0]
        
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = requests.post(
                self.token_uri,
                data=token_data,
                headers={
                    "Content-Type": ContentType.FORM,
                    "Accept": ContentType.JSON,
                },
                timeout=15,
            )
            
            if response.status_code == 200:
                token_response = response.json()
                logger.info("Successfully exchanged authorization code for tokens")
                return token_response
            else:
                error_detail = "Unknown error"
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = response.text
                
                logger.error(
                    f"Token exchange failed: HTTP {response.status_code} - {error_detail}"
                )
                return None
                
        except requests.Timeout:
            logger.error("Token exchange request timed out")
            return None
        except requests.ConnectionError as e:
            logger.error(f"Token exchange connection error: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Token exchange request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse token response: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Google using access token.
        
        Args:
            access_token: Google access token
        
        Returns:
            User info dictionary if successful, None otherwise
        
        User info contains:
            - sub: Google account ID
            - email: User email
            - email_verified: Whether email is verified
            - name: Full name
            - given_name: First name
            - family_name: Last name
            - picture: Profile picture URL
            - locale: User locale
        """
        try:
            response = requests.get(
                self.userinfo_uri,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": ContentType.JSON,
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Retrieved user info for: {mask_email(user_info.get('email', ''))}")
                return user_info
            else:
                logger.error(
                    f"User info request failed: HTTP {response.status_code} - {response.text}"
                )
                return None
                
        except requests.Timeout:
            logger.error("User info request timed out")
            return None
        except requests.ConnectionError as e:
            logger.error(f"User info connection error: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"User info request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse user info response: {e}")
            return None
    
    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token (for client-side authentication flow).
        
        Args:
            id_token: Google ID token JWT from client-side auth
        
        Returns:
            Decoded token payload if valid, None otherwise
        
        Note: This uses Google's tokeninfo endpoint for verification.
        For production, consider using google-auth library's verify_oauth2_token.
        """
        if not id_token:
            return None
        
        try:
            # Verify token with Google's tokeninfo endpoint
            verify_url = "https://oauth2.googleapis.com/tokeninfo"
            response = requests.get(
                verify_url,
                params={"id_token": id_token},
                timeout=10,
            )
            
            if response.status_code == 200:
                token_info = response.json()
                
                # Verify the token is issued for our client
                audience = token_info.get("aud")
                if audience == self.client_id:
                    logger.info(f"ID token verified for: {mask_email(token_info.get('email', ''))}")
                    return token_info
                else:
                    logger.error(
                        f"ID token audience mismatch. Expected: {self.client_id}, Got: {audience}"
                    )
                    return None
            else:
                error_detail = "Unknown error"
                try:
                    error_detail = response.json()
                except Exception:
                    error_detail = response.text
                logger.error(f"ID token verification failed: HTTP {response.status_code} - {error_detail}")
                return None
                
        except requests.Timeout:
            logger.error("ID token verification timed out")
            return None
        except requests.ConnectionError as e:
            logger.error(f"ID token verification connection error: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"ID token verification request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ID token response: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an expired access token using refresh token.
        
        Args:
            refresh_token: Google refresh token
        
        Returns:
            New token response if successful, None otherwise
        """
        if not refresh_token:
            return None
        
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            response = requests.post(
                self.token_uri,
                data=token_data,
                headers={
                    "Content-Type": ContentType.FORM,
                    "Accept": ContentType.JSON,
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                token_response = response.json()
                logger.info("Successfully refreshed access token")
                return token_response
            else:
                logger.error(
                    f"Token refresh failed: HTTP {response.status_code} - {response.text}"
                )
                return None
                
        except requests.Timeout:
            logger.error("Token refresh request timed out")
            return None
        except requests.ConnectionError as e:
            logger.error(f"Token refresh connection error: {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            return None
    
    def validate_csrf_state(self, state: str, redirect_uri: Optional[str] = None) -> bool:
        """
        Validate CSRF state token from OAuth callback.
        
        Args:
            state: State token from callback
            redirect_uri: Expected redirect URI
        
        Returns:
            True if state is valid
        """
        return self.csrf_store.validate_state(state, redirect_uri)


# ============================================================================
# AUTHENTICATION SERVICE
# ============================================================================

class AuthService:
    """
    High-level authentication service.
    Combines OAuth flows with user management and session creation.
    """
    
    def __init__(self):
        """Initialize authentication service."""
        self.user_store = UserStore()
        self.google_oauth = GoogleOAuthService()
        self.session_mgr = get_session_manager()
        logger.info("AuthService initialized")
    
    def authenticate_with_google(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
        state: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        validate_state: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple]]:
        """
        Complete Google OAuth authentication flow with CSRF protection.
        
        Args:
            code: Authorization code from Google callback
            redirect_uri: Redirect URI used in authorization
            state: CSRF state token from callback (validated if provided)
            ip_address: Client IP address for session
            user_agent: Client user agent for session
            validate_state: Whether to validate CSRF state (recommended)
        
        Returns:
            Tuple of (user_data_dict, error_response_tuple)
            
            On success, user_data contains:
                - user: Sanitized user profile
                - session_token: Session token for API requests
                - access_token: Google access token
                - refresh_token: Google refresh token (may be None)
                - expires_in: Token expiration in seconds
        """
        try:
            # Step 0: Validate CSRF state token (anti-CSRF protection)
            if validate_state and state:
                if not self.google_oauth.validate_csrf_state(state, redirect_uri):
                    return None, error_response(
                        message="Invalid or expired state token. Possible CSRF attack.",
                        error_code=ErrorCode.AUTH_GOOGLE_FAILED,
                        status_code=HttpStatus.UNAUTHORIZED,
                        error="CSRF state validation failed",
                    )
            elif validate_state and not state:
                logger.warning("No CSRF state token provided in callback")
                # In production, you might want to reject requests without state
                # For now, we log it but continue (backward compatibility)
            
            # Step 1: Exchange authorization code for tokens
            token_response = self.google_oauth.exchange_code_for_token(
                code, redirect_uri
            )
            
            if not token_response:
                return None, error_response(
                    message=ApiMessage.GOOGLE_AUTH_FAILED,
                    error_code=ErrorCode.AUTH_GOOGLE_FAILED,
                    status_code=HttpStatus.UNAUTHORIZED,
                    error="Failed to exchange authorization code for tokens",
                )
            
            access_token = token_response.get("access_token")
            refresh_token = token_response.get("refresh_token")
            id_token = token_response.get("id_token")
            expires_in = token_response.get("expires_in", 3600)
            
            if not access_token:
                return None, error_response(
                    message=ApiMessage.GOOGLE_AUTH_FAILED,
                    error_code=ErrorCode.AUTH_GOOGLE_FAILED,
                    status_code=HttpStatus.UNAUTHORIZED,
                    error="No access token received from Google",
                )
            
            # Step 2: Get user info from Google
            user_info = self.google_oauth.get_user_info(access_token)
            
            if not user_info:
                return None, error_response(
                    message=ApiMessage.GOOGLE_AUTH_FAILED,
                    error_code=ErrorCode.AUTH_GOOGLE_FAILED,
                    status_code=HttpStatus.UNAUTHORIZED,
                    error="Failed to retrieve user information from Google",
                )
            
            # Extract user details
            google_id = user_info.get("sub")
            email = user_info.get("email")
            name = user_info.get("name", "")
            picture = user_info.get("picture", "")
            email_verified = user_info.get("email_verified", False)
            
            # Validate email
            if not email or not validate_email(email):
                return None, error_response(
                    message="Invalid email address received from Google",
                    error_code=ErrorCode.VALIDATION_INVALID_FORMAT,
                    status_code=HttpStatus.BAD_REQUEST,
                )
            
            # Step 3: Find existing user or create new one
            user = self.user_store.get_user_by_google_id(google_id)
            
            if not user:
                # Try to find by email (account linking)
                user = self.user_store.get_user_by_email(email)
                
                if user:
                    # Link Google ID to existing account
                    logger.info(f"Linking Google account to existing user: {mask_email(email)}")
                    self.user_store.update_user(
                        user["user_id"],
                        {
                            "google_id": google_id,
                            "picture": picture or user.get("picture", ""),
                            "is_verified": email_verified,
                        }
                    )
                    # Refresh user data after update
                    user = self.user_store.get_user_by_id(user["user_id"])
                else:
                    # Create new user
                    logger.info(f"Creating new user from Google auth: {mask_email(email)}")
                    user = self.user_store.create_user({
                        "email": email,
                        "name": name,
                        "picture": picture,
                        "google_id": google_id,
                        "provider": "google",
                        "role": UserRole.USER.value,
                        "is_verified": email_verified,
                    })
                    
                    if not user:
                        return None, error_response(
                            message="Failed to create user account",
                            error_code=ErrorCode.SERVER_INTERNAL,
                            status_code=HttpStatus.INTERNAL_SERVER_ERROR,
                        )
            
            # Step 4: Check if user account is active
            if not user.get("is_active", False):
                logger.warning(f"Login attempt on deactivated account: {mask_email(email)}")
                return None, error_response(
                    message="Account has been deactivated. Please contact support.",
                    error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                    status_code=HttpStatus.FORBIDDEN,
                )
            
            # Step 5: Update last login
            self.user_store.update_last_login(user["user_id"])
            
            # Step 6: Create session
            session_token = self.session_mgr.create_session({
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user["name"],
                "picture": user.get("picture", ""),
                "role": user.get("role", UserRole.USER.value),
                "provider": "google",
                "ip_address": ip_address,
                "user_agent": user_agent,
            })
            
            if not session_token:
                return None, error_response(
                    message="Failed to create user session",
                    error_code=ErrorCode.SERVER_INTERNAL,
                    status_code=HttpStatus.INTERNAL_SERVER_ERROR,
                )
            
            # Step 7: Prepare response
            user_data = {
                "user": sanitize_session_for_client(user),
                "session_token": session_token,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
            }
            
            logger.info(f"User authenticated successfully: {mask_email(email)}")
            return user_data, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return None, error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
                error="An unexpected error occurred during authentication",
            )
    
    def authenticate_with_token(
        self,
        id_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple]]:
        """
        Authenticate user with Google ID token (client-side flow).
        
        Args:
            id_token: Google ID token from client-side authentication
            ip_address: Client IP address for session
            user_agent: Client user agent for session
        
        Returns:
            Tuple of (user_data_dict, error_response_tuple)
        """
        try:
            # Step 1: Verify ID token
            token_info = self.google_oauth.verify_id_token(id_token)
            
            if not token_info:
                return None, error_response(
                    message=ApiMessage.INVALID_TOKEN,
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    status_code=HttpStatus.UNAUTHORIZED,
                    error="Failed to verify Google ID token",
                )
            
            # Extract user details
            google_id = token_info.get("sub")
            email = token_info.get("email")
            name = token_info.get("name", "")
            picture = token_info.get("picture", "")
            email_verified = token_info.get("email_verified", False)
            
            if not email:
                return None, error_response(
                    message="Email not found in ID token",
                    error_code=ErrorCode.VALIDATION_MISSING_FIELD,
                    status_code=HttpStatus.BAD_REQUEST,
                )
            
            # Step 2: Find or create user
            user = self.user_store.get_user_by_google_id(google_id)
            
            if not user:
                user = self.user_store.get_user_by_email(email)
                
                if user:
                    # Link accounts
                    self.user_store.update_user(
                        user["user_id"],
                        {
                            "google_id": google_id,
                            "picture": picture or user.get("picture", ""),
                            "is_verified": email_verified,
                        }
                    )
                    user = self.user_store.get_user_by_id(user["user_id"])
                else:
                    # Create new user
                    user = self.user_store.create_user({
                        "email": email,
                        "name": name,
                        "picture": picture,
                        "google_id": google_id,
                        "provider": "google",
                        "role": UserRole.USER.value,
                        "is_verified": email_verified,
                    })
            
            if not user or not user.get("is_active", False):
                return None, error_response(
                    message="Account not found or has been deactivated",
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    status_code=HttpStatus.UNAUTHORIZED,
                )
            
            # Step 3: Update login and create session
            self.user_store.update_last_login(user["user_id"])
            
            session_token = self.session_mgr.create_session({
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user["name"],
                "picture": user.get("picture", ""),
                "role": user.get("role", UserRole.USER.value),
                "provider": "google",
                "ip_address": ip_address,
                "user_agent": user_agent,
            })
            
            if not session_token:
                return None, error_response(
                    message="Failed to create session",
                    error_code=ErrorCode.SERVER_INTERNAL,
                    status_code=HttpStatus.INTERNAL_SERVER_ERROR,
                )
            
            user_data = {
                "user": sanitize_session_for_client(user),
                "session_token": session_token,
            }
            
            logger.info(f"User authenticated via token: {mask_email(email)}")
            return user_data, None
            
        except Exception as e:
            logger.error(f"Token authentication error: {e}", exc_info=True)
            return None, error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
    
    def logout(self, session_token: str) -> Tuple[bool, Optional[Tuple]]:
        """
        Logout user by invalidating their session.
        
        Args:
            session_token: Session token to invalidate
        
        Returns:
            Tuple of (success, error_response_tuple)
        """
        try:
            success = self.session_mgr.delete_session(session_token)
            
            if success:
                logger.info("User logged out successfully")
                return True, None
            else:
                return False, error_response(
                    message="Session not found or already expired",
                    error_code=ErrorCode.AUTH_INVALID_TOKEN,
                    status_code=HttpStatus.NOT_FOUND,
                )
                
        except Exception as e:
            logger.error(f"Logout error: {e}", exc_info=True)
            return False, error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
    
    def logout_all_sessions(self, user_id: str) -> Tuple[int, Optional[Tuple]]:
        """
        Logout user from all devices.
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (sessions_deleted_count, error_response_tuple)
        """
        try:
            count = self.session_mgr.store.delete_all_user_sessions(user_id)
            logger.info(f"Logged out user {user_id} from all devices ({count} sessions)")
            return count, None
        except Exception as e:
            logger.error(f"Logout all sessions error: {e}", exc_info=True)
            return 0, error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
    
    def get_current_user(self, session_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple]]:
        """
        Get current authenticated user from session token.
        
        Args:
            session_token: Valid session token
        
        Returns:
            Tuple of (sanitized_user_data, error_response_tuple)
        """
        try:
            session_data = self.session_mgr.get_session(session_token)
            
            if not session_data:
                return None, error_response(
                    message=ApiMessage.SESSION_EXPIRED,
                    error_code=ErrorCode.AUTH_EXPIRED_TOKEN,
                    status_code=HttpStatus.UNAUTHORIZED,
                )
            
            user_id = session_data.get("user_id")
            user = self.user_store.get_user_by_id(user_id)
            
            if not user:
                return None, error_response(
                    message="User account not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    status_code=HttpStatus.NOT_FOUND,
                )
            
            return sanitize_session_for_client(user), None
            
        except Exception as e:
            logger.error(f"Get current user error: {e}", exc_info=True)
            return None, error_response(
                message=ApiMessage.INTERNAL_ERROR,
                error_code=ErrorCode.SERVER_INTERNAL,
                status_code=HttpStatus.INTERNAL_SERVER_ERROR,
            )
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User data if found, None otherwise
        """
        return self.user_store.get_user_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: User email address
        
        Returns:
            User data if found, None otherwise
        """
        return self.user_store.get_user_by_email(email)
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            updates: Fields to update
        
        Returns:
            Updated user data if successful
        """
        return self.user_store.update_user(user_id, updates)


# ============================================================================
# GLOBAL AUTH SERVICE INSTANCE
# ============================================================================

# Lazy-loaded global auth service instance
_auth_service_instance = None


def get_auth_service() -> AuthService:
    """
    Get or create the global AuthService instance.
    Uses lazy initialization to avoid circular imports.
    
    Returns:
        AuthService instance
    """
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance


# Pre-initialize for backward compatibility
auth_service = get_auth_service()