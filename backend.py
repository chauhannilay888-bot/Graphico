"""
Graphico Pro - Main Backend Server
Production-grade Flask application with comprehensive API, authentication,
session management, CORS, and error handling.
Runs on both Flask (python backend/backend.py) and Streamlit (streamlit run backend/backend.py).

Startup Order:
1. Configuration validation
2. Directory structure creation
3. Service initialization (auth, session, AI, projects, files, export, PDF, data)
4. Flask app creation with middleware
5. Route registration
6. Server startup
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, request, jsonify, g
from flask_cors import CORS

from config.settings import (
    SERVER_HOST,
    SERVER_PORT,
    SERVER_DEBUG,
    ALLOWED_ORIGINS,
    ALLOWED_METHODS,
    ALLOWED_HEADERS,
    ALLOWED_CREDENTIALS,
    MAX_REQUEST_SIZE_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    ensure_directories_exist,
    validate_configuration,
    is_production,
    get_database_config,
    get_ai_providers,
)
from config.constants import (
    HttpStatus,
    ApiMessage,
    ErrorCode,
    ContentType,
    API_PREFIX,
)
from backend.utils import (
    setup_logger,
    get_timestamp,
    get_utc_now,
    create_response,
    success_response,
    error_response,
    get_client_ip,
    ensure_directory,
)

# ============================================================================
# EARLY LOGGING SETUP
# ============================================================================

logger = setup_logger("graphico")

# ============================================================================
# SERVICE INITIALIZATION (MUST HAPPEN BEFORE ROUTE REGISTRATION)
# ============================================================================

def initialize_all_services() -> dict:
    """
    Initialize all backend services in the correct dependency order.
    
    Services must be initialized before routes are registered because:
    - Routes import and use service instances
    - Services need their storage files and directories ready
    - AI providers need to be validated
    
    Returns:
        Dictionary with initialization status for each service
    """
    status = {
        "started_at": get_timestamp(),
        "services": {},
        "warnings": [],
        "errors": [],
    }
    
    logger.info("=" * 60)
    logger.info("Graphico Pro - Service Initialization")
    logger.info("=" * 60)
    
    # Step 0: Ensure directories exist
    logger.info("Creating required directories...")
    try:
        ensure_directories_exist()
        logger.info("✓ Directory structure created")
    except Exception as e:
        error_msg = f"Failed to create directories: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        return status
    
    # Step 1: Validate configuration
    logger.info("Validating configuration...")
    config_issues = validate_configuration()
    
    for issue in config_issues:
        if issue.startswith("ERROR"):
            logger.error(f"✗ {issue}")
            status["errors"].append(issue)
        else:
            logger.warning(f"⚠ {issue}")
            status["warnings"].append(issue)
    
    if not config_issues:
        logger.info("✓ Configuration validated successfully")
    
    # Step 2: Log available configuration
    db_config = get_database_config()
    ai_providers = get_ai_providers()
    
    logger.info(f"Database type: {db_config['type']}")
    logger.info(f"AI Providers configured: {sum(1 for v in ai_providers.values() if v)}/{len(ai_providers)}")
    
    for provider, configured in ai_providers.items():
        status_icon = "✓" if configured else "✗"
        logger.info(f"  {status_icon} {provider}: {'configured' if configured else 'not configured'}")
    
    # Step 3: Initialize Session Manager
    logger.info("Initializing session manager...")
    try:
        from backend.session import get_session_manager
        session_mgr = get_session_manager()
        active_sessions = session_mgr.store.get_active_sessions_count()
        logger.info(f"✓ Session manager initialized ({active_sessions} active sessions)")
        status["services"]["session_manager"] = {
            "status": "ok",
            "active_sessions": active_sessions,
        }
    except Exception as e:
        error_msg = f"Failed to initialize session manager: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["session_manager"] = {"status": "error", "error": str(e)}
    
    # Step 4: Initialize Auth Service
    logger.info("Initializing authentication service...")
    try:
        from backend.auth import get_auth_service
        auth_svc = get_auth_service()
        active_users = auth_svc.user_store.get_active_users_count()
        total_users = auth_svc.user_store.get_total_users_count()
        csrf_active = auth_svc.google_oauth.csrf_store.get_active_state_count()
        logger.info(f"✓ Auth service initialized ({active_users} active users, {total_users} total)")
        logger.info(f"  CSRF state store: {csrf_active} active state tokens")
        status["services"]["auth_service"] = {
            "status": "ok",
            "active_users": active_users,
            "total_users": total_users,
        }
    except Exception as e:
        error_msg = f"Failed to initialize auth service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["auth_service"] = {"status": "error", "error": str(e)}
    
    # Step 5: Initialize AI Service
    logger.info("Initializing AI service...")
    try:
        from backend.services import get_ai_service
        ai_svc = get_ai_service()
        available_models = ai_svc.get_available_models()
        chat_models = sum(1 for m in available_models if m.get("type") == "chat")
        image_models = sum(1 for m in available_models if m.get("type") == "image")
        logger.info(f"✓ AI service initialized ({len(available_models)} models: {chat_models} chat, {image_models} image)")
        for model in available_models:
            logger.info(f"  • {model['display_name']} ({model['provider']})")
        status["services"]["ai_service"] = {
            "status": "ok",
            "total_models": len(available_models),
            "chat_models": chat_models,
            "image_models": image_models,
        }
    except Exception as e:
        error_msg = f"Failed to initialize AI service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["ai_service"] = {"status": "error", "error": str(e)}
    
    # Step 6: Initialize Project Service
    logger.info("Initializing project service...")
    try:
        from backend.services import get_project_service
        project_svc = get_project_service()
        total_projects = len(project_svc._projects) if hasattr(project_svc, '_projects') else 0
        logger.info(f"✓ Project service initialized ({total_projects} projects loaded)")
        status["services"]["project_service"] = {
            "status": "ok",
            "total_projects": total_projects,
        }
    except Exception as e:
        error_msg = f"Failed to initialize project service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["project_service"] = {"status": "error", "error": str(e)}
    
    # Step 7: Initialize File Service
    logger.info("Initializing file service...")
    try:
        from backend.services import get_file_service
        file_svc = get_file_service()
        logger.info(f"✓ File service initialized (upload dir: {file_svc.upload_dir})")
        status["services"]["file_service"] = {
            "status": "ok",
            "upload_dir": str(file_svc.upload_dir),
        }
    except Exception as e:
        error_msg = f"Failed to initialize file service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["file_service"] = {"status": "error", "error": str(e)}
    
    # Step 8: Initialize Export Service
    logger.info("Initializing export service...")
    try:
        from backend.services import get_export_service
        export_svc = get_export_service()
        logger.info(f"✓ Export service initialized (export dir: {export_svc.export_dir})")
        status["services"]["export_service"] = {
            "status": "ok",
            "export_dir": str(export_svc.export_dir),
        }
    except Exception as e:
        error_msg = f"Failed to initialize export service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["export_service"] = {"status": "error", "error": str(e)}
    
    # Step 9: Initialize PDF Service
    logger.info("Initializing PDF analysis service...")
    try:
        from backend.services import get_pdf_service
        pdf_svc = get_pdf_service()
        extraction_methods = []
        if hasattr(pdf_svc, '_pdfplumber') and pdf_svc._pdfplumber:
            extraction_methods.append("pdfplumber")
        if hasattr(pdf_svc, '_pypdf') and pdf_svc._pypdf:
            extraction_methods.append("PyPDF2")
        logger.info(f"✓ PDF service initialized (extraction: {', '.join(extraction_methods) if extraction_methods else 'none'})")
        status["services"]["pdf_service"] = {
            "status": "ok",
            "extraction_methods": extraction_methods,
        }
    except Exception as e:
        error_msg = f"Failed to initialize PDF service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["pdf_service"] = {"status": "error", "error": str(e)}
    
    # Step 10: Initialize Data Service
    logger.info("Initializing data service...")
    try:
        from backend.data_service import get_data_service
        data_svc = get_data_service()
        logger.info("✓ Data service initialized")
        status["services"]["data_service"] = {"status": "ok"}
    except Exception as e:
        error_msg = f"Failed to initialize data service: {e}"
        logger.error(f"✗ {error_msg}")
        status["errors"].append(error_msg)
        status["services"]["data_service"] = {"status": "error", "error": str(e)}
    
    # Summary
    services_ok = sum(1 for s in status["services"].values() if s.get("status") == "ok")
    services_total = len(status["services"])
    
    logger.info("=" * 60)
    
    if status["errors"]:
        logger.error(f"Service initialization complete with {len(status['errors'])} error(s)")
        logger.error(f"Services OK: {services_ok}/{services_total}")
        for err in status["errors"]:
            logger.error(f"  • {err}")
    else:
        logger.info(f"✓ All {services_total} services initialized successfully")
    
    logger.info("=" * 60)
    
    status["completed_at"] = get_timestamp()
    status["services_ok"] = services_ok
    status["services_total"] = services_total
    status["success"] = len(status["errors"]) == 0
    
    return status


# ============================================================================
# FLASK APPLICATION FACTORY
# ============================================================================

def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    IMPORTANT: All services must be initialized BEFORE calling this function.
    Routes are registered during app creation and depend on service instances.
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "graphico-pro-flask-secret-change-in-production")
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_SIZE_BYTES
    app.config["DEBUG"] = SERVER_DEBUG
    app.config["TESTING"] = False
    app.config["JSON_SORT_KEYS"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = SERVER_DEBUG
    app.config["SESSION_COOKIE_SECURE"] = is_production()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    CORS(
        app,
        origins=ALLOWED_ORIGINS,
        methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        supports_credentials=ALLOWED_CREDENTIALS,
        max_age=86400,
        expose_headers=["Content-Disposition", "X-Response-Time", "X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )
    
    logger.info("CORS configured for origins: %s", ALLOWED_ORIGINS)
    
    @app.before_request
    def before_request():
        g.start_time = get_utc_now()
        g.request_id = request.headers.get("X-Request-ID", "")
        if request.method == "OPTIONS": return None
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "Unknown")
        logger.info(f"→ {request.method} {request.path} from {client_ip} [{user_agent[:80]}]")
        content_length = request.content_length or 0
        if content_length > MAX_REQUEST_SIZE_BYTES:
            logger.warning(f"Request too large: {content_length} bytes from {client_ip}")
            return error_response(message=ApiMessage.FILE_TOO_LARGE, error_code=ErrorCode.FILE_TOO_LARGE, status_code=HttpStatus.BAD_REQUEST)
    
    @app.after_request
    def after_request(response):
        if hasattr(g, "start_time"):
            duration = (get_utc_now() - g.start_time).total_seconds()
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
        if hasattr(g, "request_id") and g.request_id:
            response.headers["X-Request-ID"] = g.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=()"
        if is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        if request.path.startswith(API_PREFIX):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        if request.method != "OPTIONS":
            status_emoji = "✓" if response.status_code < 400 else "✗"
            logger.info(f"← {status_emoji} {response.status_code} {request.method} {request.path}")
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            logger.error(f"Request teardown with exception: {exception}", exc_info=True)
    
    # Error handlers
    @app.errorhandler(400)
    def handle_bad_request(error):
        logger.warning(f"400 Bad Request: {error}")
        return _make_error_response(message=str(error) or ApiMessage.BAD_REQUEST, error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.BAD_REQUEST)
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        logger.warning(f"401 Unauthorized: {request.path}")
        return _make_error_response(message=ApiMessage.UNAUTHORIZED, error_code=ErrorCode.AUTH_MISSING_TOKEN, status_code=HttpStatus.UNAUTHORIZED)
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        logger.warning(f"403 Forbidden: {request.path}")
        return _make_error_response(message=ApiMessage.FORBIDDEN, error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS, status_code=HttpStatus.FORBIDDEN)
    
    @app.errorhandler(404)
    def handle_not_found(error):
        logger.warning(f"404 Not Found: {request.method} {request.path}")
        return _make_error_response(message=ApiMessage.NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
        return _make_error_response(message=ApiMessage.METHOD_NOT_ALLOWED, error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.METHOD_NOT_ALLOWED)
    
    @app.errorhandler(413)
    def handle_request_too_large(error):
        logger.warning("413 Request Entity Too Large")
        return _make_error_response(message=ApiMessage.FILE_TOO_LARGE, error_code=ErrorCode.FILE_TOO_LARGE, status_code=HttpStatus.BAD_REQUEST)
    
    @app.errorhandler(429)
    def handle_too_many_requests(error):
        logger.warning(f"429 Too Many Requests from {get_client_ip(request)}")
        return _make_error_response(message=ApiMessage.RATE_LIMITED, error_code=ErrorCode.AI_RATE_LIMITED, status_code=HttpStatus.TOO_MANY_REQUESTS)
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return _make_error_response(message=ApiMessage.INTERNAL_ERROR, error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.INTERNAL_SERVER_ERROR)
    
    @app.errorhandler(502)
    def handle_bad_gateway(error):
        logger.error(f"502 Bad Gateway: {error}")
        return _make_error_response(message="Upstream service unavailable", error_code=ErrorCode.AI_PROVIDER_ERROR, status_code=HttpStatus.BAD_GATEWAY)
    
    @app.errorhandler(503)
    def handle_service_unavailable(error):
        logger.error(f"503 Service Unavailable: {error}")
        return _make_error_response(message=ApiMessage.SERVICE_UNAVAILABLE, error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.SERVICE_UNAVAILABLE)
    
    def _make_error_response(message, error_code, status_code):
        response_data, _ = error_response(message=message, error_code=error_code, status_code=status_code)
        response = jsonify(response_data)
        response.status_code = status_code
        return response
    
    # Register routes
    logger.info("Registering API routes...")
    from backend.routes import register_routes, register_error_handlers, register_middleware
    register_middleware(app)
    register_routes(app)
    register_error_handlers(app)
    logger.info("✓ Routes registered successfully")
    
    return app


# ============================================================================
# STARTUP BANNER
# ============================================================================

def print_startup_banner(init_status: dict):
    banner = r"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗██╗ ██████╗ ██████╗      ║
║  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║██║██╔════╝██╔═══██╗     ║
║  ██║  ███╗██████╔╝███████║██████╔╝███████║██║██║     ██║   ██║     ║
║  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║██║██║     ██║   ██║     ║
║  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║██║╚██████╗╚██████╔╝     ║
║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═════╝      ║
║                                                                      ║
║          The AI Operating System for Creativity                      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    logger.info(banner)
    logger.info("─" * 60)
    logger.info("SERVER INFORMATION")
    logger.info("─" * 60)
    logger.info(f"  Environment:    {'PRODUCTION' if is_production() else 'DEVELOPMENT'}")
    logger.info(f"  Debug Mode:     {SERVER_DEBUG}")
    logger.info(f"  Server URL:     http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"  API Base URL:   http://{SERVER_HOST}:{SERVER_PORT}{API_PREFIX}")
    logger.info(f"  Health Check:   http://{SERVER_HOST}:{SERVER_PORT}/api/health")
    logger.info(f"  Allowed Origins: {', '.join(ALLOWED_ORIGINS)}")
    logger.info("─" * 60)
    logger.info("SERVICE STATUS")
    logger.info("─" * 60)
    services = init_status.get("services", {})
    for service_name, service_info in services.items():
        status_icon = "✓" if service_info.get("status") == "ok" else "✗"
        display_name = service_name.replace("_", " ").title()
        logger.info(f"  {status_icon} {display_name}")
    warnings = init_status.get("warnings", [])
    if warnings:
        logger.info("─" * 60)
        logger.info("WARNINGS")
        logger.info("─" * 60)
        for warning in warnings: logger.warning(f"  ⚠ {warning}")
    errors = init_status.get("errors", [])
    if errors:
        logger.info("─" * 60)
        logger.info("ERRORS")
        logger.info("─" * 60)
        for error in errors: logger.error(f"  ✗ {error}")
    logger.info("─" * 60)
    if init_status.get("success", False):
        logger.info("✓ All services initialized successfully")
        logger.info("  Ready to accept connections")
    else:
        logger.warning("⚠ Server starting with initialization errors")
        logger.warning("  Some features may not work correctly")
    logger.info("─" * 60)
    logger.info("")


# ============================================================================
# ENTRY POINTS
# ============================================================================

# Initialize services
_init_status = initialize_all_services()

# Create Flask app
app = create_app()


def main():
    """Run as Flask development server."""
    print_startup_banner(_init_status)
    try:
        logger.info(f"Starting Flask server on {SERVER_HOST}:{SERVER_PORT}...")
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=SERVER_DEBUG, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C)")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {SERVER_PORT} is already in use.")
        else:
            logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Server failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Graphico Pro backend server stopped")


# Streamlit entry point
def run_streamlit():
    """Run the Flask app via Streamlit using streamlit-lambdas."""
    try:
        import streamlit as st
        from streamlit_lambdas import streamlit_lambdas
        
        st.set_page_config(page_title="Graphico Pro", page_icon="📊", layout="wide")
        st.title("Graphico Pro — Backend Server")
        st.caption(f"API running at http://{SERVER_HOST}:{SERVER_PORT}{API_PREFIX}")
        st.success("✓ All services initialized — ready to accept API requests")
        
        st.markdown("---")
        st.subheader("Service Status")
        for name, info in _init_status.get("services", {}).items():
            icon = "✅" if info.get("status") == "ok" else "❌"
            st.write(f"{icon} **{name.replace('_', ' ').title()}**")
        
        st.markdown("---")
        st.subheader("API Endpoints")
        st.code(f"Health: GET /api/v1/health\nStatus: GET /api/v1/status\nAuth: POST /api/v1/auth/google/callback\nChat: POST /api/v1/ai/chat\nData: GET /api/v1/data/preview\nReport: POST /api/v1/data/report", language="text")
        
        # Wrap Flask as Streamlit handler
        streamlit_lambdas(app, port=SERVER_PORT)
        
    except ImportError:
        logger.error("streamlit-lambdas not installed. Run: pip install streamlit-lambdas")
        print("To run on Streamlit, install: pip install streamlit streamlit-lambdas")
        print("Then run: streamlit run backend/backend.py")


# Auto-detect if running via Streamlit
if __name__ == "__main__":
    # Check if Streamlit is the runner
    if "STREAMLIT" in os.environ or "streamlit" in sys.argv[0].lower():
        run_streamlit()
    else:
        main()