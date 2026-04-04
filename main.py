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

# --------- 1. GOOGLE ANALYTICS & CUSTOM CSS -----------
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
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
  }
</style>
"""
components.html(ga_code, height=0)

# ---------------- 2. PAGE CONFIG ----------------
st.set_page_config(
  page_title="Graphico Pro 🚀 | AI-Powered Data Tool",
  page_icon="💎",
  layout="wide"
)
px.defaults.template = "plotly_dark"

# ---------------- 3. CORE FUNCTIONS ----------------
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

# ---------------- 4. SIDEBAR NAVIGATION ----------------
with st.sidebar:
  st.markdown("<h1 style='text-align: center; color: #4facfe;'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
  st.divider()
  
  page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights", "🧠 DS Hub", "📖 Samples"], index=0)
  
  uploaded_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx", "xls", "json"])
  
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    if 'df' not in st.session_state:
        raw_df = load_data(uploaded_file, ext)
        if raw_df is not None:
            st.session_state.df = fill_missing_values(raw_df)
    st.success("✅ Dataset Loaded!")

  # --------- ⭐ REVIEW SYSTEM ----------
  st.divider()
  if "show_review" not in st.session_state: st.session_state.show_review = False
  if st.button("⭐ Review Us", use_container_width=True):
      st.session_state.show_review = not st.session_state.show_review

  if st.session_state.show_review:
      with st.expander("📝 Feedback", expanded=True):
          rating = st.selectbox("Rate", [5, 4, 3, 2, 1], key="rev_rating")
          review_text = st.text_area("Message", key="rev_text")
          if st.button("Submit"):
              try:
                  conn = st.connection("gsheets", type=GSheetsConnection)
                  existing = conn.read(worksheet="Sheet1", ttl=0)
                  new_row = pd.DataFrame([{"rating": int(rating), "review": review_text.strip()}])
                  updated = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                  conn.update(worksheet="Sheet1", data=updated)
                  st.success("Legend! 🚀")
                  st.balloons()
              except: st.error("Link error!")
  
  st.info("Developed by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if 'df' in st.session_state:
  df = st.session_state.df
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include=np.number).columns.tolist()

  if page == "🏠 Home & Visualizer":
    st.markdown("<h2 style='color: #4facfe;'>📊 Professional Data Visualizer</h2>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("📈 Rows", df.shape[0])
    m2.metric("📋 Columns", df.shape[1])
    m3.metric("⚠️ Missing Cells", int(df.isnull().sum().sum()))
    st.divider()

    st.sidebar.header("🎨 Graph Settings")
    g_type = st.sidebar.selectbox("Chart Type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    x_ax = st.sidebar.selectbox("X-Axis", all_cols)
    y_ax = st.sidebar.selectbox("Y-Axis (Numeric)", num_cols) if num_cols else None
    
    st.subheader("🔍 Filter Data")
    f_col = st.selectbox("Filter Column", all_cols)
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect("Values", u_vals, default=u_vals[:3] if len(u_vals)>3 else u_vals)
    df_f = df[df[f_col].isin(s_vals)]
    
    try:
      fig = None
      if g_type == "Auto Suggestion": g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
      
      if g_type == "Heatmap":
          fig = px.imshow(df_f.corr(numeric_only=True), text_auto=True)
      elif y_ax:
          if g_type == "Bar": fig = px.bar(df_f, x=x_ax, y=y_ax)
          elif g_type == "Line": fig = px.line(df_f, x=x_ax, y=y_ax)
          elif g_type == "Scatter": fig = px.scatter(df_f, x=x_ax, y=y_ax)
          elif g_type == "Pie": fig = px.pie(df_f, names=x_ax, values=y_ax)
          elif g_type == "Histogram": fig = px.histogram(df_f, x=y_ax)
          elif g_type == "Box": fig = px.box(df_f, x=x_ax, y=y_ax)
          elif g_type == "Area": fig = px.area(df_f, x=x_ax, y=y_ax)
      
      if fig: st.plotly_chart(fig, use_container_width=True)
    except Exception as e: st.error(f"Viz Error: {e}")

  elif page == "🔍 Raw Insights":
    st.header("🧠 Data Insights")
    st.dataframe(df, use_container_width=True)
    st.write(df.describe())
    st.subheader("Missing Values")
    st.write(df.isnull().sum())

  elif page == "🧠 DS Hub":
    st.title("DS Mastermind's Hub 🧠💡")
    
    t1, t2 = st.tabs(["Pre-processing & AI", "DataFrame Editor"])
    
    with t1:
        st.subheader("1. Encoding")
        e_col = st.selectbox("Column", all_cols, key="e_c")
        e_m = st.selectbox("Method", ["Label Encoding", "One-Hot Encoding"], key="e_m")
        if st.button("Transform"):
            if df[e_col].dtype == 'object':
                if e_m == "Label Encoding":
                    le = LabelEncoder()
                    df[f"{e_col}_enc"] = le.fit_transform(df[e_col].astype(str))
                else:
                    df = pd.get_dummies(df, columns=[e_col])
                st.session_state.df = df
                st.rerun()
            else: st.info("Numeric already!")
        
        st.divider()
        st.subheader("2. AI Predictions")
        if len(num_cols) >= 2:
            X = st.selectbox("Feature (X)", num_cols, key="x_p")
            y = st.selectbox("Target (y)", num_cols, key="y_p")
            m_type = st.radio("Model", ["Linear", "Polynomial"])
            val = st.number_input("Input Value")
            if st.button("Predict"):
                if m_type == "Linear":
                    model = LinearRegression().fit(df[[X]], df[y])
                    res = model.predict([[val]])
                else:
                    model = make_pipeline(PolynomialFeatures(2), LinearRegression()).fit(df[[X]], df[y])
                    res = model.predict([[val]])
                st.metric("Result", f"{res[0]:.2f}")
        else: st.warning("Need numeric columns!")

    with t2:
        st.subheader("Edit Data")
        op = st.selectbox("Action", ["Replace Value", "Remove Row", "Remove Column"])
        
        if op == "Remove Column":
            c_del = st.selectbox("Column", df.columns, key="c_d")
            if st.button("Delete Column"):
                st.session_state.df = df.drop(columns=[c_del])
                st.rerun()
        
        elif op == "Remove Row":
            r_del = st.number_input("Index", 0, len(df)-1)
            if st.button("Delete Row"):
                st.session_state.df = df.drop(index=r_del)
                st.rerun()
        
        elif op == "Replace Value":
            c_r = st.selectbox("Column", df.columns, key="c_r")
            idx_r = st.number_input("Index", 0, len(df)-1, key="idx_r")
            
            # Smart Input Fix for TypeError
            if df[c_r].dtype == 'object':
                v_new = st.text_input("New Text")
            else:
                v_new = st.number_input("New Number", value=float(df.at[idx_r, c_r]))
            
            if st.button("Update"):
                try:
                    if df[c_r].dtype != 'object':
                        # Dynamic casting to original type
                        df.at[idx_r, c_r] = type(df[c_r].iloc[0])(v_new)
                    else:
                        df.at[idx_r, c_r] = str(v_new)
                    st.session_state.df = df
                    st.success("Updated!")
                    st.rerun()
                except: st.error("Type Mismatch!")

  elif page == "📖 Samples":
    st.title("Tutorial & Samples")
    st.video("Tutorial.mp4")
    if os.path.exists("tutorial_PNGs"):
        files = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
        for i in range(0, len(files), 4):
            cols = st.columns(4)
            for j, c in enumerate(cols):
                if i+j < len(files):
                    c.image(Image.open(os.path.join("tutorial_PNGs", files[i+j])), use_container_width=True)

else:
  st.title("💎 Graphico Pro")
  st.info("👈 Upload a dataset to unlock features!")

if st.query_params.get("sitemap") == "true":
    st.text("Sitemap Active")
    st.stop()
