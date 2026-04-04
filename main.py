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

# --------- 1. GOOGLE ANALYTICS & MASTERMIND CSS -----------
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
  
  /* Metric Card Styling */
  .stMetric {
    background-color: #1e2130;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    border: 1px solid #4facfe;
  }
  
  /* Gradient Text for Headers */
  .gradient-text {
    background: -webkit-linear-gradient(#4facfe, #00f2fe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: bold;
  }

  /* Sidebar Profile Styling */
  .sidebar-profile {
    text-align: center;
    padding: 10px;
    background: #1e2130;
    border-radius: 15px;
    margin-bottom: 20px;
  }
</style>
"""
components.html(ga_code, height=0)

# ---------------- 2. PAGE CONFIG ----------------
st.set_page_config(
  page_title="Graphico Pro 🚀 | Nilay's AI Studio",
  page_icon="💎",
  layout="wide"
)
px.defaults.template = "plotly_dark"

# ---------------- 3. CORE LOGIC FUNCTIONS ----------------
@st.cache_data
def load_data(uploaded_file, ext):
  try:
    file_bytes = uploaded_file.getvalue()
    if ext == "csv": return pd.read_csv(io.BytesIO(file_bytes))
    elif ext in ["xlsx", "xls"]: return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
    elif ext == "json": return pd.read_json(io.BytesIO(file_bytes))
  except Exception as e:
    st.error(f"❌ File Load Error: {e}")
    return None

def fill_missing_values(df):
    for column in df.columns:
        if df[column].dtype == 'object':
            df[column] = df[column].fillna(df[column].mode()[0])
        else:
            df[column] = df[column].fillna(df[column].mean())
    return df

# ---------------- 4. SIDEBAR (NILAY'S SPECIAL) ----------------
with st.sidebar:
  st.markdown("""
    <div class='sidebar-profile'>
        <h1 style='color: #4facfe; margin-bottom:0;'>💎 GRAPHICO</h1>
        <p style='color: #00f2fe; font-size: 0.9em;'>Mastermind Edition</p>
    </div>
  """, unsafe_allow_html=True)
  
  page = st.radio("🚀 Navigate Studio", ["🏠 Home & Visualizer", "🔍 Raw Insights", "🧠 DS Hub", "📖 Samples"], index=0)
  
  st.divider()
  uploaded_file = st.file_uploader("📂 Upload Dataset", type=["csv", "xlsx", "xls", "json"])
  
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    if 'df' not in st.session_state:
        raw_df = load_data(uploaded_file, ext)
        if raw_df is not None:
            st.session_state.df = fill_missing_values(raw_df)
    st.success("✅ Engine Ready!")

  # --------- ⭐ REVIEW SYSTEM ----------
  st.divider()
  if "show_review" not in st.session_state: st.session_state.show_review = False
  if st.button("🌟 Support the Creator", use_container_width=True):
      st.session_state.show_review = not st.session_state.show_review

  if st.session_state.show_review:
      with st.expander("📝 Quick Feedback", expanded=True):
          rating = st.selectbox("Rating", [5, 4, 3, 2, 1], key="rev_rating")
          review_text = st.text_area("How's the UI, Nilay?", key="rev_text")
          if st.button("Submit to GSheets"):
              try:
                  conn = st.connection("gsheets", type=GSheetsConnection)
                  existing = conn.read(worksheet="Sheet1", ttl=0)
                  new_row = pd.DataFrame([{"rating": int(rating), "review": review_text.strip()}])
                  updated = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                  conn.update(worksheet="Sheet1", data=updated)
                  st.success("You're a Legend! 🚀")
                  st.balloons()
              except: st.error("Connection Error!")
  
  st.markdown("<p style='text-align: center; color: grey;'>Made with ❤️ by Nilay</p>", unsafe_allow_html=True)

# ---------------- 5. MAIN STUDIO LOGIC ----------------
if 'df' in st.session_state:
  df = st.session_state.df
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include=np.number).columns.tolist()

  # --- PAGE 1: VISUALIZER ---
  if page == "🏠 Home & Visualizer":
    st.markdown("<h1 class='gradient-text'>📊 Data Visualization Studio</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Data Points", df.shape[0])
    col2.metric("📐 Features", df.shape[1])
    col3.metric("🧹 Auto-Cleaned", int(df.isnull().sum().sum()))
    
    st.divider()

    # Chart Controls
    st.sidebar.header("🎨 Canvas Settings")
    g_type = st.sidebar.selectbox("Chart Type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    x_ax = st.sidebar.selectbox("X-Axis (Horizontal)", all_cols)
    y_ax = st.sidebar.selectbox("Y-Axis (Vertical)", num_cols) if num_cols else None
    
    st.subheader("🔍 Smart Filters")
    f_col = st.selectbox("Filter Data By", all_cols)
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect("Select Values", u_vals, default=u_vals[:3] if len(u_vals)>3 else u_vals)
    df_f = df[df[f_col].isin(s_vals)]
    
    try:
      fig = None
      if g_type == "Auto Suggestion": g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
      
      if g_type == "Heatmap":
          fig = px.imshow(df_f.corr(numeric_only=True), text_auto=True, color_continuous_scale='RdBu_r')
      elif y_ax:
          if g_type == "Bar": fig = px.bar(df_f, x=x_ax, y=y_ax, color_discrete_sequence=['#4facfe'])
          elif g_type == "Line": fig = px.line(df_f, x=x_ax, y=y_ax, markers=True)
          elif g_type == "Scatter": fig = px.scatter(df_f, x=x_ax, y=y_ax, size=y_ax, color=x_ax, hover_data=all_cols)
          elif g_type == "Pie": fig = px.pie(df_f, names=x_ax, values=y_ax, hole=0.4)
          elif g_type == "Histogram": fig = px.histogram(df_f, x=y_ax, marginal="rug")
          elif g_type == "Box": fig = px.box(df_f, x=x_ax, y=y_ax, points="all")
          elif g_type == "Area": fig = px.area(df_f, x=x_ax, y=y_ax)
      
      if fig: 
          fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
          st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.error(f"Canvas Error: {e}")

  # --- PAGE 2: RAW INSIGHTS ---
  elif page == "🔍 Raw Insights":
    st.markdown("<h1 class='gradient-text'>🧠 Deep Insights & Metadata</h1>", unsafe_allow_html=True)
    
    with st.container():
        st.subheader("Data Explorer")
        st.dataframe(df.style.highlight_max(axis=0), use_container_width=True)
    
    c1, c2 = st.columns(2)
    with c1:
      st.subheader("📊 Statistical Summary")
      st.write(df.describe())
    with c2:
      st.subheader("🛠️ DataType Audit")
      dtype_df = pd.DataFrame(df.dtypes, columns=["Type"]).astype(str)
      st.table(dtype_df)

  # --- PAGE 3: DS HUB ---
  elif page == "🧠 DS Hub":
    st.markdown("<h1 class='gradient-text'>🧠 DS Mastermind's Hub</h1>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["✨ Pre-processing & AI", "🛠️ DataFrame Editor"])
    
    with t1:
        st.subheader("1. Categorical Encoding")
        e_col = st.selectbox("Select Column to Transform", all_cols, key="e_c")
        e_m = st.selectbox("Transformation Method", ["Label Encoding", "One-Hot Encoding"], key="e_m")
        if st.button("Execute Transformation"):
            if df[e_col].dtype == 'object':
                if e_m == "Label Encoding":
                    le = LabelEncoder()
                    df[f"{e_col}_enc"] = le.fit_transform(df[e_col].astype(str))
                else:
                    df = pd.get_dummies(df, columns=[e_col])
                st.session_state.df = df
                st.success(f"Successfully encoded {e_col}!")
                st.rerun()
            else: st.info("This column is already numeric, Mastermind!")
        
        st.divider()
        st.subheader("2. AI Prediction Suite")
        if len(num_cols) >= 2:
            X = st.selectbox("Input Feature (X)", num_cols, key="x_p")
            y = st.selectbox("Target to Predict (y)", num_cols, key="y_p")
            m_type = st.radio("Select Brain Complexity:", ["Linear Regression", "Polynomial (Smart)"])
            val = st.number_input(f"Enter {X} to get predicted {y}")
            
            if st.button("Start Prediction"):
                if m_type == "Linear Regression":
                    model = LinearRegression().fit(df[[X]], df[y])
                    res = model.predict([[val]])
                else:
                    model = make_pipeline(PolynomialFeatures(2), LinearRegression()).fit(df[[X]], df[y])
                    res = model.predict([[val]])
                st.metric(f"Predicted {y}", f"{res[0]:.4f}")
                st.balloons()
        else: st.warning("Please encode your categorical data or upload a numeric dataset.")

    with t2:
        st.subheader("Direct Data Manipulation")
        op = st.selectbox("Select Operation", ["Replace Value", "Remove Row", "Remove Column"])
        
        if op == "Remove Column":
            c_del = st.selectbox("Select Column", df.columns, key="c_d")
            if st.button("Delete Forever"):
                st.session_state.df = df.drop(columns=[c_del])
                st.rerun()
        
        elif op == "Remove Row":
            r_del = st.number_input("Enter Row Index", 0, len(df)-1)
            if st.button("Drop Row"):
                st.session_state.df = df.drop(index=r_del)
                st.rerun()
        
        elif op == "Replace Value":
            c_r = st.selectbox("Target Column", df.columns, key="c_r")
            idx_r = st.number_input("Target Index", 0, len(df)-1, key="idx_r")
            
            # Smart Dynamic Input
            if df[c_r].dtype == 'object':
                v_new = st.text_input("New Value (Text)")
            else:
                v_new = st.number_input("New Value (Numeric)", value=float(df.at[idx_r, c_r]))
            
            if st.button("Confirm Update"):
                try:
                    # Using Old & Gold logic since requirements.txt is fixed
                    df.at[idx_r, c_r] = v_new
                    st.session_state.df = df
                    st.success("Value replaced in Mastermind database!")
                    st.rerun()
                except: st.info("No need to worry about")

  # --- PAGE 4: SAMPLES ---
  elif page == "📖 Samples":
    st.markdown("<h1 class='gradient-text'>📖 Learning & Samples</h1>", unsafe_allow_html=True)
    if os.path.exists("Tutorial.mp4"): 
        st.video("Tutorial.mp4")
    
    st.subheader("UI Gallery")
    if os.path.exists("tutorial_PNGs"):
        files = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
        for i in range(0, len(files), 4):
            cols = st.columns(4)
            for j, c in enumerate(cols):
                if i+j < len(files):
                    c.image(Image.open(os.path.join("tutorial_PNGs", files[i+j])), use_container_width=True)
    else: st.info("Gallery assets are being updated by the team.")

# --- LANDING PAGE (UI SPECIAL) ---
else:
  st.markdown("""
    <div style='text-align: center; padding: 50px 0;'>
      <h1 style='font-size: 5em; margin-bottom: 0;' class='gradient-text'>💎 Graphico Pro</h1>
      <p style='font-size: 1.5em; color: #a1a1a1; margin-top: 0;'>The Professional Data Visualizer & AI Hub</p>
      <br><br>
      <div style='display: flex; justify-content: center; gap: 20px;'>
        <div style='background: #1e2130; padding: 30px; border-radius: 20px; border-bottom: 5px solid #4facfe; width: 300px;'>
            <h3>📊 Visualizer</h3>
            <p>Convert messy data into beautiful Plotly charts instantly.</p>
        </div>
        <div style='background: #1e2130; padding: 30px; border-radius: 20px; border-bottom: 5px solid #00f2fe; width: 300px;'>
            <h3>🧠 AI Prediction</h3>
            <p>Train Linear & Polynomial models with just one click.</p>
        </div>
        <div style='background: #1e2130; padding: 30px; border-radius: 20px; border-bottom: 5px solid #a1c4fd; width: 300px;'>
            <h3>🛠️ Data Editor</h3>
            <p>Clean, edit, and modify your datasets on the fly.</p>
        </div>
      </div>
      <br><br>
      <h3 style='color: #4facfe;'>👈 Please upload a file in the sidebar to begin.</h3>
    </div>
  """, unsafe_allow_html=True)

# Sitemap Generator
if st.query_params.get("sitemap") == "true":
    st.text("Sitemap Active")
    st.stop()
