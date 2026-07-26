"""
Graphico Pro — Streamlit Dashboard
Pure Streamlit frontend that communicates with the Flask backend API.
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json
import io
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "https://graphico-backend.streamlit.app"
API_URL = f"{API_BASE_URL}/api/v1"

st.set_page_config(
    page_title="Graphico Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SESSION STATE
# ============================================================================

if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "available_models" not in st.session_state:
    st.session_state.available_models = []
if "data_preview" not in st.session_state:
    st.session_state.data_preview = None
if "data_file_path" not in st.session_state:
    st.session_state.data_file_path = None
if "projects" not in st.session_state:
    st.session_state.projects = []
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None

# ============================================================================
# API HELPERS
# ============================================================================

def api_request(method, endpoint, data=None, files=None, is_file_download=False):
    headers = {}
    if st.session_state.session_token:
        headers["Authorization"] = f"Bearer {st.session_state.session_token}"
    
    url = f"{API_URL}{endpoint}"
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            if files:
                resp = requests.post(url, headers=headers, files=files, timeout=60)
            else:
                headers["Content-Type"] = "application/json"
                resp = requests.post(url, headers=headers, json=data, timeout=60)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            return None
        
        if is_file_download and resp.status_code == 200:
            return resp
        
        if resp.status_code == 200:
            return resp.json()
        
        try:
            err = resp.json()
            st.error(err.get("message", "Unknown error"))
        except:
            st.error(f"HTTP {resp.status_code}")
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

# ============================================================================
# AUTHENTICATION
# ============================================================================

def login_page():
    st.title("Graphico Pro")
    st.subheader("The AI Operating System for Creativity")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")
        st.markdown("### Sign in to your workspace")
        
        # Get Google OAuth URL
        resp = api_request("GET", "/auth/google/url")
        if resp and resp.get("success"):
            auth_url = resp["data"]["auth_url"]
            st.markdown(f"[![Sign in with Google](https://developers.google.com/identity/images/btn_google_signin_dark_normal_web.png)]({auth_url})")
        
        st.markdown("---")
        st.caption("Or paste your session token:")
        token_input = st.text_input("Session Token", type="password", key="token_input")
        if st.button("Submit Token"):
            st.session_state.session_token = token_input.strip()
            resp = api_request("GET", "/auth/me")
            if resp and resp.get("success"):
                st.session_state.user = resp["data"]["user"]
                st.rerun()

    # Handle OAuth callback
    params = st.query_params
    if "code" in params:
        code = params["code"]
        resp = api_request("POST", "/auth/google/callback", data={"code": code, "redirect_uri": st.query_params.get("redirect_uri", "")})
        if resp and resp.get("success"):
            st.session_state.session_token = resp["data"]["session_token"]
            st.session_state.user = resp["data"]["user"]
            st.query_params.clear()
            st.rerun()

# ============================================================================
# MAIN APP
# ============================================================================

def main_app():
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/40x40.png?text=GP", width=40)
        st.title("Graphico Pro")
        
        if st.session_state.user:
            st.write(f"👤 {st.session_state.user.get('name', 'User')}")
            st.write(f"📧 {st.session_state.user.get('email', '')}")
        
        page = st.radio("Navigation", ["💬 Chat", "📊 Data Analysis", "📁 Projects", "⚙️ Settings"])
        
        if st.button("🚪 Logout"):
            api_request("POST", "/auth/logout")
            st.session_state.clear()
            st.rerun()
    
    if page == "💬 Chat":
        chat_page()
    elif page == "📊 Data Analysis":
        data_page()
    elif page == "📁 Projects":
        projects_page()
    elif page == "⚙️ Settings":
        settings_page()

# ============================================================================
# CHAT PAGE
# ============================================================================

def chat_page():
    st.title("💬 Workspace Chat")
    
    # Model selector and project selector
    col1, col2 = st.columns(2)
    with col1:
        load_models()
        models_list = [m["model"] for m in st.session_state.available_models if m.get("type") == "chat"]
        display_names = [f"{m['display_name']} ({m['provider']})" for m in st.session_state.available_models if m.get("type") == "chat"]
        selected_model = st.selectbox("AI Model", display_names, key="model_select")
        selected_model_id = models_list[display_names.index(selected_model)] if display_names else None
    
    with col2:
        load_projects()
        project_names = ["None"] + [p["name"] for p in st.session_state.projects]
        selected_project_name = st.selectbox("Save to Project", project_names, key="project_select")
        if selected_project_name != "None":
            for p in st.session_state.projects:
                if p["name"] == selected_project_name:
                    st.session_state.active_project_id = p["project_id"]
                    break
        else:
            st.session_state.active_project_id = None
    
    # Chat history
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.chat_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                st.chat_message("user").write(content)
            elif role == "assistant":
                st.chat_message("assistant").markdown(content)
            elif role == "system":
                st.error(content)
    
    # Chat input
    if prompt := st.chat_input("Message the assistant…"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        messages_payload = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
        
        data = {"messages": messages_payload}
        if selected_model_id:
            data["model"] = selected_model_id
        if st.session_state.active_project_id:
            data["project_id"] = st.session_state.active_project_id
        
        with st.spinner("Thinking..."):
            resp = api_request("POST", "/ai/chat", data=data)
        
        if resp and resp.get("success"):
            st.session_state.chat_messages.append({"role": "assistant", "content": resp["data"]["content"]})
        else:
            st.session_state.chat_messages.append({"role": "system", "content": "Failed to get response"})
        
        st.rerun()
    
    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ============================================================================
# DATA PAGE
# ============================================================================

def data_page():
    st.title("📊 Data Analysis")
    
    # Upload section
    st.subheader("Upload Data")
    uploaded_file = st.file_uploader("Choose a CSV or JSON file", type=["csv", "json"])
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Project name (optional)", value="Data Analysis Project")
    with col2:
        if uploaded_file and st.button("Upload & Analyze"):
            # Create project
            resp = api_request("POST", "/projects", data={"name": project_name, "project_type": "data"})
            if resp and resp.get("success"):
                project_id = resp["data"]["project_id"]
                # Upload file
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                upload_resp = requests.post(
                    f"{API_URL}/files/upload",
                    headers={"Authorization": f"Bearer {st.session_state.session_token}"},
                    files=files,
                    data={"project_id": project_id}
                )
                if upload_resp.status_code == 201:
                    upload_data = upload_resp.json()
                    st.session_state.data_file_path = upload_data["data"]["path"]
                    st.success("File uploaded!")
                    st.rerun()
    
    # Manual file path
    st.divider()
    file_path = st.text_input("Or enter file path directly", value=st.session_state.data_file_path or "")
    if file_path and st.button("Load Data"):
        st.session_state.data_file_path = file_path
        resp = api_request("GET", f"/data/preview?file_path={file_path}")
        if resp and resp.get("success"):
            st.session_state.data_preview = resp["data"]
    
    # Display data
    if st.session_state.data_preview:
        preview = st.session_state.data_preview
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rows", preview.get("row_count", 0))
        col2.metric("Columns", len(preview.get("columns", [])))
        total_null = sum(preview.get("null_counts", {}).values())
        col3.metric("Missing Values", total_null)
        numeric_cols = len(preview.get("basic_stats", {}))
        col4.metric("Numeric Columns", numeric_cols)
        
        # Table
        st.subheader("Data Preview")
        if preview.get("sample_rows"):
            df = pd.DataFrame(preview["sample_rows"])
            st.dataframe(df, use_container_width=True)
        
        # Actions
        st.subheader("Actions")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("🧹 Clean Data"):
                resp = api_request("POST", "/data/clean", data={"file_path": st.session_state.data_file_path})
                if resp and resp.get("success"):
                    st.session_state.data_file_path = resp["data"]["file_path"]
                    st.success("Data cleaned!")
                    st.rerun()
        
        with col2:
            if st.button("📈 Plot"):
                st.session_state.show_plot = True
        
        with col3:
            if st.button("📄 Report PDF"):
                resp = requests.post(
                    f"{API_URL}/data/report",
                    headers={"Authorization": f"Bearer {st.session_state.session_token}", "Content-Type": "application/json"},
                    json={"file_path": st.session_state.data_file_path, "include_plots": True}
                )
                if resp.status_code == 200:
                    st.download_button("⬇️ Download PDF", resp.content, "report.pdf", "application/pdf")
        
        with col4:
            if st.button("📥 Export CSV"):
                resp = requests.post(
                    f"{API_URL}/data/export",
                    headers={"Authorization": f"Bearer {st.session_state.session_token}", "Content-Type": "application/json"},
                    json={"file_path": st.session_state.data_file_path, "format": "csv"}
                )
                if resp.status_code == 200:
                    st.download_button("⬇️ Download CSV", resp.content, "export.csv", "text/csv")
        
        with col5:
            if st.button("📥 Export JSON"):
                resp = requests.post(
                    f"{API_URL}/data/export",
                    headers={"Authorization": f"Bearer {st.session_state.session_token}", "Content-Type": "application/json"},
                    json={"file_path": st.session_state.data_file_path, "format": "json"}
                )
                if resp.status_code == 200:
                    st.download_button("⬇️ Download JSON", resp.content, "export.json", "application/json")
        
        # Plot section
        if st.session_state.get("show_plot"):
            st.subheader("Plot Configuration")
            cols = preview.get("columns", [])
            col1, col2, col3 = st.columns(3)
            with col1:
                plot_type = st.selectbox("Plot Type", ["scatter", "line", "bar", "histogram", "box", "pie", "heatmap", "area"])
            with col2:
                x_col = st.selectbox("X Axis", ["auto"] + cols)
            with col3:
                y_col = st.selectbox("Y Axis", ["auto"] + cols)
            
            if st.button("Generate Plot"):
                resp = api_request("POST", "/data/plot", data={
                    "file_path": st.session_state.data_file_path,
                    "plot_type": plot_type,
                    "x_column": None if x_col == "auto" else x_col,
                    "y_column": None if y_col == "auto" else y_col,
                })
                if resp and resp.get("success"):
                    plot_data = json.loads(resp["data"]["plot_json"])
                    fig = go.Figure(plot_data)
                    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PROJECTS PAGE
# ============================================================================

def projects_page():
    st.title("📁 Projects")
    
    if st.button("🔄 Refresh"):
        load_projects()
        st.rerun()
    
    load_projects()
    
    if not st.session_state.projects:
        st.info("No projects yet. Create one from the Chat or Data pages.")
        return
    
    for project in st.session_state.projects:
        with st.expander(f"📌 {project['name']} ({project.get('status', 'active')})"):
            st.write(f"**Description:** {project.get('description', 'No description')}")
            st.write(f"**Type:** {project.get('project_type', 'general')}")
            st.write(f"**Files:** {len(project.get('files', []))}")
            st.write(f"**Updated:** {project.get('updated_at', '')}")
            
            if st.button(f"💬 Open Chat — {project['name']}"):
                st.session_state.active_project_id = project["project_id"]
                # Load history
                resp = api_request("GET", f"/projects/{project['project_id']}/history")
                if resp and resp.get("success"):
                    st.session_state.chat_messages = resp["data"]["history"]
                st.success("Project loaded! Go to Chat page.")
            
            if st.button(f"🗑️ Delete — {project['name']}"):
                resp = api_request("DELETE", f"/projects/{project['project_id']}")
                if resp and resp.get("success"):
                    st.success("Project deleted!")
                    st.rerun()

# ============================================================================
# SETTINGS PAGE
# ============================================================================

def settings_page():
    st.title("⚙️ Settings")
    
    st.subheader("Backend Status")
    resp = api_request("GET", "/health")
    if resp:
        st.json(resp)
    
    st.subheader("Available AI Models")
    load_models()
    for model in st.session_state.available_models:
        st.write(f"• **{model['display_name']}** ({model['provider']}) — {model['type']}")

# ============================================================================
# HELPERS
# ============================================================================

def load_models():
    if not st.session_state.available_models:
        resp = api_request("GET", "/ai/models")
        if resp and resp.get("success"):
            st.session_state.available_models = resp["data"].get("models", [])

def load_projects():
    resp = api_request("GET", "/projects")
    if resp and resp.get("success"):
        st.session_state.projects = resp["data"].get("items", [])

# ============================================================================
# MAIN
# ============================================================================

if st.session_state.session_token and st.session_state.user:
    main_app()
else:
    login_page()
