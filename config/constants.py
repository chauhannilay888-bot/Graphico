"""
Graphico Pro - Application Constants
Immutable constants, enums, and mappings used across the entire backend application.

All values defined here are considered stable and should not change at runtime.
For configurable values, see config/settings.py.
"""

from enum import Enum
from typing import Final

# ============================================================================
# API VERSIONING
# ============================================================================

API_VERSION: Final[str] = "v1"
API_PREFIX: Final[str] = f"/api/{API_VERSION}"

# ============================================================================
# HTTP STATUS CODES
# ============================================================================

class HttpStatus:
    """
    HTTP Status Codes for consistent API responses.
    Using named constants instead of magic numbers.
    """
    
    # 2xx Success
    OK: Final[int] = 200
    CREATED: Final[int] = 201
    ACCEPTED: Final[int] = 202
    NO_CONTENT: Final[int] = 204
    
    # 3xx Redirection
    MOVED_PERMANENTLY: Final[int] = 301
    FOUND: Final[int] = 302
    NOT_MODIFIED: Final[int] = 304
    
    # 4xx Client Errors
    BAD_REQUEST: Final[int] = 400
    UNAUTHORIZED: Final[int] = 401
    FORBIDDEN: Final[int] = 403
    NOT_FOUND: Final[int] = 404
    METHOD_NOT_ALLOWED: Final[int] = 405
    CONFLICT: Final[int] = 409
    UNPROCESSABLE_ENTITY: Final[int] = 422
    TOO_MANY_REQUESTS: Final[int] = 429
    
    # 5xx Server Errors
    INTERNAL_SERVER_ERROR: Final[int] = 500
    NOT_IMPLEMENTED: Final[int] = 501
    BAD_GATEWAY: Final[int] = 502
    SERVICE_UNAVAILABLE: Final[int] = 503
    GATEWAY_TIMEOUT: Final[int] = 504

# ============================================================================
# API RESPONSE MESSAGES
# ============================================================================

class ApiMessage:
    """
    Standardized API response messages.
    Ensures consistent user-facing messages across all endpoints.
    """
    
    # Generic Success Messages
    SUCCESS: Final[str] = "Operation completed successfully"
    CREATED: Final[str] = "Resource created successfully"
    UPDATED: Final[str] = "Resource updated successfully"
    DELETED: Final[str] = "Resource deleted successfully"
    
    # Authentication Messages
    LOGIN_SUCCESS: Final[str] = "Login successful"
    LOGOUT_SUCCESS: Final[str] = "Logout successful"
    SESSION_REFRESHED: Final[str] = "Session refreshed successfully"
    
    # File Messages
    UPLOAD_SUCCESS: Final[str] = "File uploaded successfully"
    EXPORT_SUCCESS: Final[str] = "Export completed successfully"
    
    # AI Messages
    CHAT_GENERATED: Final[str] = "Chat completion generated"
    IMAGE_GENERATED: Final[str] = "Image generated successfully"
    DOCUMENT_GENERATED: Final[str] = "Document generated successfully"
    PRESENTATION_CREATED: Final[str] = "Presentation content generated"
    PDF_ANALYZED: Final[str] = "PDF analysis completed"
    PDF_TEXT_EXTRACTED: Final[str] = "PDF text extracted successfully"
    
    # Generic Error Messages
    BAD_REQUEST: Final[str] = "Bad request"
    UNAUTHORIZED: Final[str] = "Authentication required"
    FORBIDDEN: Final[str] = "Access denied"
    NOT_FOUND: Final[str] = "Resource not found"
    METHOD_NOT_ALLOWED: Final[str] = "HTTP method not allowed"
    CONFLICT: Final[str] = "Resource already exists"
    VALIDATION_ERROR: Final[str] = "Validation error"
    INTERNAL_ERROR: Final[str] = "Internal server error"
    SERVICE_UNAVAILABLE: Final[str] = "Service temporarily unavailable"
    RATE_LIMITED: Final[str] = "Too many requests. Please try again later"
    
    # Auth Error Messages
    INVALID_TOKEN: Final[str] = "Invalid or expired token"
    INVALID_CREDENTIALS: Final[str] = "Invalid credentials"
    GOOGLE_AUTH_FAILED: Final[str] = "Google authentication failed"
    SESSION_EXPIRED: Final[str] = "Session expired. Please login again"
    ACCOUNT_DEACTIVATED: Final[str] = "Account has been deactivated. Please contact support"
    CSRF_VALIDATION_FAILED: Final[str] = "Invalid or expired state token. Possible CSRF attack"
    
    # File Error Messages
    FILE_TOO_LARGE: Final[str] = "File size exceeds maximum allowed size"
    INVALID_FILE_TYPE: Final[str] = "File type not supported"
    FILE_NOT_FOUND: Final[str] = "File not found"
    FILE_UPLOAD_FAILED: Final[str] = "File upload failed"
    FILE_CORRUPTED: Final[str] = "File is corrupted or cannot be read"
    
    # AI Error Messages
    AI_GENERATION_FAILED: Final[str] = "AI generation failed"
    AI_MODEL_UNAVAILABLE: Final[str] = "Requested AI model is not available"
    AI_QUOTA_EXCEEDED: Final[str] = "AI quota exceeded"
    AI_CONTENT_FILTERED: Final[str] = "Content was filtered by AI safety systems"
    
    # Project Error Messages
    PROJECT_LIMIT_REACHED: Final[str] = "Maximum number of projects reached"
    PROJECT_NOT_FOUND: Final[str] = "Project not found"
    FILE_LIMIT_REACHED: Final[str] = "Maximum number of files per project reached"
    
    # Export Error Messages
    EXPORT_FAILED: Final[str] = "Export failed"
    UNSUPPORTED_EXPORT_FORMAT: Final[str] = "Unsupported export format"

# ============================================================================
# USER ROLES
# ============================================================================

class UserRole(str, Enum):
    """User role definitions for access control."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    GUEST = "guest"

# ============================================================================
# PROJECT STATUS
# ============================================================================

class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    DRAFT = "draft"

# ============================================================================
# AI PROVIDERS
# ============================================================================

class AIProvider(str, Enum):
    """Supported AI service providers."""
    GITHUB_MODELS = "github_models"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE_AI = "google_ai"
    STABILITY = "stability"
    REPLICATE = "replicate"

# ============================================================================
# AI MODELS
# ============================================================================

class AIModel(str, Enum):
    """
    Available AI models organized by provider.
    Model IDs match the API identifiers exactly.
    """
    # GitHub Models (free via Azure)
    GITHUB_GPT4O = "gpt-4o"

    # DeepSeek Models
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_REASONER = "deepseek-reasoner"

    # OpenAI Models
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"
    DALL_E_3 = "dall-e-3"
    DALL_E_2 = "dall-e-2"

    # Anthropic (Claude) Models
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    # Google AI (Gemini) Models
    GEMINI_20_FLASH = "gemini-2.0-flash"
    GEMINI_25_PRO = "gemini-2.5-pro"
    GEMINI_25_FLASH = "gemini-2.5-flash"
    GEMINI_FLASH_LATEST = "gemini-flash-latest"
    GEMINI_PRO_LATEST = "gemini-pro-latest"

    # Stability AI Models
    STABLE_DIFFUSION_XL = "stable-diffusion-xl"
    STABLE_DIFFUSION_3 = "stable-diffusion-3"

    # Replicate Models
    SDXL_LIGHTNING = "sdxl-lightning"

class AITaskType(str, Enum):
    """Types of AI operations supported by the platform."""
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_GENERATION = "document_generation"
    PDF_ANALYSIS = "pdf_analysis"
    PRESENTATION_CREATION = "presentation_creation"
    CODE_GENERATION = "code_generation"
    TEXT_SUMMARIZATION = "text_summarization"
    TRANSLATION = "translation"
    KEYWORD_EXTRACTION = "keyword_extraction"

# ============================================================================
# FILE CATEGORIES
# ============================================================================

class FileCategory(str, Enum):
    """Supported file categories for uploads and exports."""
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    CODE = "code"
    DATA = "data"
    ARCHIVE = "archive"

# ============================================================================
# MIME TYPES MAPPING
# ============================================================================

MIME_TYPES: Final[dict] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".ts": "text/typescript",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".md": "text/markdown",
    ".sql": "text/x-sql",
    ".sh": "text/x-shellscript",
    ".bash": "text/x-shellscript",
    ".zip": "application/zip",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".tgz": "application/gzip",
    ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".bin": "application/octet-stream",
}

# ============================================================================
# EXPORT FORMAT MIME TYPES
# ============================================================================

EXPORT_MIME_TYPES: Final[dict] = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "json": "application/json",
    "csv": "text/csv",
    "markdown": "text/markdown",
    "html": "text/html",
}

# ============================================================================
# DEFAULT PROMPTS
# ============================================================================

class DefaultPrompts:
    """Default system prompts for different AI task types."""
    
    CHAT_ASSISTANT: Final[str] = (
        "You are Graphico Pro AI, a creative and professional AI assistant. "
        "You help users with creative tasks, document generation, presentations, "
        "image descriptions, code, and general problem-solving. "
        "Always be helpful, precise, and maintain a professional tone. "
        "Respond in the same language as the user's query. "
        "When generating code or technical content, ensure accuracy and best practices."
    )

    IMAGE_GENERATOR: Final[str] = (
        "You are an expert at crafting detailed image generation prompts. "
        "Create vivid, descriptive prompts that will produce stunning visual results. "
        "Include specific details about: style, lighting, composition, mood, "
        "color palette, perspective, and technical specifications. "
        "Be precise and evocative in your descriptions."
    )

    DOCUMENT_WRITER: Final[str] = (
        "You are a professional document writer. "
        "Create well-structured, comprehensive documents with proper formatting, "
        "clear headings, logical organization, and engaging content. "
        "Use markdown formatting for structure. "
        "Maintain a professional tone while being informative and accessible."
    )

    PRESENTATION_CREATOR: Final[str] = (
        "You are a presentation design expert. "
        "Create compelling slide-by-slide content with engaging titles, "
        "concise bullet points, and clear narrative flow. "
        "For each slide, provide: title, key points (3-5 bullets), "
        "speaker notes, and visual suggestions. "
        "Focus on visual hierarchy and information clarity. "
        "Use '--- SLIDE X ---' separators between slides."
    )

    PDF_ANALYZER: Final[str] = (
        "You are a document analysis specialist. "
        "Extract key information, summarize content, identify main themes, "
        "and provide structured insights from documents. "
        "Be thorough yet concise in your analysis. "
        "Highlight important facts, figures, dates, and conclusions. "
        "Organize information in a scannable, well-structured format."
    )

    CODE_HELPER: Final[str] = (
        "You are an expert programmer and coding assistant. "
        "Write clean, efficient, well-documented code following best practices. "
        "Explain complex concepts clearly and provide practical examples. "
        "Use appropriate error handling, type hints, and comments. "
        "Follow language-specific conventions and idioms."
    )

# ============================================================================
# VALIDATION PATTERNS
# ============================================================================

class ValidationPatterns:
    """Regex patterns for input validation."""
    
    EMAIL: Final[str] = (
        r"^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}"
        r"@[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
        r"(\.[a-zA-Z]{2,})+$"
    )
    
    USERNAME: Final[str] = r"^[a-zA-Z0-9_-]{3,50}$"
    PROJECT_NAME: Final[str] = r"^[a-zA-Z0-9\s\-_.,!?()]{1,200}$"
    FILENAME: Final[str] = r"^[a-zA-Z0-9\s\-_.,!@#$%^&()+=[\]{}']+$"
    URL: Final[str] = (
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$"
    )
    SLUG: Final[str] = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    UUID: Final[str] = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    HEX_COLOR: Final[str] = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"

# ============================================================================
# PAGINATION DEFAULTS
# ============================================================================

class Pagination:
    """Default pagination settings for list endpoints."""
    DEFAULT_PAGE: Final[int] = 1
    DEFAULT_PER_PAGE: Final[int] = 20
    MAX_PER_PAGE: Final[int] = 100
    MIN_PER_PAGE: Final[int] = 1

# ============================================================================
# EXPORT QUALITY SETTINGS
# ============================================================================

class ExportQuality:
    """Export quality presets for various formats."""
    IMAGE_DPI: Final[int] = 300
    THUMBNAIL_DPI: Final[int] = 72
    PDF_COMPRESSION: Final[str] = "medium"
    PDF_PAGE_SIZE: Final[str] = "A4"
    PRESENTATION_ASPECT_RATIO: Final[str] = "16:9"
    PRESENTATION_SLIDE_WIDTH_INCHES: Final[float] = 13.333
    PRESENTATION_SLIDE_HEIGHT_INCHES: Final[float] = 7.5
    THUMBNAIL_SIZE: Final[tuple] = (300, 300)
    PREVIEW_SIZE: Final[tuple] = (1200, 800)
    FULL_SIZE: Final[tuple] = (2048, 2048)

# ============================================================================
# ERROR CODES
# ============================================================================

class ErrorCode(str, Enum):
    """
    Application-specific error codes for debugging and client handling.
    """
    AUTH_MISSING_TOKEN = "AUTH_001"
    AUTH_INVALID_TOKEN = "AUTH_002"
    AUTH_EXPIRED_TOKEN = "AUTH_003"
    AUTH_GOOGLE_FAILED = "AUTH_004"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_005"
    AUTH_ACCOUNT_DEACTIVATED = "AUTH_006"
    AUTH_CSRF_FAILED = "AUTH_007"
    AUTH_SESSION_LIMIT = "AUTH_008"
    VALIDATION_MISSING_FIELD = "VAL_001"
    VALIDATION_INVALID_FORMAT = "VAL_002"
    VALIDATION_CONSTRAINT_VIOLATION = "VAL_003"
    VALIDATION_VALUE_OUT_OF_RANGE = "VAL_004"
    VALIDATION_DUPLICATE_ENTRY = "VAL_005"
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_LIMIT_REACHED = "RES_003"
    RESOURCE_CONFLICT = "RES_004"
    RESOURCE_DELETED = "RES_005"
    FILE_TOO_LARGE = "FILE_001"
    FILE_UNSUPPORTED_TYPE = "FILE_002"
    FILE_CORRUPTED = "FILE_003"
    FILE_UPLOAD_FAILED = "FILE_004"
    FILE_NOT_FOUND = "FILE_005"
    FILE_READ_ERROR = "FILE_006"
    FILE_WRITE_ERROR = "FILE_007"
    FILE_DELETE_ERROR = "FILE_008"
    AI_PROVIDER_ERROR = "AI_001"
    AI_MODEL_ERROR = "AI_002"
    AI_GENERATION_ERROR = "AI_003"
    AI_RATE_LIMITED = "AI_004"
    AI_CONTENT_FILTERED = "AI_005"
    AI_TIMEOUT = "AI_006"
    AI_INVALID_RESPONSE = "AI_007"
    AI_QUOTA_EXCEEDED = "AI_008"
    EXPORT_FAILED = "EXPORT_001"
    EXPORT_UNSUPPORTED_FORMAT = "EXPORT_002"
    EXPORT_FILE_TOO_LARGE = "EXPORT_003"
    SERVER_INTERNAL = "SRV_001"
    SERVER_DATABASE = "SRV_002"
    SERVER_CONFIGURATION = "SRV_003"
    SERVER_OVERLOADED = "SRV_004"
    SERVER_MAINTENANCE = "SRV_005"
    RATE_LIMIT_EXCEEDED = "RATE_001"
    RATE_QUOTA_EXCEEDED = "RATE_002"
    NOT_IMPLEMENTED = "NI_001"

# ============================================================================
# HTTP HEADER NAMES
# ============================================================================

class HeaderNames:
    """HTTP header name constants used across the application."""
    AUTHORIZATION: Final[str] = "Authorization"
    CONTENT_TYPE: Final[str] = "Content-Type"
    ACCEPT: Final[str] = "Accept"
    USER_AGENT: Final[str] = "User-Agent"
    ORIGIN: Final[str] = "Origin"
    REFERER: Final[str] = "Referer"
    X_REQUEST_ID: Final[str] = "X-Request-ID"
    X_SESSION_TOKEN: Final[str] = "X-Session-Token"
    X_RESPONSE_TIME: Final[str] = "X-Response-Time"
    X_RATE_LIMIT_REMAINING: Final[str] = "X-RateLimit-Remaining"
    X_RATE_LIMIT_RESET: Final[str] = "X-RateLimit-Reset"
    X_FORWARDED_FOR: Final[str] = "X-Forwarded-For"
    X_REAL_IP: Final[str] = "X-Real-IP"
    CONTENT_DISPOSITION: Final[str] = "Content-Disposition"
    CACHE_CONTROL: Final[str] = "Cache-Control"

# ============================================================================
# CONTENT TYPES
# ============================================================================

class ContentType:
    """Content-Type header values for HTTP requests and responses."""
    JSON: Final[str] = "application/json"
    FORM: Final[str] = "application/x-www-form-urlencoded"
    MULTIPART: Final[str] = "multipart/form-data"
    TEXT: Final[str] = "text/plain"
    HTML: Final[str] = "text/html"
    OCTET_STREAM: Final[str] = "application/octet-stream"
    FORM_DATA: Final[str] = "multipart/form-data"

# ============================================================================
# SUPPORTED LANGUAGES
# ============================================================================

SUPPORTED_LANGUAGES: Final[dict] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)", "hi": "Hindi", "ar": "Arabic",
    "tr": "Turkish", "pl": "Polish", "sv": "Swedish", "da": "Danish",
    "fi": "Finnish", "no": "Norwegian", "cs": "Czech", "ro": "Romanian",
    "th": "Thai", "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
    "uk": "Ukrainian",
}

# ============================================================================
# SYSTEM LIMITS
# ============================================================================

class SystemLimits:
    """System-wide hard limits to prevent resource abuse."""
    MAX_CHAT_MESSAGE_LENGTH: Final[int] = 4096
    MAX_SYSTEM_PROMPT_LENGTH: Final[int] = 2048
    MAX_CONTEXT_WINDOW: Final[int] = 100
    MAX_IMAGE_GENERATION_BATCH: Final[int] = 4
    MAX_PDF_PAGES: Final[int] = 500
    MAX_PRESENTATION_SLIDES: Final[int] = 100
    MAX_EXPORT_WAIT_SECONDS: Final[int] = 300
    MAX_EXPORT_FILE_SIZE_BYTES: Final[int] = 100 * 1024 * 1024
    MAX_CONCURRENT_REQUESTS: Final[int] = 10
    MAX_REQUEST_BODY_SIZE: Final[int] = 10 * 1024 * 1024
    MAX_TOTAL_STORAGE_PER_USER_BYTES: Final[int] = 500 * 1024 * 1024
    MAX_SINGLE_FILE_SIZE_BYTES: Final[int] = 50 * 1024 * 1024
    MAX_SESSIONS_PER_USER: Final[int] = 10

# ============================================================================
# TIME CONSTANTS (in seconds)
# ============================================================================

class TimeConstants:
    """Common time durations in seconds for consistency."""
    ONE_MINUTE: Final[int] = 60
    FIVE_MINUTES: Final[int] = 300
    TEN_MINUTES: Final[int] = 600
    FIFTEEN_MINUTES: Final[int] = 900
    THIRTY_MINUTES: Final[int] = 1800
    ONE_HOUR: Final[int] = 3600
    SIX_HOURS: Final[int] = 21600
    TWELVE_HOURS: Final[int] = 43200
    ONE_DAY: Final[int] = 86400
    ONE_WEEK: Final[int] = 604800
    ONE_MONTH: Final[int] = 2592000

# ============================================================================
# AI MODEL CAPABILITIES
# ============================================================================

class ModelCapability(str, Enum):
    """Capabilities that AI models can support."""
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_UNDERSTANDING = "image_understanding"
    CODE_GENERATION = "code_generation"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    LONG_CONTEXT = "long_context"

# ============================================================================
# AI MODEL DEFAULT PARAMETERS
# ============================================================================

class ModelDefaults:
    """Default parameters for AI model requests."""
    DEFAULT_MAX_TOKENS: Final[int] = 2000
    DEFAULT_TEMPERATURE: Final[float] = 0.7
    DEFAULT_TOP_P: Final[float] = 1.0
    DEFAULT_IMAGE_SIZE: Final[str] = "1024x1024"
    DEFAULT_IMAGE_QUALITY: Final[str] = "standard"
    DEFAULT_IMAGE_COUNT: Final[int] = 1
    DEFAULT_ANALYSIS_TYPE: Final[str] = "summarize"
    MAX_PDF_TEXT_LENGTH: Final[int] = 30000

# ============================================================================
# ANALYSIS TYPES
# ============================================================================

class AnalysisType(str, Enum):
    """Types of document analysis available."""
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    KEYWORDS = "keywords"
    QUESTIONS = "questions"
    SENTIMENT = "sentiment"
    ENTITIES = "entities"

# ============================================================================
# DOCUMENT TYPES
# ============================================================================

class DocumentType(str, Enum):
    """Types of documents that can be generated."""
    REPORT = "report"
    ARTICLE = "article"
    LETTER = "letter"
    PROPOSAL = "proposal"
    MEMO = "memo"
    EMAIL = "email"
    BLOG_POST = "blog_post"
    WHITEPAPER = "whitepaper"
    MANUAL = "manual"
    GUIDE = "guide"

# ============================================================================
# WRITING TONES
# ============================================================================

class WritingTone(str, Enum):
    """Writing tone options for AI content generation."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ACADEMIC = "academic"
    PERSUASIVE = "persuasive"
    INFORMATIVE = "informative"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"

# ============================================================================
# PRESENTATION STYLES
# ============================================================================

class PresentationStyle(str, Enum):
    """Presentation style options for AI generation."""
    BUSINESS = "business"
    CREATIVE = "creative"
    ACADEMIC = "academic"
    MINIMAL = "minimal"
    PITCH_DECK = "pitch_deck"
    TRAINING = "training"
    CONFERENCE = "conference"

# ============================================================================
# CONTENT LENGTHS
# ============================================================================

class ContentLength(str, Enum):
    """Content length options for AI generation."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    EXTENDED = "extended"