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

# --------- 1. ULTRA-PREMIUM UI CSS -----------
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

  .card-box {
    background: #1e2130;
    padding: 25px;
    border-radius: 20px;
    border: 1px solid #333;
    transition: all 0.4s ease;
  }
  .card-box:hover {
    transform: translateY(-5px);
    border-color: #4facfe;
    box-shadow: 0 10px 20px rgba(79, 172, 254, 0.2);
  }
</style>
"""
components.html(ga_code, height=0)

# ---------------- 2. PAGE CONFIG ----------------
st.set_page_config(
  page_title="Graphico Pro 🚀 | Nilay's Masterpiece",
  page_icon="💎",
  layout="wide",
  initial_sidebar_state="expanded"
)
px.defaults.template = "plotly_dark"

# ---------------- 3. ANTI-TABAHI CLEANING LOGIC ----------------
def smart_clean_df(df):
    """Handles missing values without crashing, regardless of data type"""
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].isnull().any():
            if pd.api.types.is_numeric_dtype(df_clean[col]):
                mean_val = df_clean[col].mean()
                df_clean[col] = df_clean[col].fillna(mean_val if pd.notnull(mean_val) else 0)
            else:
                mode_vals = df_clean[col].mode()
                df_clean[col] = df_clean[col].fillna(mode_vals[0] if not mode_vals.empty else "Unknown")
    return df_clean

# ---------------- 4. SIDEBAR NAVIGATION ----------------
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-size: 2.2em;' class='gradient-text'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("✨ Control Center", ["🏠 Dashboard", "🔍 Raw Analytics", "🧠 ML Hub", "📖 Sample Vault"], index=0)
    
    st.markdown("### 📂 Data Source")
    u_file = st.file_uploader("Upload CSV, Excel or JSON", type=["csv", "xlsx", "xls", "json"])
    
    if u_file:
        if "file_id" not in st.session_state or st.session_state.file_id != u_file.name:
            ext = u_file.name.split(".")[-1].lower()
            try:
                if ext == "csv": data = pd.read_csv(u_file)
                elif ext in ["xlsx", "xls"]: data = pd.read_excel(u_file)
                else: data = pd.read_json(u_file)
                
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
                except: st.error("Link Error! Check GSheets Connection.")
    
    st.caption("Crafted with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if 'df' in st.session_state:
    df = st.session_state.df
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=np.number).columns.tolist()

    if page == "🏠 Dashboard":
        st.markdown("<h1 class='gradient-text'>📊 Visualization Dashboard</h1>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 Total Rows", df.shape[0])
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
                fig = None
                if y_ax:
                    args = {"data_frame": df, "x": x_ax, "y": y_ax, "color": color_by, "template": "plotly_dark"}
                    if g_type == "Bar": fig = px.bar(**args)
                    elif g_type == "Line": fig = px.line(**args)
                    elif g_type == "Scatter": fig = px.scatter(**args, size_max=15)
                    elif g_type == "Pie": fig = px.pie(df, names=x_ax, values=y_ax)
                    elif g_type == "Histogram": fig = px.histogram(df, x=y_ax, color=color_by)
                    elif g_type == "Box Plot": fig = px.box(**args)
                    elif g_type == "Area Chart": fig = px.area(**args)
                
                if fig:
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ Select a Numeric Column for Y-Axis.")
            except Exception as e: st.error(f"Viz Error: {e}")

    elif page == "🔍 Raw Analytics":
        st.markdown("<h1 class='gradient-text'>🔍 Insight Engine</h1>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.write("#### 📊 Descriptive Stats", df.describe())

    elif page == "🧠 ML Hub":
        st.markdown("<h1 class='gradient-text'>🧠 ML & Data Surgeon Hub</h1>", unsafe_allow_html=True)
        t_ai, t_surgeon = st.tabs(["✨ AI Predictions", "🛠️ Data Surgeon"])
        
        with t_ai:
            if len(num_cols) >= 2:
                c_x, c_y = st.columns(2)
                X_f = c_x.selectbox("Feature (X)", num_cols)
                y_f = c_y.selectbox("Target (y)", num_cols)
                in_val = st.number_input(f"Enter {X_f}:", value=0.0)
                if st.button("🚀 Forecast Now"):
                    model = LinearRegression().fit(df[[X_f]].values, df[y_f].values)
                    pred = model.predict([[in_val]])
                    st.metric(f"Predicted {y_f}", f"{pred[0]:.4f}")
                    st.balloons()
            else: st.error("Need more numeric data for AI!")

        with t_surgeon:
            st.subheader("Live Database Modification")
            action = st.selectbox("Select Surgery Type", ["Update Value", "Drop Column", "Drop Row"])
            
            if action == "Update Value":
                col_s = st.selectbox("Column", all_cols)
                idx_s = st.number_input("Index", 0, len(df)-1)
                curr_val = df.at[idx_s, col_s]
                
                if pd.api.types.is_numeric_dtype(df[col_s]):
                    new_v = st.number_input("New Value", value=float(curr_val))
                else:
                    new_v = st.text_input("New Value", value=str(curr_val))
                
                if st.button("Apply Transformation"):
                    try:
                        df.at[idx_s, col_s] = type(df[col_s].iloc[0])(new_v)
                        st.session_state.df = df
                        st.success("Synchronized!")
                        st.rerun()
                    except: st.info("No need to worry about!")

            elif action == "Drop Column":
                target_col = st.selectbox("Remove Column", all_cols)
                if st.button("🔥 Confirm Deletion"):
                    st.session_state.df = df.drop(columns=[target_col])
                    st.toast(f"Column '{target_col}' removed!")
                    st.rerun()

            elif action == "Drop Row":
                target_row = st.number_input("Remove Index", 0, len(df)-1)
                if st.button("🗑️ Confirm Removal"):
                    st.session_state.df = df.drop(index=target_row).reset_index(drop=True)
                    st.toast(f"Row {target_row} deleted!")
                    st.rerun()

    elif page == "📖 Sample Vault":
        st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
        if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
        import streamlit as st, os
        files=[f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
        for i in range(0,len(files),4):
          cols=st.columns(4)
          for j,c in enumerate(cols):
            if i+j<len(files): c.image(Image.open(os.path.join("tutorial_PNGs",files[i+j])),use_column_width=True)
     
elif page == "📖 Sample Vault":
        st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
        if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
        files=[f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
        for i in range(0,len(files),4):
          cols=st.columns(4)
          for j,c in enumerate(cols):
            if i+j<len(files): c.image(Image.open(os.path.join("tutorial_PNGs",files[i+j])),use_column_width=True)

else:
    st.markdown("""
    <div style='text-align: center; padding: 100px 0;'>
      <h1 style='font-size: 6em; margin-bottom: 0;' class='gradient-text'>💎 Graphico Pro</h1>
      <p style='font-size: 1.8em; color: #a1a1a1; margin-top: 0;'>The Professional Data Studio by Nilay</p>
      <br><br>
      <div style='display: flex; justify-content: center; gap: 30px;'>
        <div class='card-box' style='width: 300px;'><h3>⚡ Fast</h3><p>Instant visualization for any file.</p></div>
        <div class='card-box' style='width: 300px;'><h3>🧠 Smart</h3><p>Built-in AI forecasting logic.</p></div>
        <div class='card-box' style='width: 300px;'><h3>🛠️ Reliable</h3><p>Full-scale data surgery tools.</p></div>
      </div>
      <br><br>
      <h4 style='color: #4facfe;'>👈 Upload your Dataset in the Sidebar to Launch Engine</h4>
    </div>
    """, unsafe_allow_html=True)

if st.query_params.get("sitemap") == "true":
    st.text("Engine Status: 100% Operational")
    st.stop()
