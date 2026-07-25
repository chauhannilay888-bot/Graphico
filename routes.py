"""
Graphico Pro - API Routes
Defines all API endpoints and route handlers for the backend server.
"""

import json
import logging
import io
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from flask import request, send_file, jsonify, make_response

from config.settings import (
    ALLOWED_ORIGINS,
    ALLOWED_METHODS,
    ALLOWED_HEADERS,
    ALLOWED_CREDENTIALS,
    MAX_UPLOAD_SIZE_MB,
    SERVER_DEBUG,
)
from config.constants import (
    API_PREFIX,
    HttpStatus,
    ApiMessage,
    ErrorCode,
    ContentType,
    HeaderNames,
    Pagination,
    MIME_TYPES,
    SystemLimits,
    DefaultPrompts,
)
from backend.utils import (
    create_response,
    success_response,
    error_response,
    paginated_response,
    get_utc_now,
    get_timestamp,
    validate_email,
    validate_file_extension,
    validate_file_size,
    sanitize_filename,
    get_file_extension,
    get_mime_type,
    humanize_bytes,
    ensure_directory,
    handle_errors,
    log_execution_time,
    get_client_ip,
    logger as utils_logger,
)
from backend.auth import (
    auth_service,
    get_auth_service,
)
from backend.session import (
    session_manager,
    get_session_manager,
    require_auth,
    optional_auth,
    sanitize_session_for_client,
)
from backend.services import (
    ai_service,
    project_service,
    file_service,
    export_service,
    pdf_service,
    get_ai_service,
    get_project_service,
    get_file_service,
    get_export_service,
    get_pdf_service,
)
from backend.data_service import (
    data_service,
    get_data_service,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

class CORSMiddleware:
    
    @staticmethod
    def add_cors_headers(response, request_obj=None):
        origin = "*"
        if request_obj:
            request_origin = request_obj.headers.get("Origin", "")
            if request_origin in ALLOWED_ORIGINS:
                origin = request_origin
            elif request_origin:
                for allowed in ALLOWED_ORIGINS:
                    if request_origin.startswith(allowed.rstrip('/')):
                        origin = request_origin
                        break
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(ALLOWED_METHODS)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(ALLOWED_HEADERS)
        response.headers["Access-Control-Allow-Credentials"] = str(ALLOWED_CREDENTIALS).lower()
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, X-Response-Time, X-Request-ID"
        return response
    
    @staticmethod
    def handle_preflight():
        request_origin = request.headers.get("Origin", "")
        origin_allowed = any(request_origin in ALLOWED_ORIGINS or request_origin.startswith(a.rstrip('/')) for a in ALLOWED_ORIGINS)
        if origin_allowed or request_origin == "":
            response = make_response("", HttpStatus.OK)
            response.headers["Access-Control-Allow-Origin"] = request_origin or "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(ALLOWED_METHODS)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(ALLOWED_HEADERS)
            response.headers["Access-Control-Allow-Credentials"] = str(ALLOWED_CREDENTIALS).lower()
            response.headers["Access-Control-Max-Age"] = "86400"
            response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, X-Response-Time, X-Request-ID"
            return response
        else:
            response = make_response(jsonify({"success": False, "message": "Origin not allowed", "error_code": ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS.value}), HttpStatus.FORBIDDEN)
            response.headers["Content-Type"] = ContentType.JSON
            return response


cors = CORSMiddleware()


def make_json_response(data: dict, status_code: int = HttpStatus.OK, extra_headers: dict = None):
    response = make_response(jsonify(data), status_code)
    response.headers["Content-Type"] = ContentType.JSON
    if extra_headers:
        for key, value in extra_headers.items():
            response.headers[key] = value
    response = cors.add_cors_headers(response, request)
    return response


def register_routes(app):

    # ========================================================================
    # HEALTH & STATUS
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/health", methods=["GET"])
    @handle_errors
    def health_check():
        return make_json_response(success_response(data={"status": "healthy", "service": "Graphico Pro API", "version": "1.0.0", "timestamp": get_timestamp(), "environment": "production" if not SERVER_DEBUG else "development"}, message="Graphico Pro API is running")[0])

    @app.route(f"{API_PREFIX}/status", methods=["GET"])
    @handle_errors
    def api_status():
        try: ai_models = ai_service.get_available_models()
        except: ai_models = []
        try: active_sessions = session_manager.store.get_active_sessions_count()
        except: active_sessions = 0
        return make_json_response(success_response(data={"api_version": API_PREFIX, "status": "operational", "available_models": len(ai_models), "models": [{"model": m["model"], "provider": m["provider"], "display_name": m["display_name"], "type": m["type"]} for m in ai_models], "active_sessions": active_sessions, "server_time": get_timestamp()}, message="API status retrieved")[0])

    # ========================================================================
    # AUTH
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/auth/google/url", methods=["GET"])
    @handle_errors
    def get_google_auth_url():
        redirect_uri = request.args.get("redirect_uri")
        if redirect_uri:
            try:
                parsed = urlparse(redirect_uri)
                origin = f"{parsed.scheme}://{parsed.netloc}"
                if not any(origin == a or origin.startswith(a.rstrip('/')) for a in ALLOWED_ORIGINS):
                    return make_json_response(error_response(message="Invalid redirect URI", error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
            except:
                return make_json_response(error_response(message="Invalid redirect URI format", error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        auth_url, _ = auth_service.google_oauth.get_authorization_url(redirect_uri=redirect_uri)
        return make_json_response(success_response(data={"auth_url": auth_url}, message="Authorization URL generated")[0])

    @app.route(f"{API_PREFIX}/auth/google/callback", methods=["POST"])
    @handle_errors
    def google_auth_callback():
        data = request.get_json(silent=True) or {}
        code = data.get("code")
        if not code: return make_json_response(error_response(message="Authorization code required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        user_data, error = auth_service.authenticate_with_google(code=code, redirect_uri=data.get("redirect_uri"), ip_address=get_client_ip(request), user_agent=request.headers.get("User-Agent", ""))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"user": user_data["user"], "session_token": user_data["session_token"], "expires_in": user_data.get("expires_in", 3600)}, message=ApiMessage.LOGIN_SUCCESS)[0])

    @app.route(f"{API_PREFIX}/auth/google/token", methods=["POST"])
    @handle_errors
    def google_token_auth():
        data = request.get_json(silent=True) or {}
        id_token = data.get("id_token")
        if not id_token: return make_json_response(error_response(message="ID token required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        user_data, error = auth_service.authenticate_with_token(id_token)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"user": user_data["user"], "session_token": user_data["session_token"]}, message=ApiMessage.LOGIN_SUCCESS)[0])

    @app.route(f"{API_PREFIX}/auth/logout", methods=["POST"])
    @handle_errors
    def logout():
        token = session_manager.extract_token(request)
        if not token: return make_json_response(error_response(message="No session token", error_code=ErrorCode.AUTH_MISSING_TOKEN, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        success, error = auth_service.logout(token)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(message=ApiMessage.LOGOUT_SUCCESS)[0])

    @app.route(f"{API_PREFIX}/auth/me", methods=["GET"])
    @handle_errors
    def get_current_user():
        user_session, error = session_manager.authenticate_request(request)
        if error: return make_json_response(error[0], status_code=error[1])
        user, error = auth_service.get_current_user(session_manager.extract_token(request))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"user": user}, message="User info retrieved")[0])

    @app.route(f"{API_PREFIX}/auth/session/refresh", methods=["POST"])
    @handle_errors
    def refresh_session():
        token = session_manager.extract_token(request)
        if not token: return make_json_response(error_response(message="No session token", error_code=ErrorCode.AUTH_MISSING_TOKEN, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        if not session_manager.store.refresh_session(token): return make_json_response(error_response(message=ApiMessage.SESSION_EXPIRED, error_code=ErrorCode.AUTH_EXPIRED_TOKEN, status_code=HttpStatus.UNAUTHORIZED)[0], status_code=HttpStatus.UNAUTHORIZED)
        return make_json_response(success_response(message="Session refreshed")[0])

    # ========================================================================
    # AI
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/ai/models", methods=["GET"])
    @handle_errors
    def get_ai_models():
        models = ai_service.get_available_models()
        return make_json_response(success_response(data={"models": models, "total": len(models), "chat_models": [m for m in models if m.get("type")=="chat"], "image_models": [m for m in models if m.get("type")=="image"]}, message="Models retrieved")[0])

    @app.route(f"{API_PREFIX}/ai/chat", methods=["POST"])
    @handle_errors
    @require_auth
    def chat_completion(user_session=None):
        data = request.get_json(silent=True) or {}
        messages = data.get("messages", [])
        if not messages or not isinstance(messages, list): return make_json_response(error_response(message="Messages array required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg: return make_json_response(error_response(message=f"Message {i} needs role and content", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        
        system_prompt = data.get("system_prompt")
        project_id = data.get("project_id")
        
        # Auto-include ALL project files context
        if project_id and user_session:
            project = project_service.get_project(project_id)
            if project and project.get("user_id") == user_session.get("user_id"):
                files = project.get("files", [])
                if files:
                    context_parts = []
                    for idx, f in enumerate(files, 1):
                        fp = f.get("path")
                        if fp and Path(fp).exists():
                            try:
                                preview, _ = data_service.get_preview(fp, rows=3)
                                if preview: context_parts.append(f"FILE {idx} ({f.get('original_name','unknown')}): Columns: {', '.join(preview.get('columns',[]))}. Rows: {preview.get('row_count',0)}.")
                            except: pass
                    if context_parts:
                        ctx = "\n\n[SYSTEM NOTE: This project has the following data files:\n" + "\n".join(context_parts) + "\nUse this context to answer data-related questions accurately.]"
                        system_prompt = (system_prompt + ctx) if system_prompt else ctx.strip()
        
        result, error = ai_service.chat(messages=messages, model=data.get("model"), system_prompt=system_prompt, max_tokens=data.get("max_tokens",2000), temperature=data.get("temperature",0.7))
        if error: return make_json_response(error[0], status_code=error[1])
        
        if project_id and user_session:
            project = project_service.get_project(project_id)
            if project and project.get("user_id") == user_session.get("user_id"):
                for msg in messages: project_service.add_chat_history(project_id, {"role":msg.get("role"),"content":msg.get("content"),"timestamp":get_timestamp()})
                project_service.add_chat_history(project_id, {"role":"assistant","content":result.get("content"),"model":result.get("model"),"timestamp":get_timestamp()})
        return make_json_response(success_response(data=result, message="Chat generated")[0])

    @app.route(f"{API_PREFIX}/ai/image/generate", methods=["POST"])
    @handle_errors
    @require_auth
    def generate_image(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("prompt"): return make_json_response(error_response(message="Prompt required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        n = max(1, min(int(data.get("n",1)), SystemLimits.MAX_IMAGE_GENERATION_BATCH))
        result, error = ai_service.generate_image(prompt=data["prompt"], model=data.get("model"), size=data.get("size","1024x1024"), quality=data.get("quality","standard"), n=n)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data=result, message="Image generated")[0])

    @app.route(f"{API_PREFIX}/ai/analyze/pdf", methods=["POST"])
    @handle_errors
    @require_auth
    def analyze_pdf(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path"): return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        at = data.get("analysis_type","summarize")
        if at not in ["summarize","extract","analyze","keywords","questions"]: at = "summarize"
        result, error = pdf_service.analyze_with_ai(file_path=data["file_path"], ai_service=ai_service, analysis_type=at, model=data.get("model"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data=result, message="PDF analyzed")[0])

    @app.route(f"{API_PREFIX}/ai/pdf/extract-text", methods=["POST"])
    @handle_errors
    @require_auth
    def extract_pdf_text(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path"): return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        text, error = pdf_service.extract_text(data["file_path"])
        if error: return make_json_response(error[0], status_code=error[1])
        meta, _ = pdf_service.extract_metadata(data["file_path"])
        return make_json_response(success_response(data={"text":text,"length":len(text) if text else 0,"metadata":meta}, message="Text extracted")[0])

    @app.route(f"{API_PREFIX}/ai/document/generate", methods=["POST"])
    @handle_errors
    @require_auth
    def generate_document(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("topic"): return make_json_response(error_response(message="Topic required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        lt = {"short":500,"medium":1500,"long":3000}
        result, error = ai_service.chat(messages=[{"role":"user","content":f"Generate a {data.get('document_type','report')} about: {data['topic']}"}], system_prompt=DefaultPrompts.DOCUMENT_WRITER, max_tokens=lt.get(data.get("length","medium"),1500), temperature=0.7)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"content":result.get("content"),"model":result.get("model"),"usage":result.get("usage",{})}, message="Document generated")[0])

    @app.route(f"{API_PREFIX}/ai/presentation/create", methods=["POST"])
    @handle_errors
    @require_auth
    def create_presentation(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("topic"): return make_json_response(error_response(message="Topic required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        sc = max(1, min(int(data.get("slide_count",10)), SystemLimits.MAX_PRESENTATION_SLIDES))
        result, error = ai_service.chat(messages=[{"role":"user","content":f"Create a {sc}-slide presentation about: {data['topic']}"}], system_prompt=DefaultPrompts.PRESENTATION_CREATOR, max_tokens=3000, temperature=0.8)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"content":result.get("content"),"model":result.get("model"),"usage":result.get("usage",{}),"slide_count":sc,"topic":data["topic"]}, message="Presentation created")[0])

    # ========================================================================
    # PROJECTS
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/projects", methods=["GET"])
    @handle_errors
    @require_auth
    def list_projects(user_session=None):
        uid = user_session.get("user_id")
        page = max(1, int(request.args.get("page", Pagination.DEFAULT_PAGE)))
        pp = min(Pagination.MAX_PER_PAGE, max(Pagination.MIN_PER_PAGE, int(request.args.get("per_page", Pagination.DEFAULT_PER_PAGE))))
        projects = project_service.get_user_projects(uid, request.args.get("status"), page, pp)
        return make_json_response(paginated_response(items=projects, total=project_service.get_user_projects_count(uid, request.args.get("status")), page=page, per_page=pp, message="Projects retrieved")[0])

    @app.route(f"{API_PREFIX}/projects", methods=["POST"])
    @handle_errors
    @require_auth
    def create_project(user_session=None):
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        if not name or not name.strip(): return make_json_response(error_response(message="Project name required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        project, error = project_service.create_project(user_id=user_session.get("user_id"), name=name.strip(), description=data.get("description",""), project_type=data.get("project_type","general"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data=project, message=ApiMessage.CREATED)[0], status_code=HttpStatus.CREATED)

    @app.route(f"{API_PREFIX}/projects/<project_id>", methods=["GET"])
    @handle_errors
    @require_auth
    def get_project(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        return make_json_response(success_response(data=p, message="Project retrieved")[0])

    @app.route(f"{API_PREFIX}/projects/<project_id>", methods=["PUT"])
    @handle_errors
    @require_auth
    def update_project(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        updated, error = project_service.update_project(project_id, request.get_json(silent=True) or {})
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data=updated, message=ApiMessage.UPDATED)[0])

    @app.route(f"{API_PREFIX}/projects/<project_id>", methods=["DELETE"])
    @handle_errors
    @require_auth
    def delete_project(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        success, error = project_service.delete_project(project_id)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(message=ApiMessage.DELETED)[0])

    @app.route(f"{API_PREFIX}/projects/<project_id>/archive", methods=["POST"])
    @handle_errors
    @require_auth
    def archive_project(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        success, error = project_service.archive_project(project_id)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(message="Archived")[0])

    @app.route(f"{API_PREFIX}/projects/<project_id>/history", methods=["GET"])
    @handle_errors
    @require_auth
    def get_project_history(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        history = p.get("history",[])
        limit = int(request.args.get("limit",100))
        if limit > 0: history = history[-limit:]
        return make_json_response(success_response(data={"history":history,"total":len(history),"project_id":project_id}, message="History retrieved")[0])

    @app.route(f"{API_PREFIX}/projects/<project_id>/history", methods=["DELETE"])
    @handle_errors
    @require_auth
    def clear_project_history(project_id, user_session=None):
        p = project_service.get_project(project_id)
        if not p or p.get("user_id") != user_session.get("user_id"): return make_json_response(error_response(message=ApiMessage.PROJECT_NOT_FOUND if not p else ApiMessage.FORBIDDEN, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.NOT_FOUND if not p else HttpStatus.FORBIDDEN)
        success, error = project_service.clear_chat_history(project_id)
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(message="History cleared")[0])

    # ========================================================================
    # FILES
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/files/upload", methods=["POST"])
    @handle_errors
    @require_auth
    def upload_file(user_session=None):
        if "file" not in request.files: return make_json_response(error_response(message="No file provided", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        file = request.files["file"]
        if not file.filename: return make_json_response(error_response(message="No file selected", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        uid = user_session.get("user_id")
        file_info, error = file_service.upload_file(file_data=file.read(), filename=file.filename, user_id=uid, project_id=request.form.get("project_id"))
        if error: return make_json_response(error[0], status_code=error[1])
        # Allow multiple files — just add, don't delete
        pid = request.form.get("project_id")
        if pid and file_info:
            p = project_service.get_project(pid)
            if p and p.get("user_id") == uid: project_service.add_file_to_project(pid, file_info)
        return make_json_response(success_response(data=file_info, message=ApiMessage.UPLOAD_SUCCESS)[0], status_code=HttpStatus.CREATED)

    @app.route(f"{API_PREFIX}/files", methods=["GET"])
    @handle_errors
    @require_auth
    def list_files(user_session=None):
        files = file_service.get_user_files(user_session.get("user_id"), request.args.get("category"))
        return make_json_response(success_response(data={"files":files,"total":len(files),"storage":file_service.get_user_storage_stats(user_session.get("user_id"))}, message="Files retrieved")[0])

    @app.route(f"{API_PREFIX}/files/<file_id>", methods=["GET"])
    @handle_errors
    @require_auth
    def download_file(file_id, user_session=None):
        uid = user_session.get("user_id")
        ud = file_service.upload_dir / uid
        if not ud.exists(): return make_json_response(error_response(message=ApiMessage.FILE_NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)[0], status_code=HttpStatus.NOT_FOUND)
        fp = None; fn = None
        try:
            for f in ud.iterdir():
                if f.is_file() and f.stem == file_id: fp = f; break
        except: pass
        if not fp: return make_json_response(error_response(message=ApiMessage.FILE_NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)[0], status_code=HttpStatus.NOT_FOUND)
        fd, error = file_service.get_file(str(fp))
        if error: return make_json_response(error[0], status_code=error[1])
        try:
            resp = send_file(io.BytesIO(fd), mimetype=get_mime_type(fp.name), as_attachment=True, download_name=fn or fp.name)
            return cors.add_cors_headers(resp, request)
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return make_json_response(error_response(message="Download error", error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.INTERNAL_SERVER_ERROR)[0], status_code=HttpStatus.INTERNAL_SERVER_ERROR)

    @app.route(f"{API_PREFIX}/files/<file_id>", methods=["DELETE"])
    @handle_errors
    @require_auth
    def delete_file(file_id, user_session=None):
        uid = user_session.get("user_id")
        ud = file_service.upload_dir / uid
        if not ud.exists(): return make_json_response(error_response(message=ApiMessage.FILE_NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)[0], status_code=HttpStatus.NOT_FOUND)
        fp = None
        try:
            for f in ud.iterdir():
                if f.is_file() and f.stem == file_id: fp = f; break
        except: pass
        if not fp: return make_json_response(error_response(message=ApiMessage.FILE_NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)[0], status_code=HttpStatus.NOT_FOUND)
        success, error = file_service.delete_file(str(fp))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(message=ApiMessage.DELETED)[0])

    # ========================================================================
    # EXPORTS
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/export/chat", methods=["POST"])
    @handle_errors
    @require_auth
    def export_chat(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("messages"): return make_json_response(error_response(message="Messages required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        path, error = export_service.export_chat_history(data["messages"], data.get("format","json"), data.get("filename","chat_export"), user_session.get("user_id"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":path,"format":data.get("format","json")}, message=ApiMessage.EXPORT_SUCCESS)[0])

    @app.route(f"{API_PREFIX}/export/document", methods=["POST"])
    @handle_errors
    @require_auth
    def export_document(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("content"): return make_json_response(error_response(message="Content required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        path, error = export_service.export_document(data["content"], data.get("format","pdf"), data.get("filename","document_export"), user_session.get("user_id"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":path,"format":data.get("format","pdf")}, message=ApiMessage.EXPORT_SUCCESS)[0])

    @app.route(f"{API_PREFIX}/export/presentation", methods=["POST"])
    @handle_errors
    @require_auth
    def export_presentation(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("slides"): return make_json_response(error_response(message="Slides required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        path, error = export_service.export_to_pptx(data["slides"], data.get("filename","presentation_export"), user_session.get("user_id"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":path,"format":"pptx"}, message=ApiMessage.EXPORT_SUCCESS)[0])

    # ========================================================================
    # DATA
    # ========================================================================
    
    @app.route(f"{API_PREFIX}/data/preview", methods=["GET"])
    @handle_errors
    @require_auth
    def data_preview(user_session=None):
        fp = request.args.get("file_path")
        if not fp: return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        preview, error = data_service.get_preview(fp, int(request.args.get("rows",20)))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data=preview, message="Preview retrieved")[0])

    @app.route(f"{API_PREFIX}/data/clean", methods=["POST"])
    @handle_errors
    @require_auth
    def data_clean(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path"): return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        cleaned, error = data_service.clean_data(data["file_path"], data.get("drop_duplicates",True), data.get("fill_numeric","mean"), data.get("drop_null_rows",False), data.get("fill_categorical","mode"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":cleaned}, message="Data cleaned")[0])

    @app.route(f"{API_PREFIX}/data/merge", methods=["POST"])
    @handle_errors
    @require_auth
    def data_merge(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path_1") or not data.get("file_path_2") or not data.get("on_column"): return make_json_response(error_response(message="file_path_1, file_path_2, on_column required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        merged, error = data_service.merge_files(data["file_path_1"], data["file_path_2"], data["on_column"], data.get("how","inner"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":merged}, message="Merged")[0])

    @app.route(f"{API_PREFIX}/data/split", methods=["POST"])
    @handle_errors
    @require_auth
    def data_split(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path"): return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        paths, error = data_service.split_file(data["file_path"], data.get("split_column"), data.get("num_splits",2))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_paths":paths}, message="Split")[0])

    @app.route(f"{API_PREFIX}/data/edit-cell", methods=["POST"])
    @handle_errors
    @require_auth
    def data_edit_cell(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or data.get("row_index") is None or not data.get("column"): return make_json_response(error_response(message="file_path, row_index, column required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        updated, error = data_service.edit_cell(data["file_path"], int(data["row_index"]), data["column"], str(data.get("new_value","")))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":updated}, message="Cell edited")[0])

    @app.route(f"{API_PREFIX}/data/add-row", methods=["POST"])
    @handle_errors
    @require_auth
    def data_add_row(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or not data.get("row_data"): return make_json_response(error_response(message="file_path and row_data required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        updated, error = data_service.add_row(data["file_path"], data["row_data"])
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":updated}, message="Row added")[0])

    @app.route(f"{API_PREFIX}/data/delete-row", methods=["POST"])
    @handle_errors
    @require_auth
    def data_delete_row(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or data.get("row_index") is None: return make_json_response(error_response(message="file_path and row_index required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        updated, error = data_service.delete_row(data["file_path"], int(data["row_index"]))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":updated}, message="Row deleted")[0])

    @app.route(f"{API_PREFIX}/data/add-column", methods=["POST"])
    @handle_errors
    @require_auth
    def data_add_column(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or not data.get("column_name"): return make_json_response(error_response(message="file_path and column_name required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        updated, error = data_service.add_column(data["file_path"], data["column_name"], data.get("default_value",""))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":updated}, message="Column added")[0])

    @app.route(f"{API_PREFIX}/data/delete-column", methods=["POST"])
    @handle_errors
    @require_auth
    def data_delete_column(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or not data.get("column_name"): return make_json_response(error_response(message="file_path and column_name required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        updated, error = data_service.delete_column(data["file_path"], data["column_name"])
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"file_path":updated}, message="Column deleted")[0])

    @app.route(f"{API_PREFIX}/data/plot", methods=["POST"])
    @handle_errors
    @require_auth
    def data_plot(user_session=None):
        data = request.get_json(silent=True) or {}
        if not data.get("file_path") or not data.get("plot_type"): return make_json_response(error_response(message="file_path and plot_type required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        plot_json, error = data_service.generate_plot(data["file_path"], data["plot_type"], data.get("x_column"), data.get("y_column"), data.get("title","Graphico Pro — Plot"))
        if error: return make_json_response(error[0], status_code=error[1])
        return make_json_response(success_response(data={"plot_json":plot_json,"plot_type":data["plot_type"]}, message="Plot generated")[0])

    @app.route(f"{API_PREFIX}/data/report", methods=["POST"])
    @handle_errors
    @require_auth
    def data_report(user_session=None):
        data = request.get_json(silent=True) or {}
        file_path = data.get("file_path")
        if not file_path: return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        pdf_path, error = data_service.generate_report_pdf(file_path, user_session.get("user_id"), data.get("include_plots",True))
        if error: return make_json_response(error[0], status_code=error[1])
        # Send the PDF file directly for browser download
        try:
            resp = send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=Path(pdf_path).name)
            return cors.add_cors_headers(resp, request)
        except Exception as e:
            logger.error(f"Error sending report: {e}")
            return make_json_response(error_response(message="Error sending report", error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.INTERNAL_SERVER_ERROR)[0], status_code=HttpStatus.INTERNAL_SERVER_ERROR)

    @app.route(f"{API_PREFIX}/data/export", methods=["POST"])
    @handle_errors
    @require_auth
    def data_export(user_session=None):
        data = request.get_json(silent=True) or {}
        file_path = data.get("file_path")
        if not file_path: return make_json_response(error_response(message="File path required", error_code=ErrorCode.VALIDATION_MISSING_FIELD, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
        format = data.get("format","csv")
        exported_path, error = data_service.export_data(file_path, format, user_session.get("user_id"))
        if error: return make_json_response(error[0], status_code=error[1])
        # Send the file directly for browser download
        mime_map = {'csv':'text/csv', 'json':'application/json', 'xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'parquet':'application/octet-stream'}
        try:
            resp = send_file(exported_path, mimetype=mime_map.get(format,'application/octet-stream'), as_attachment=True, download_name=Path(exported_path).name)
            return cors.add_cors_headers(resp, request)
        except Exception as e:
            logger.error(f"Error sending export: {e}")
            return make_json_response(error_response(message="Error sending file", error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.INTERNAL_SERVER_ERROR)[0], status_code=HttpStatus.INTERNAL_SERVER_ERROR)

    # ========================================================================
    # CORS PREFLIGHT
    # ========================================================================
    
    @app.route("/api/<path:path>", methods=["OPTIONS"])
    @app.route(f"{API_PREFIX}/<path:path>", methods=["OPTIONS"])
    def handle_cors_preflight(path=None): return cors.handle_preflight()

    @app.route(f"{API_PREFIX}/health", methods=["OPTIONS"])
    def handle_health_preflight(): return cors.handle_preflight()

    logger.info("All API routes registered successfully")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e): return make_json_response(error_response(message=str(e) or ApiMessage.BAD_REQUEST, error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
    @app.errorhandler(401)
    def unauthorized(e): return make_json_response(error_response(message=ApiMessage.UNAUTHORIZED, error_code=ErrorCode.AUTH_MISSING_TOKEN, status_code=HttpStatus.UNAUTHORIZED)[0], status_code=HttpStatus.UNAUTHORIZED)
    @app.errorhandler(403)
    def forbidden(e): return make_json_response(error_response(message=ApiMessage.FORBIDDEN, error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS, status_code=HttpStatus.FORBIDDEN)[0], status_code=HttpStatus.FORBIDDEN)
    @app.errorhandler(404)
    def not_found(e): return make_json_response(error_response(message=ApiMessage.NOT_FOUND, error_code=ErrorCode.RESOURCE_NOT_FOUND, status_code=HttpStatus.NOT_FOUND)[0], status_code=HttpStatus.NOT_FOUND)
    @app.errorhandler(405)
    def method_not_allowed(e): return make_json_response(error_response(message=ApiMessage.METHOD_NOT_ALLOWED, error_code=ErrorCode.VALIDATION_INVALID_FORMAT, status_code=HttpStatus.METHOD_NOT_ALLOWED)[0], status_code=HttpStatus.METHOD_NOT_ALLOWED)
    @app.errorhandler(413)
    def too_large(e): return make_json_response(error_response(message=ApiMessage.FILE_TOO_LARGE, error_code=ErrorCode.FILE_TOO_LARGE, status_code=HttpStatus.BAD_REQUEST)[0], status_code=HttpStatus.BAD_REQUEST)
    @app.errorhandler(429)
    def rate_limited(e): return make_json_response(error_response(message=ApiMessage.RATE_LIMITED, error_code=ErrorCode.AI_RATE_LIMITED, status_code=HttpStatus.TOO_MANY_REQUESTS)[0], status_code=HttpStatus.TOO_MANY_REQUESTS)
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"500: {e}", exc_info=True)
        return make_json_response(error_response(message=ApiMessage.INTERNAL_ERROR, error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.INTERNAL_SERVER_ERROR)[0], status_code=HttpStatus.INTERNAL_SERVER_ERROR)
    @app.errorhandler(502)
    def bad_gateway(e): return make_json_response(error_response(message=ApiMessage.SERVICE_UNAVAILABLE, error_code=ErrorCode.AI_PROVIDER_ERROR, status_code=HttpStatus.BAD_GATEWAY)[0], status_code=HttpStatus.BAD_GATEWAY)
    @app.errorhandler(503)
    def unavailable(e): return make_json_response(error_response(message=ApiMessage.SERVICE_UNAVAILABLE, error_code=ErrorCode.SERVER_INTERNAL, status_code=HttpStatus.SERVICE_UNAVAILABLE)[0], status_code=HttpStatus.SERVICE_UNAVAILABLE)
    logger.info("Error handlers registered")


# ============================================================================
# MIDDLEWARE
# ============================================================================

def register_middleware(app):
    @app.before_request
    def before_request():
        if request.method == "OPTIONS": return None
        logger.info(f"→ {request.method} {request.path} from {get_client_ip(request)}")
    @app.after_request
    def after_request(response):
        response = cors.add_cors_headers(response, request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
    logger.info("Middleware registered")
    