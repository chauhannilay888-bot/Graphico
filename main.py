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
    if df is None or df.empty:
        return df
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
    st.markdown("<h1 style='text-align: center; font-size: 2.2em;' class='gradient-text'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("✨ Control Center", 
                    ["🏠 Dashboard", "🔍 Raw Analytics", "🧠 ML Hub", "📖 Sample Vault"], 
                    index=0)
    
    st.markdown("### 📂 Data Source")
    u_file = st.file_uploader("Upload CSV, Excel or JSON", 
                              type=["csv", "xlsx", "xls", "json"])
    
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
                except: 
                    st.error("Link Error! Check GSheets Connection.")
    
    st.caption("Crafted with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if 'df' in st.session_state and st.session_state.df is not None and not st.session_state.df.empty:
    df = st.session_state.df
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=np.number).columns.tolist()

    if 'action_count' not in st.session_state:
        st.session_state.action_count = 0
    st.session_state.action_count += 1
    if st.session_state.action_count % 5 == 0:
        st.toast("💡 Loving Graphico? Leave a review in the sidebar!", icon="⭐")

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
            except Exception as e: 
                st.error(f"Viz Error: {e}")

    elif page == "🔍 Raw Analytics":
        st.markdown("<h1 class='gradient-text'>🔍 Insight Engine</h1>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.write("#### 📊 Descriptive Stats", df.describe())

    elif page == "🧠 ML Hub":
        st.title("Welcome to DS Hub!")
        
        # Encoding Section
        st.subheader("🛠️ Data Pre-processing")
        le = LabelEncoder()
        encoding_type = st.selectbox("Select Encoding Type", 
                                     ("Label Encoding (for 2 categories)", "One-Hot Encoding (for 2 or more categories)"))
        t_colm = st.selectbox("Select column to encode", df.columns)
        
        if st.button("Apply Encoding ⚡"):
            df_copy = df.copy()
            if "Label Encoding" in encoding_type:
                encd_name = str(t_colm) + "_encoded"
                df_copy[encd_name] = le.fit_transform(df_copy[t_colm].astype(str))
                st.success(f"Encoded '{t_colm}' into '{encd_name}'")
            else:
                df_copy = pd.get_dummies(df_copy, columns=[t_colm])
                st.success(f"One-Hot Encoding complete for '{t_colm}'")
            
            st.session_state.df = df_copy
            st.rerun()

        st.divider()

        work_option = st.radio("What's next?", ("Edit DataFrame", "Make Predictions"))

        if work_option == "Edit DataFrame":
            op = st.selectbox("Action", ("Remove Column", "Remove Row", "Update Value"))
            if op == "Remove Column":
                c_rem = st.selectbox("Select column", df.columns)
                if st.button("Delete Column"):
                    st.session_state.df = df.drop(columns=[c_rem])
                    st.rerun()
            elif op == "Remove Row":
                r_rem = st.number_input("Row index", 0, len(df)-1)
                if st.button("Delete Row"):
                    st.session_state.df = df.drop(index=r_rem).reset_index(drop=True)
                    st.rerun()
            elif op == "Update Value":
                c_edit = st.selectbox("Column", df.columns)
                r_edit = st.number_input("Index", 0, len(df)-1)
                n_val = st.text_input("New Value")
                if st.button("Update"):
                    df.at[r_edit, c_edit] = n_val
                    st.session_state.df = df
                    st.rerun()

        elif work_option == "Make Predictions":
            st.subheader("Model Training")
            feat = st.selectbox("Input Feature (X)", num_cols)
            targ = st.selectbox("Target Label (y)", num_cols)
            
            try:
                m_type = st.radio("Model", ("Linear Regression", "Polynomial Regression"))
                if m_type == "Linear Regression":
                    model = LinearRegression().fit(df[[feat]], df[targ])
                else:
                    deg = st.slider("Polynomial Degree", 1, 5, 2)
                    model = make_pipeline(PolynomialFeatures(deg), LinearRegression()).fit(df[[feat]], df[targ])
                
                st.success("Model Trained!")
                val = st.number_input("Predict for value:", step=1.0)
                if st.button("Predict"):
                    p = model.predict([[val]])
                    st.metric("Forecasted Result", f"{p[0]:.2f}")
                    st.balloons()
            except Exception as e:
                st.error(f"Prediction Error: {e}")

    elif page == "📖 Sample Vault":
        st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
        if os.path.exists("Tutorial.mp4"):
            st.video("Tutorial.mp4")

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
