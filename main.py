import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import numpy as np
import plotly.express as px
import os
from PIL import Image
from streamlit_gsheets import GSheetsConnection
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import base64
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

# ================== ULTRA-PREMIUM UI CSS & SECURITY ==================
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-FHN9KEP6KN');
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
* { -webkit-user-select: none !important; user-select: none !important; }
body.hidden { filter: blur(20px) !important; }
#watermark { position: fixed; top: 35%; left: 15%; font-size: 48px; color: rgba(255,255,255,0.06); transform: rotate(-30deg); pointer-events: none; z-index: 9999; }
.stMetric { background: rgba(30, 33, 48, 0.7); padding: 20px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-top: 4px solid #4facfe; }
.gradient-text { background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; letter-spacing: -1px; }
</style>

<div id="watermark">CONFIDENTIAL • GRAPHICO PRO</div>

<script>
document.addEventListener("contextmenu", e => e.preventDefault());
document.addEventListener("keydown", function(e) {
    if (e.key === "PrintScreen" || (e.ctrlKey && e.shiftKey && ["I","C","J"].includes(e.key)) || (e.ctrlKey && ["u","s","p"].includes(e.key.toLowerCase()))) e.preventDefault();
});
document.addEventListener("visibilitychange", function() {
    document.body.classList.toggle("hidden", document.hidden);
});
</script>
"""
components.html(ga_code, height=0)

@st.cache_data
def img_to_base64(image_path):
    try:
        img_bytes = Path(image_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        ext = image_path.lower().split(".")[-1]
        mime = "jpeg" if ext in ["jpg", "jpeg"] else ext
        return f"data:image/{mime};base64,{encoded}"
    except Exception:
        return ""

st.set_page_config(page_title="Graphico Pro | Data Disneyland", page_icon="Naw4n.jpg", layout="wide", initial_sidebar_state="expanded")
px.defaults.template = "plotly_dark"

# ================== USER AUTH & DB ==================
conn = st.connection("gsheets", type=GSheetsConnection)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_email(email):
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        user = df[df['Email'] == email]
        if not user.empty:
            return user.iloc[0].to_dict()
        return None
    except:
        return None

def create_user(email, password):
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        hashed = hash_password(password)
        new_user = pd.DataFrame([{
            "Email": email,
            "Password": hashed,
            "JoinDate": datetime.now().strftime("%Y-%m-%d"),
            "Status": "Free",
            "ExpiryDate": ""
        }])
        updated = pd.concat([df, new_user], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated)
        return True
    except:
        return False

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 class='gradient-text' style='text-align:center;'>Graphico Pro</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = get_user_by_email(email)
            if user and user.get("Password") == hash_password(password):
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            if get_user_by_email(email):
                st.error("Email already registered")
            else:
                if create_user(email, password):
                    st.success("Account created! Please Login.")
                else:
                    st.error("Signup failed")
    st.stop()

user = st.session_state.user
is_paid = user.get("Status") == "Paid" and datetime.now().strftime("%Y-%m-%d") <= user.get("ExpiryDate", "1900-01-01")

if not is_paid:
    st.error("🔒 The full app is locked until you subscribe.")
    if st.button("💳 Subscribe Now - ₹199 for 1 Month", type="primary", use_container_width=True):
        st.markdown("[Proceed to Razorpay Payment](https://razxyz.com)", unsafe_allow_html=True)
        if st.button("✅ Test Payment Success"):
            expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            dfu = conn.read(worksheet="Sheet1")
            dfu.loc[dfu['Email'] == user['Email'], 'Status'] = "Paid"
            dfu.loc[dfu['Email'] == user['Email'], 'ExpiryDate'] = expiry
            conn.update(worksheet="Sheet1", data=dfu)
            st.success("✅ Subscription Activated! App Unlocked.")
            st.rerun()
    st.stop()

# ================== YOUR ORIGINAL APP CODE STARTS HERE ==================

with st.sidebar:
    st.title("Navigation")
    st.divider()
    page = st.radio("✨ Control Center", ["🏠 Dashboard", "🔍 Raw Analytics", "🧠 ML Hub", "📖 Sample Vault"], index=0)
    st.markdown("### 📂 Data Source")
    u_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls", "json", "parquet"])
    if u_file:
        if "file_id" not in st.session_state or st.session_state.file_id != u_file.name:
            ext = u_file.name.split(".")[-1].lower()
            try:
                if ext == "csv":
                    data = pd.read_csv(u_file, engine="pyarrow")
                elif ext in ["xlsx", "xls"]:
                    data = pd.read_excel(u_file, engine="openpyxl")
                elif ext == "parquet":
                    data = pd.read_parquet(u_file, engine="pyarrow")
                else:
                    data = pd.read_json(u_file)
                st.session_state.df = data
                st.session_state.file_id = u_file.name
                st.toast("Data Engine Synced! 🚀", icon="✅")
            except Exception as e:
                st.error(f"Upload Failed: {e}")
    st.divider()
    st.caption("Crafted with ❤️ by Nilay")

if 'df' in st.session_state and st.session_state.df is not None and not st.session_state.df.empty:
    df = st.session_state.df
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    
    if page == "🏠 Dashboard":
        st.markdown("<h1 class='gradient-text'>📊 Visualization Dashboard</h1>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 Total Rows", f"{df.shape[0]:,}")
        m2.metric("📐 Feature Count", df.shape[1])
        m3.metric("🧹 Cells Cleaned", int(df.isnull().sum().sum()))
        st.divider()
        v_col, s_col = st.columns([4, 1])
        with s_col:
            st.markdown("### 🎨 Styling")
            mg = st.checkbox("Want to make chart of multiple columns in one figure? ")
            x_ax = st.selectbox("X-Axis (Category)", all_cols)
            if mg:
              y_ax = st.multiselect("Y-Axis (Numeric)", num_cols) if num_cols else None
              g_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Histogram", "Box Plot", "Area Chart"])
              color_by = None
            else:
              y_ax = st.selectbox("Y-Axis (Numeric)", num_cols) if num_cols else None
              g_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Pie", "Histogram", "Box Plot", "Area Chart"])
              color_by = st.selectbox("Color By (Optional)", [None] + all_cols)
        with v_col:
            st.markdown(f"### 📈 {g_type} Analysis")
            try:
                plot_df = df if len(df) <= 50000 else df.sample(50000)
                if len(df) > 50000: st.warning("⚡ Large Dataset: Displaying 50k representative points.")
                fig = None
                if y_ax:
                    args = {"data_frame": plot_df, "x": x_ax, "y": y_ax, "color": color_by, "template": "plotly_dark"}
                    if g_type == "Bar": fig = px.bar(**args)
                    elif g_type == "Line": fig = px.line(**args)
                    elif g_type == "Scatter": fig = px.scatter(**args)
                    elif g_type == "Pie": fig = px.pie(plot_df, names=x_ax, values=y_ax)
                    elif g_type == "Histogram": fig = px.histogram(plot_df, x=y_ax, color=color_by)
                    elif g_type == "Box Plot": fig = px.box(**args)
                    elif g_type == "Area Chart": fig = px.area(**args)
                if fig:
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Viz Error: {e}")
                
    elif page == "🔍 Raw Analytics":
        st.markdown("<h1 class='gradient-text'>🔍 Insight Engine</h1>", unsafe_allow_html=True)
        st.subheader("DataSet")
        st.dataframe(df.head(5000), use_container_width=True)
        st.write("#### 📊 Descriptive Stats", df.describe())
        
    elif page == "🧠 ML Hub":
        st.title("Welcome to DS Hub, optimized for your data!")
        encoding_type = st.selectbox("Select Encoding Type", ("Label Encoding", "One-Hot Encoding"))
        t_colm = st.selectbox("Select Target Column", df.columns)
        df_preview = df.copy()
        if encoding_type == "Label Encoding":
            le = LabelEncoder()
            encd_name = str(t_colm) + "_encoded"
            df_preview[encd_name] = le.fit_transform(df_preview[t_colm].astype(str))
            st.write("📊 **Preview after Encoding:**")
            st.dataframe(df_preview.head(50))
            if st.checkbox("**Keep Encoding** (Save to Dataset)"):
                st.session_state['df'] = df_preview
                st.success("Data Updated! 🚀")
                st.rerun()
        elif encoding_type == "One-Hot Encoding":
            df_preview = pd.get_dummies(df_preview, columns=[t_colm])
            st.write("📊 **Preview after Encoding:**")
            st.dataframe(df_preview.head(50))
            if st.checkbox("**Keep Encoding** (Save to Dataset)"):
                st.session_state['df'] = df_preview
                st.success("Data Updated! 🚀")
                st.rerun()
        st.divider()
        work_option = st.radio("Workflow Mode", ("Edit Data", "Make Predictions"))
        if work_option == "Edit Data":
            op = st.selectbox("Action", ("Remove Column", "Remove Row", "Replace or Add Value"))
            if op == "Remove Column":
                col_rem = st.selectbox("Select Column to drop", df.columns)
                if st.button("Delete Column"):
                    df.drop(columns=[col_rem], inplace=True)
                    st.session_state['df'] = df
                    st.rerun()
                    st.success("Removal Successful!")
            # Add your remaining edit logic here...
            st.dataframe(df.head(100))
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("Excel"):
                    towrite = io.BytesIO()
                    df.to_excel(towrite, index=False, engine="openpyxl")
                    towrite.seek(0)
                    st.download_button("Download Excel", towrite, file_name="cleaned_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            # Add other download buttons...
        elif work_option == "Make Predictions":
            # Your prediction code here
            pass

    elif page == "📖 Sample Vault":
        st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
        if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
        if os.path.exists("tutorial_PNGs"):
            files = sorted([f for f in os.listdir("tutorial_PNGs") if f.lower().endswith(".png")])
            for i in range(0, len(files), 3):
                cols = st.columns(3)
                for col, f in zip(cols, files[i:i+3]):
                    col.image(Image.open(f"tutorial_PNGs/{f}"), caption=f)

else:
    icon_b64 = img_to_base64("Naw4n.jpg")
    st.html(f"""
    <div style="text-align: center; padding: 100px 0;">
      <h1 class="gradient-text" style="font-size: 5.5em; margin-bottom: 0;">
        <img src="{icon_b64}" style="width:90px; border-radius:12px; vertical-align:middle; margin-right:20px;"> Graphico Pro
      </h1>
      <p style="font-size: 1.8em; color: gray;">The Professional Data Studio by Nilay</p>
      <br><br>
      <h4 style="color: #4facfe;">👈 Please upload a dataset in the sidebar to start analysis.</h4>
    </div>
    """)

# Payment refresh
if st.button("🔄 Refresh Subscription Status"):
    st.rerun()