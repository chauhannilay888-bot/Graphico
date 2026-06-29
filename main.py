import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
from streamlit_gsheets import GSheetsConnection
import base64
from pathlib import Path

# ================== PREMIUM UI + SECURITY ==================
ga_code = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>window.dataLayer = window.dataLayer || []; function gtag(){dataLayer.push(arguments);} gtag('js', new Date()); gtag('config', 'G-FHN9KEP6KN');</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
* { font-family: 'Inter', sans-serif; user-select: none; }
.stMetric { background: rgba(30,33,48,0.7); padding:20px; border-radius:15px; box-shadow:0 8px 32px rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); }
.gradient-text { background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight:800; }
</style>
<div id="watermark" style="position:fixed;top:35%;left:15%;font-size:48px;color:rgba(255,255,255,0.06);transform:rotate(-30deg);pointer-events:none;z-index:9999;">GRAPHICO PRO</div>"""

components.html(ga_code, height=0)

st.set_page_config(page_title="Graphico Pro", layout="wide", page_icon="📊")

# ================== GOOGLE LOGIN & USER MANAGEMENT ==================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.downloads_used = 0

conn = st.connection("gsheets", type=GSheetsConnection)

def get_or_create_user(email):
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        user_row = df[df['Email'] == email]
        if user_row.empty:
            new_user = pd.DataFrame([{
                "Email": email,
                "JoinDate": datetime.now().strftime("%Y-%m-%d"),
                "Status": "Free",
                "ExpiryDate": ""
            }])
            updated = pd.concat([df, new_user], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            return {"Email": email, "Status": "Free", "ExpiryDate": ""}
        else:
            return user_row.iloc[0].to_dict()
    except:
        return None

# Google Login (using your OAuth)
if st.session_state.user is None:
    st.markdown("<h1 class='gradient-text' style='text-align:center;'>Welcome to Graphico Pro</h1>", unsafe_allow_html=True)
    if st.button("🔑 Login with Google", use_container_width=True):
        # For Streamlit Cloud + your OAuth JSON, use st.login or custom flow
        # Placeholder - replace with actual Google OAuth flow using your client_secret
        email = st.text_input("Enter your email for demo (use real later)", "user@example.com")
        if email:
            user = get_or_create_user(email)
            st.session_state.user = user
            st.rerun()
    st.stop()

user = st.session_state.user
is_paid = user.get("Status") == "Paid" and datetime.now().strftime("%Y-%m-%d") <= user.get("ExpiryDate", "")

st.sidebar.success(f"Logged in as: {user['Email']}")
st.sidebar.info(f"Status: {'✅ Paid' if is_paid else '🔓 Free'}")

# ================== BACKEND CONNECTION ==================
def call_backend(task, data):
    try:
        resp = requests.post("https://graphico-backend.streamlit.app/", json={"task": task, "data": data}, timeout=20)
        return resp.json() if resp.ok else None
    except:
        st.warning("Backend temporarily unavailable - using local processing")
        return None

# ================== MAIN APP ==================
if 'df' not in st.session_state:
    st.session_state.df = None

st.title("📊 Graphico Pro - Data Studio")

u_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "parquet"])

if u_file and st.session_state.df is None:
    df = pd.read_csv(u_file) if u_file.name.endswith('.csv') else pd.read_excel(u_file)
    st.session_state.df = df
    st.success("Data Loaded!")

if st.session_state.df is not None:
    df = st.session_state.df
    
    # Free limit enforcement
    if not is_paid and st.session_state.downloads_used >= 1:
        st.error("🔒 Free limit reached. Please subscribe for unlimited access.")
        if st.button("💳 Upgrade Now - ₹199 / Month", type="primary"):
            st.markdown(f"[Pay with Razorpay]({ 'https://razxyz.com' })", unsafe_allow_html=True)
            # On success callback → update sheet
        st.stop()

    # Dashboard, ML, etc. (your original logic here - I can merge full version if needed)
    st.write("Your full analysis tools go here...")

    if st.button("📥 Download Graph / Report"):
        st.session_state.downloads_used += 1
        st.success("Downloaded! (Demo)")
        
        # After successful payment simulation
        if st.button("Simulate Payment Success (for testing)"):
            expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            # Update Google Sheet
            df_users = conn.read(worksheet="Sheet1")
            df_users.loc[df_users['Email'] == user['Email'], 'Status'] = "Paid"
            df_users.loc[df_users['Email'] == user['Email'], 'ExpiryDate'] = expiry
            conn.update(worksheet="Sheet1", data=df_users)
            st.success("✅ Subscription Activated!")
            st.rerun()

st.caption("Crafted with ❤️ | Backend: graphico-backend.streamlit.app")