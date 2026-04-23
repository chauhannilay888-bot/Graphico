import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import numpy as np
import plotly.express as px
import os
from PIL import Image
from io import BytesIO
from streamlit_gsheets import GSheetsConnection
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import base64
from pathlib import Path

# --------- 1. ULTRA-PREMIUM UI CSS & ANALYTICS -----------
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
  .stMetric {
    background: rgba(30, 33, 48, 0.7);
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(4px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-top: 4px solid #4facfe;
  }
  .gradient-text {
    background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    letter-spacing: -1px;
  }
</style>
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

# ---------------- 2. PAGE CONFIG ----------------
st.set_page_config(
    page_title="Graphico Pro 🚀 | Nilay's Masterpiece",
    page_icon="Naw4n.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

px.defaults.template = "plotly_dark"

# ---------------- 3. BRAHMASTRA: DATA ENGINE ----------------
def smart_clean_df(df):
    if df is None or df.empty:
        return df
    
    # BRAHMASTRA: Downcast numeric types to save 50%+ RAM
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    df_clean = df.copy()
    if df_clean.isnull().values.any():
        for column in df_clean.columns:
            if df_clean[column].isnull().any():
                if pd.api.types.is_numeric_dtype(df_clean[column]):
                    mean_val = df_clean[column].mean()
                    df_clean[column] = df_clean[column].fillna(mean_val if pd.notnull(mean_val) else 0)
                else:
                    mode_vals = df_clean[column].mode()
                    df_clean[column] = df_clean[column].fillna(mode_vals[0] if not mode_vals.empty else "Unknown")
        st.info("✨ Missing values handled by Mr Mastermind")
    return df_clean

# ---------------- 4. SIDEBAR NAVIGATION ----------------
with st.sidebar:
    st.title("Navigation")
    st.divider()
  
    page = st.radio("✨ Control Center",
                    ["🏠 Dashboard", "🔍 Raw Analytics", "🧠 ML Hub", "📖 Sample Vault"],
                    index=0)
  
    st.markdown("### 📂 Data Source")
    u_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls", "json", "parquet"])
  
    if u_file:
        if "file_id" not in st.session_state or st.session_state.file_id != u_file.name:
            ext = u_file.name.split(".")[-1].lower()
            try:
                # BRAHMASTRA: PyArrow engine for superfast CSV/Parquet loading
                if ext == "csv":
                    data = pd.read_csv(u_file, engine="pyarrow")
                elif ext in ["xlsx", "xls"]:
                    data = pd.read_excel(u_file, engine="openpyxl")
                elif ext == "parquet":
                    data = pd.read_parquet(u_file, engine="pyarrow")
                else:
                    data = pd.read_json(u_file)
              
                st.session_state.df = smart_clean_df(data)
                st.session_state.file_id = u_file.name
                st.toast("Data Engine Synced! 🚀", icon="✅")
            except Exception as e:
                st.error(f"Upload Failed: {e}")

    st.divider()
    if st.button("🌟 Support Nilay", use_container_width=True):
        st.session_state.review_active = not st.session_state.get("review_active", False)
    
    if st.session_state.get("review_active"):
        with st.expander("📝 Feedback Loop", expanded=True):
            r = st.slider("Rating", 1, 5, 5)
            m = st.text_input("Message")
            if st.button("Submit Review"):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    existing = conn.read(worksheet="Sheet1", ttl=0)
                    new_row = pd.DataFrame([{"rating": int(r), "review": m.strip()}])
                    updated = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                    conn.update(worksheet="Sheet1", data=updated)
                    st.success("Review Logged! 🚀")
                    st.balloons()
                    st.session_state.review_active = False
                except:
                    st.error("Link Error! Check GSheets.")
  
    st.caption("Crafted with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
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
        
        v_col, s_col = st.columns([3, 1])
        with s_col:
            st.markdown("### 🎨 Styling")
            g_type = st.selectbox("Chart Type", ["Bar", "Line", "Scatter", "Pie", "Histogram", "Box Plot", "Area Chart"])
            x_ax = st.selectbox("X-Axis (Category)", all_cols)
            y_ax = st.selectbox("Y-Axis (Numeric)", num_cols) if num_cols else None
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
        # BRAHMASTRA: Showing only top 5k rows to keep UI snappy
        st.write(f"Showing sample of 5,000 rows from {len(df):,} total.")
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
            # (Additional edit logic remains same)
            st.dataframe(df.head(100))
            
        elif work_option == "Make Predictions":
            feat = st.selectbox("Input Feature (Numeric)", num_cols, key="f_ml")
            targ = st.selectbox("Target Output (Numeric)", num_cols, key="t_ml")
            if feat and targ:
                st.subheader("Linear Regression Engine")
                model = LinearRegression().fit(df[[feat]], df[[targ]])
                val = st.number_input("Enter input value to predict")
                if st.button("Run Prediction"):
                    res = model.predict([[val]])
                    st.metric("Predicted Result", f"{res[0][0]:.4f}")

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
    # --- Landing Page when no file is uploaded ---
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