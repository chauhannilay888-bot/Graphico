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

# --------- 1. SMART UI & ANALYTICS -----------
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

# ---------------- 3. ANTI-TABAHI FUNCTIONS ----------------
@st.cache_data
def load_data(uploaded_file, ext):
  try:
    file_bytes = uploaded_file.getvalue()
    if ext == "csv": return pd.read_csv(io.BytesIO(file_bytes))
    elif ext in ["xlsx", "xls"]: return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
    elif ext == "json": return pd.read_json(io.BytesIO(file_bytes))
  except Exception as e:
    st.error(f"⚠️ File Format Error: {e}")
    return None

def smart_clean_df(df):
    """Handles both numeric and non-numeric files without crashing"""
    for col in df.columns:
        if df[col].isnull().any():
            # Check if column is numeric (int/float)
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[column].fillna(df[column].mean())
            else:
                # Mode logic for objects/strings
                m = df[col].mode()
                fill_val = m[0] if not m.empty else "N/A"
                df[col] = df[col].fillna(fill_val)
    return df

# ---------------- 4. SIDEBAR & NAVIGATION ----------------
with st.sidebar:
  st.markdown("<h1 style='text-align: center;' class='gradient-text'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
  st.divider()
  
  page = st.radio("✨ Navigation Hub", ["🏠 Studio Home", "🔍 Insight Engine", "🧠 DS Mastermind", "📖 Learn & Samples"], index=0)
  
  st.subheader("📂 Project Data")
  uploaded_file = st.file_uploader("Drop your dataset here", type=["csv", "xlsx", "xls", "json"])
  
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    if 'df' not in st.session_state:
        raw_df = load_data(uploaded_file, ext)
        if raw_df is not None:
            st.session_state.df = smart_clean_df(raw_df)
            st.success("✅ Engine Synchronized!")

  # --------- ⭐ REVIEW SYSTEM ----------
  st.divider()
  if "show_review" not in st.session_state: st.session_state.show_review = False
  if st.button("🌟 Support Nilay", use_container_width=True):
      st.session_state.show_review = not st.session_state.show_review

  if st.session_state.show_review:
      with st.expander("📝 Quick Feedback", expanded=True):
          rating = st.selectbox("Rating", [5, 4, 3, 2, 1])
          msg = st.text_area("How's the new logic?", placeholder="Feedback here...")
          if st.button("Submit to Cloud"):
              try:
                  conn = st.connection("gsheets", type=GSheetsConnection)
                  existing = conn.read(worksheet="Sheet1", ttl=0)
                  new_row = pd.DataFrame([{"rating": int(rating), "review": msg.strip()}])
                  updated = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                  conn.update(worksheet="Sheet1", data=updated)
                  st.success("You are a Legend! 🚀")
                  st.balloons()
                  st.session_state.show_review = False
              except: st.error("Database Link Busy!")
  
  st.caption("Crafted with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC FLOW ----------------
if 'df' in st.session_state:
  df = st.session_state.df
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include=np.number).columns.tolist()

  # --- PAGE 1: VISUALIZER ---
  if page == "🏠 Studio Home":
    st.markdown("<h1 class='gradient-text'>📊 Professional Visualization Studio</h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Rows Detected", df.shape[0])
    c2.metric("📐 Total Columns", df.shape[1])
    c3.metric("🧹 Auto-Cleaned", int(df.isnull().sum().sum()))
    st.divider()

    st.sidebar.header("🎨 Canvas Controls")
    g_type = st.sidebar.selectbox("Chart Style", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    x_ax = st.sidebar.selectbox("X-Axis (Category)", all_cols)
    y_ax = st.sidebar.selectbox("Y-Axis (Value)", num_cols) if num_cols else None
    
    st.subheader("🔍 Contextual Filtering")
    f_col = st.selectbox("Filter Data By", all_cols)
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect("Select Focus Values", u_vals, default=u_vals[:3] if len(u_vals)>3 else u_vals)
    df_f = df[df[f_col].isin(s_vals)]
    
    try:
      fig = None
      if g_type == "Auto Suggestion": g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
      
      if g_type == "Heatmap":
          fig = px.imshow(df_f.corr(numeric_only=True), text_auto=True, color_continuous_scale='Viridis')
      elif y_ax:
          color_seq = ['#4facfe', '#00f2fe', '#a1c4fd']
          if g_type == "Bar": fig = px.bar(df_f, x=x_ax, y=y_ax, color_discrete_sequence=color_seq)
          elif g_type == "Line": fig = px.line(df_f, x=x_ax, y=y_ax, markers=True)
          elif g_type == "Scatter": fig = px.scatter(df_f, x=x_ax, y=y_ax, size=y_ax, color=x_ax)
          elif g_type == "Pie": fig = px.pie(df_f, names=x_ax, values=y_ax, hole=0.5)
          elif g_type == "Histogram": fig = px.histogram(df_f, x=y_ax)
          elif g_type == "Box": fig = px.box(df_f, x=x_ax, y=y_ax)
          elif g_type == "Area": fig = px.area(df_f, x=x_ax, y=y_ax)
      
      if fig: 
          fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
          st.plotly_chart(fig, use_container_width=True)
      else: st.warning("⚠️ Need a Numeric Column for Y-Axis to visualize correctly!")
    except Exception as e: st.error(f"Studio Error: {e}")

  # --- PAGE 2: INSIGHTS ---
  elif page == "🔍 Insight Engine":
    st.markdown("<h1 class='gradient-text'>🧠 Advanced Metadata & Insights</h1>", unsafe_allow_html=True)
    st.subheader("Dataset Deep-Dive")
    st.dataframe(df, use_container_width=True)
    
    colA, colB = st.columns(2)
    with colA:
      st.subheader("📊 Statistics Overview")
      st.write(df.describe())
    with colB:
      st.subheader("🛠️ Data Architecture")
      st.table(pd.DataFrame(df.dtypes, columns=["DataType"]).astype(str))

  # --- PAGE 3: DS HUB (CRITICAL FIXES) ---
  elif page == "🧠 DS Mastermind":
    st.markdown("<h1 class='gradient-text'>🧠 Mastermind Machine Learning Hub</h1>", unsafe_allow_html=True)
    
    tab_ai, tab_edit = st.tabs(["✨ AI Predictions", "🛠️ Data Surgeon"])
    
    with tab_ai:
        st.subheader("1. Categorical Encoding")
        e_col = st.selectbox("Pick Target Column", all_cols, key="e_col")
        e_m = st.selectbox("Method", ["Label Encoding", "One-Hot Encoding"])
        if st.button("Run Transformation"):
            if df[e_col].dtype == 'object':
                if e_m == "Label Encoding":
                    le = LabelEncoder()
                    df[f"{e_col}_enc"] = le.fit_transform(df[e_col].astype(str))
                else:
                    df = pd.get_dummies(df, columns=[e_col])
                st.session_state.df = df
                st.success("Data Transformed! 🚀")
                st.rerun()
            else: st.info("Already Numeric, Boss!")
        
        st.divider()
        st.subheader("2. AI Models")
        if len(num_cols) >= 2:
            X, y = st.selectbox("X Feature", num_cols, key="X"), st.selectbox("y Target", num_cols, key="y")
            m_choice = st.radio("Logic:", ["Linear", "Polynomial (Smart)"])
            val = st.number_input(f"Predict {y} for {X}:")
            
            if st.button("Execute Forecast"):
                model = LinearRegression() if m_choice == "Linear" else make_pipeline(PolynomialFeatures(2), LinearRegression())
                model.fit(df[[X]].values, df[y].values)
                res = model.predict([[val]])
                st.metric("Forecasted Result", f"{res[0]:.4f}")
        else: st.error("Need numeric columns! Encode your data first.")

    with tab_edit:
        st.subheader("DataFrame Surgeon")
        op = st.selectbox("Action", ["Replace Value", "Remove Row", "Remove Column"])
        
        if op == "Remove Column":
            c_rm = st.selectbox("Column", df.columns, key="crm")
            if st.button("Delete Column"):
                st.session_state.df = df.drop(columns=[c_rm])
                st.rerun()
        
        elif op == "Replace Value":
            c_rp = st.selectbox("Select Column", df.columns, key="crp")
            idx_rp = st.number_input("Index", 0, len(df)-1)
            
            # User Friendly Input Handling
            if pd.api.types.is_numeric_dtype(df[c_rp]):
                v_in = st.number_input("New Number", value=float(df.at[idx_rp, c_rp]))
            else:
                v_in = st.text_input("New Text", value=str(df.at[idx_rp, c_rp]))
            
            if st.button("Update Database"):
                try:
                    # New Pandas Version friendly replacement
                    # Cast value to match column type
                    if pd.api.types.is_numeric_dtype(df[c_rp]):
                        df.at[idx_rp, c_rp] = type(df[c_rp].iloc[0])(v_in)
                    else:
                        df.at[idx_rp, c_rp] = str(v_in)
                    
                    st.session_state.df = df
                    st.success("Synchronized successfully!")
                    st.rerun()
                except: st.error("DType Mismatch! Enter correct value.")

  # --- PAGE 4: SAMPLES ---
  elif page == "📖 Learn & Samples":
    st.markdown("<h1 class='gradient-text'>📖 Learning Resources</h1>", unsafe_allow_html=True)
    if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
    
    st.subheader("Studio Snapshot Gallery")
    if os.path.exists("tutorial_PNGs"):
        f_list = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
        for i in range(0, len(f_list), 4):
            cols = st.columns(4)
            for j, c in enumerate(cols):
                if i+j < len(f_list):
                    c.image(Image.open(os.path.join("tutorial_PNGs", f_list[i+j])), use_container_width=True)

# --- LANDING PAGE (UI MASTERPIECE) ---
else:
  st.markdown("""
    <div style='text-align: center; padding: 60px 0;'>
      <h1 style='font-size: 5.5em; margin-bottom: 0;' class='gradient-text'>💎 Graphico Pro</h1>
      <p style='font-size: 1.6em; color: #a1a1a1; margin-top: 0;'>The Professional Data Studio by Nilay</p>
      <br><br>
      <div style='display: flex; justify-content: center; gap: 30px;'>
        <div class='card-box' style='width: 320px;'>
            <h2 style='color: #4facfe;'>📊 Visualize</h2>
            <p style='color: #ccc;'>Convert complex CSV/Excel files into interactive visual stories instantly.</p>
        </div>
        <div class='card-box' style='width: 320px;'>
            <h2 style='color: #00f2fe;'>🧠 Predict</h2>
            <p style='color: #ccc;'>Built-in AI models to forecast trends using Machine Learning logic.</p>
        </div>
        <div class='card-box' style='width: 320px;'>
            <h2 style='color: #a1c4fd;'>🛠️ Clean</h2>
            <p style='color: #ccc;'>Auto-handles missing values and lets you edit data like a surgeon.</p>
        </div>
      </div>
      <br><br><br>
      <div style='background: #1e2130; padding: 20px; border-radius: 50px; display: inline-block; border: 1px dashed #4facfe;'>
        <h4 style='margin:0; color: #4facfe;'>👈 Drag your Data in the Sidebar to Launch Engine</h4>
      </div>
    </div>
  """, unsafe_allow_html=True)

# Sitemap XML
if st.query_params.get("sitemap") == "true":
    st.text("Sitemap 2026: Graphico Pro Active")
    st.stop()
