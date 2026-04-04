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

# --------- 1. SMART UI & MASTERMIND CSS -----------
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-FHN9KEP6KN');
</script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  
  .stMetric {
    background-color: #1e2130;
    padding: 18px;
    border-radius: 15px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    border-left: 5px solid #4facfe;
  }
  
  .gradient-text {
    background: -webkit-linear-gradient(#4facfe, #00f2fe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
  }

  .card-box {
    background: #1e2130;
    padding: 25px;
    border-radius: 20px;
    border: 1px solid #333;
    transition: 0.3s;
  }
  .card-box:hover { border-color: #4facfe; }
</style>
"""
components.html(ga_code, height=0)

# ---------------- 2. PAGE CONFIG ----------------
st.set_page_config(
  page_title="Graphico Pro 🚀 | Nilay's Masterpiece",
  page_icon="💎",
  layout="wide"
)
px.defaults.template = "plotly_dark"

# ---------------- 3. CORE LOGIC (ANTI-TABAHI) ----------------
def smart_clean_df(df):
    """Gracefully handles missing values for both Numeric and Text data"""
    temp_df = df.copy()
    for col in temp_df.columns:
        if temp_df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(temp_df[col]):
                temp_df[col] = temp_df[col].fillna(temp_df[col].mean())
            else:
                mode_res = temp_df[col].mode()
                fill_val = mode_res[0] if not mode_res.empty else "N/A"
                temp_df[col] = temp_df[col].fillna(fill_val)
    return temp_df

# ---------------- 4. SIDEBAR & FILE HANDLING ----------------
with st.sidebar:
    st.markdown("<h1 style='text-align: center;' class='gradient-text'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
    st.divider()
    
    page = st.radio("✨ Navigation Hub", ["🏠 Studio Home", "🔍 Insight Engine", "🧠 DS Mastermind", "📖 Learn & Samples"], index=0)
    
    st.subheader("📂 Project Data")
    uploaded_file = st.file_uploader("Drop your dataset here", type=["csv", "xlsx", "xls", "json"])
    
    if uploaded_file:
        # Loop Prevention: Only process if it's a new file
        if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
            ext = uploaded_file.name.split(".")[-1].lower()
            try:
                file_bytes = uploaded_file.getvalue()
                if ext == "csv": raw_df = pd.read_csv(io.BytesIO(file_bytes))
                elif ext in ["xlsx", "xls"]: raw_df = pd.read_excel(io.BytesIO(file_bytes))
                else: raw_df = pd.read_json(io.BytesIO(file_bytes))
                
                st.session_state.df = smart_clean_df(raw_df)
                st.session_state.last_uploaded_file = uploaded_file.name
                st.success("✅ Engine Synchronized!")
            except Exception as e:
                st.error(f"⚠️ Error loading file: {e}")

    # Review System
    st.divider()
    if st.button("🌟 Support Nilay", use_container_width=True):
        st.session_state.show_review = not st.session_state.get("show_review", False)

    if st.session_state.get("show_review"):
        with st.expander("📝 Quick Feedback", expanded=True):
            rating = st.selectbox("Rating", [5, 4, 3, 2, 1], key="user_rating")
            msg = st.text_area("How's the tool?", key="user_msg")
            if st.button("Submit Review"):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    existing = conn.read(worksheet="Sheet1", ttl=0)
                    new_row = pd.DataFrame([{"rating": int(rating), "review": msg.strip()}])
                    updated = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                    conn.update(worksheet="Sheet1", data=updated)
                    st.success("Legend! 🚀")
                    st.balloons()
                except: st.error("Link error!")
    
    st.caption("Crafted with ❤️ by Nilay")

# ---------------- 5. MAIN STUDIO LOGIC ----------------
if 'df' in st.session_state:
    df = st.session_state.df
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=np.number).columns.tolist()

    # --- PAGE 1: VISUALIZER ---
    if page == "🏠 Studio Home":
        st.markdown("<h1 class='gradient-text'>📊 Visualization Studio</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Rows", df.shape[0])
        c2.metric("📐 Columns", df.shape[1])
        c3.metric("🧹 Auto-Cleaned", int(df.isnull().sum().sum()))
        st.divider()

        st.sidebar.header("🎨 Canvas Controls")
        g_type = st.sidebar.selectbox("Chart Style", ["Bar", "Line", "Scatter", "Pie", "Histogram", "Heatmap"])
        x_ax = st.sidebar.selectbox("X-Axis", all_cols)
        y_ax = st.sidebar.selectbox("Y-Axis", num_cols) if num_cols else None
        
        st.subheader("🔍 Smart Filter")
        f_col = st.selectbox("Filter By", all_cols)
        u_vals = df[f_col].dropna().unique().tolist()
        s_vals = st.multiselect("Select Values", u_vals, default=u_vals[:3] if len(u_vals)>3 else u_vals)
        df_f = df[df[f_col].isin(s_vals)]
        
        try:
            fig = None
            if g_type == "Heatmap":
                fig = px.imshow(df_f.corr(numeric_only=True), text_auto=True)
            elif y_ax:
                if g_type == "Bar": fig = px.bar(df_f, x=x_ax, y=y_ax, color_discrete_sequence=['#4facfe'])
                elif g_type == "Line": fig = px.line(df_f, x=x_ax, y=y_ax)
                elif g_type == "Scatter": fig = px.scatter(df_f, x=x_ax, y=y_ax, color=x_ax)
                elif g_type == "Pie": fig = px.pie(df_f, names=x_ax, values=y_ax, hole=0.4)
                elif g_type == "Histogram": fig = px.histogram(df_f, x=y_ax)
            
            if fig: st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Please pick a numeric column for Y-Axis!")
        except Exception as e: st.error(f"Viz Error: {e}")

    # --- PAGE 2: INSIGHTS ---
    elif page == "🔍 Insight Engine":
        st.markdown("<h1 class='gradient-text'>🧠 Deep Insights</h1>", unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        colA, colB = st.columns(2)
        with colA: st.write("📊 Statistics", df.describe())
        with colB: st.write("🛠️ Data Types", pd.DataFrame(df.dtypes, columns=["Type"]).astype(str))

    # --- PAGE 3: DS HUB ---
    elif page == "🧠 DS Mastermind":
        st.markdown("<h1 class='gradient-text'>🧠 Mastermind Hub</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["✨ AI Predictions", "🛠️ Data Surgeon"])
        
        with t1:
            if len(num_cols) >= 2:
                X_p, y_p = st.selectbox("X", num_cols), st.selectbox("y", num_cols)
                val = st.number_input("Input Value")
                if st.button("Forecast"):
                    model = LinearRegression().fit(df[[X_p]].values, df[y_p].values)
                    res = model.predict([[val]])
                    st.metric("Prediction", f"{res[0]:.2f}")
            else: st.error("Need numeric data for AI!")

        with t2:
            op = st.selectbox("Action", ["Replace Value", "Remove Column"])
            if op == "Replace Value":
                c_r = st.selectbox("Column", all_cols)
                idx_r = st.number_input("Index", 0, len(df)-1)
                v_new = st.text_input("New Value")
                if st.button("Update"):
                    # Dynamic casting for new Pandas versions
                    current_val = df.at[idx_r, c_r]
                    df.at[idx_r, c_r] = type(current_val)(v_new) if not pd.isna(current_val) else v_new
                    st.session_state.df = df
                    st.success("Updated!")
                    st.rerun()

    # --- PAGE 4: SAMPLES ---
    elif page == "📖 Learn & Samples":
        st.title("Tutorials")
        if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")

# --- LANDING PAGE ---
else:
    st.markdown("""
    <div style='text-align: center; padding: 80px 0;'>
      <h1 style='font-size: 5.5em; margin-bottom: 0;' class='gradient-text'>💎 Graphico Pro</h1>
      <p style='font-size: 1.6em; color: #a1a1a1; margin-top: 0;'>The Professional Data Studio by Nilay</p>
      <br><br>
      <div style='display: flex; justify-content: center; gap: 30px;'>
        <div class='card-box' style='width: 320px;'><h3>📊 Visualize</h3><p>Messy data to beautiful charts.</p></div>
        <div class='card-box' style='width: 320px;'><h3>🧠 Predict</h3><p>Built-in AI forecasting.</p></div>
        <div class='card-box' style='width: 320px;'><h3>🛠️ Clean</h3><p>Smart auto-handling of data.</p></div>
      </div>
      <br><br>
      <h4 style='color: #4facfe;'>👈 Upload a dataset in the sidebar to start!</h4>
    </div>
    """, unsafe_allow_html=True)

# Sitemap
if st.query_params.get("sitemap") == "true":
    st.text("Sitemap Active")
    st.stop()
