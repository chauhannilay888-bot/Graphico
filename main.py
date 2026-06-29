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

# --------- 1. ULTRA-PREMIUM UI CSS & SECURITY -----------
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
// Disable right click, keys, devtools etc. (your original)
document.addEventListener("contextmenu", e => e.preventDefault());
document.addEventListener("keydown", function(e) {
    if (e.key === "PrintScreen" || (e.ctrlKey && e.shiftKey && ["I","C","J"].includes(e.key)) || (e.ctrlKey && ["u","s","p"].includes(e.key.toLowerCase()))) {
        e.preventDefault();
    }
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

# ================== USER AUTH & GOOGLE SHEET DB ==================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_or_create_user(email):
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        user = df[df['Email'] == email]
        if user.empty:
            new_user = pd.DataFrame([{
                "Email": email,
                "JoinDate": datetime.now().strftime("%Y-%m-%d"),
                "Status": "Free",
                "ExpiryDate": ""
            }])
            updated = pd.concat([df, new_user], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated)
            return {"Email": email, "Status": "Free", "ExpiryDate": ""}
        return user.iloc[0].to_dict()
    except:
        return None

if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.download_count = 0

if st.session_state.user is None:
    st.markdown("<h1 class='gradient-text' style='text-align:center;'>Graphico Pro</h1>", unsafe_allow_html=True)
    if st.button("🔑 Login with Google", type="primary", use_container_width=True):
        email = st.text_input("Enter your email", "user@gmail.com", key="login_email")
        if st.button("Continue"):
            st.session_state.user = get_or_create_user(email)
            st.rerun()
    st.stop()

user = st.session_state.user
is_paid = user.get("Status") == "Paid" and datetime.now().strftime("%Y-%m-%d") <= user.get("ExpiryDate", "1900-01-01")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("Navigation")
    st.write(f"👤 {user['Email']}")
    st.info(f"Status: {'✅ Pro' if is_paid else '🔓 Free (1 download left)'}")
    st.divider()
    page = st.radio("✨ Control Center", ["🏠 Dashboard", "🔍 Raw Analytics", "🧠 ML Hub", "📖 Sample Vault"], index=0)
    st.markdown("### 📂 Data Source")
    u_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls", "json", "parquet"])
    if u_file:
        if "file_id" not in st.session_state or st.session_state.file_id != u_file.name:
            try:
                ext = u_file.name.split(".")[-1].lower()
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
    # Review button (your original)
    st.divider()
    st.caption("Crafted with ❤️ by Nilay")

# ---------------- MAIN LOGIC (Your Original) ----------------
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
            mg = st.checkbox("Want to make clart of multiple columns in one figure? ")
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
                # BRAHMASTRA: Auto-Sampling for Plotly (Prevents 400MB browser crash)
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
        
        le = LabelEncoder()
        encoding_type = st.selectbox("Select Encoding Type", ("Label Encoding", "One-Hot Encoding"))
        t_colm = st.selectbox("Select Target Column", df.columns)
        
        # FIXED: Encoding Logic with Preview + Keep functionality
        df_preview = df.copy() 
        
        if encoding_type == "Label Encoding":
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
                  
            elif op == "Remove Row":
              row_rem = st.selectbox("Select the index number of row to drop", range(0, len(df)+1, 1))
              if st.button("Remove"):
                df.drop(index=int(row_rem), inplace=True)
                st.session_state['df'] = df
                st.rerun()
                st.success("Removal successful")
            else:
              try:
                  clm = st.selectbox("From which column", df.columns)
                  row = st.selectbox("From which index", range(0, len(df), 1))
                  if st.button("Delete permanently"):
                    df.at[int(row), clm] = None
                    st.session_state['df'] = df
                    st.rerun()
                    st.info("Deleted")
                  new_value = st.text_input("Enter the new value to replace")
                  if st.button("Replace"):
                    df.at[int(row), clm] = new_value # Update Done!
                    st.session_state['df'] = df
                    st.rerun()
                    st.sccess("Replacement Successful")
              except Exception as e:
                st.error(e)
                
            # (Additional edit logic remains same)
            st.dataframe(df.head(100))
            # download options for excel, json, parquet and csv
            st.markdown("### 📥 Download Cleaned Data"
                        " (Excel, CSV, JSON, Parquet)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("Excel"):
                    towrite = io.BytesIO()
                    df.to_excel(towrite, index=False, engine="openpyxl")
                    towrite.seek(0)
                    st.download_button("Download Excel", towrite, file_name="cleaned_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col2:
                if st.button("CSV"):
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV", csv_data, file_name="cleaned_data.csv", mime="text/csv")
            with col3:
                if st.button("JSON"):
                    json_data = df.to_json(orient="records").encode('utf-8')
                    st.download_button("Download JSON", json_data, file_name="cleaned_data.json", mime="application/json")
            with col4:
                if st.button("Parquet"):
                    towrite = io.BytesIO()
                    df.to_parquet(towrite, index=False, engine="pyarrow")
                    towrite.seek(0)
                    st.download_button("Download Parquet", towrite, file_name="cleaned_data.parquet", mime="application/octet-stream")
            
        elif work_option == "Make Predictions":
            if not num_cols:
                st.warning("⚠️ No numeric columns available for modeling.")
            else:
                feat = st.selectbox("Input Feature (Numeric)", num_cols, key="f_ml")
                targ = st.selectbox("Target Output (Numeric)", num_cols, key="t_ml")
                models = st.radio("Model Type", ("Linear Regression", "Polynomial Regression"))
                if feat and targ:
                    if models == "Linear Regression":
                        model = LinearRegression()
                        model.fit(df[[feat]], df[targ])
                        w_to_pred = st.number_input(f"Enter the value to predict for {feat} (to predict {targ})")
                        pred = model.predict([[w_to_pred]])[0]
                        st.write("📈 **Prediction**")
                        st.subheader(pred)
                    elif models == "Polynomial Regression":
                        degree = st.slider("Polynomial Degree", 2, 5, 2)
                        model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
                        model.fit(df[[feat]], df[targ])
                        w_to_pred = st.number_input(f"Enter the value to predict for {feat} (to predict {targ})")
                        pred = model.predict([[w_to_pred]])[0]
                        st.write("📈 **Prediction**")
                        st.subheader(pred)

    elif page == "📖 Sample Vault":
        st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
        if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
        if os.path.exists("tutorial_PNGs"):
            files = sorted([f for f in os.listdir("tutorial_PNGs") if f.lower().endswith(".png")])
            for i in range(0, len(files), 3):
                cols = st.columns(3)
                for col, f in zip(cols, files[i:i+3]):
                    col.image(Image.open(f"tutorial_PNGs/{f}"), caption=f)
    
# should accessable when no file is uploaded, so users can explore learning resources without uploading data
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
      <h1 class="gradient-text" style="font-size: 5.5em;">Graphico Pro</h1>
      <p style="font-size: 1.8em; color: gray;">The Professional Data Studio by Nilay</p>
      <h4 style="color: #4facfe;">Upload a dataset in sidebar to start</h4>
    </div>
    """)

# Payment
if not is_paid:
    if st.button("💳 Upgrade to Pro - ₹199 / 1 Month", type="primary"):
        st.markdown("[Pay with Razorpay](https://razxyz.com)", unsafe_allow_html=True)
        if st.button("✅ Test Payment Success"):
            expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            dfu = conn.read(worksheet="Sheet1")
            dfu.loc[dfu['Email'] == user['Email'], 'Status'] = "Paid"
            dfu.loc[dfu['Email'] == user['Email'], 'ExpiryDate'] = expiry
            conn.update(worksheet="Sheet1", data=dfu)
            st.success("Pro Activated for 30 days!")
            st.rerun()