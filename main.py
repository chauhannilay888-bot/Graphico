import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import plotly.express as px
import os
from PIL import Image
import json
import time
from streamlit_gsheets import GSheetsConnection
from streamlit_star_rating import st_star_rating   # ← Yeh line add ki hai

# --------- 1. GOOGLE ANALYTICS & CUSTOM CSS -----------
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-FHN9KEP6KN');
</script>
<meta name="google-site-verification" content="zINnwjOarj-lAgHmEFrOPaihJvA5iwrmzhapCKGuqj0" />
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }
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

# ---------------- 3. DATA LOADING FUNCTION ----------------
@st.cache_data
def load_data(uploaded_file, ext):
  try:
    file_bytes = uploaded_file.getvalue()
    if ext == "csv":
      return pd.read_csv(io.BytesIO(file_bytes))
    elif ext in ["xlsx", "xls"]:
      return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
    elif ext == "json":
      return pd.read_json(io.BytesIO(file_bytes))
  except Exception as e:
    st.error(f"❌ File Load Error: {e}")
    return None

# ---------------- 4. SIDEBAR NAVIGATION ----------------
with st.sidebar:
  st.markdown("<h1 style='text-align: center; color: #4facfe;'>💎 GRAPHICO PRO</h1>", unsafe_allow_html=True)
  st.markdown("<p style='text-align: center; font-size: 0.8em;'>Empowering Your Data Journey</p>", unsafe_allow_html=True)
  st.divider()
  
  page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights", "📖 Samples"], index=0)
 
  uploaded_file = st.file_uploader("Upload Dataset (CSV, Excel, JSON)", type=["csv", "xlsx", "xls", "json"])
 
  df = None
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    df = load_data(uploaded_file, ext)
    if df is not None:
      st.success("✅ Dataset Loaded!")

  # ==================== BEAUTIFUL REVIEW SYSTEM ====================
  if st.button("⭐ Review Us", use_container_width=True, type="secondary"):
      st.session_state.show_review = True

  if st.session_state.get("show_review", False):
      with st.form("review_form"):
          st.markdown("### 📝 How was your experience with Graphico Pro?")
          
          # Beautiful Star Rating
          rating = st_star_rating(
              label="Give us stars",
              maxValue=5,
              defaultValue=5,
              size=45,
              read_only=False,
              customCSS="""
                  .stStarRating { 
                      justify-content: center; 
                      margin: 15px 0;
                  }
              """
          )
          
          review_text = st.text_area(
              "Your valuable feedback / suggestions", 
              placeholder="App kaisa laga? Kya improve kar sakte hain? Be honest 😊",
              height=130
          )
          
          col1, col2 = st.columns([3, 1])
          with col1:
              submitted = st.form_submit_button("Submit Review", use_container_width=True)
          with col2:
              if st.form_submit_button("Cancel", use_container_width=True):
                  st.session_state.show_review = False
                  st.rerun()

          if submitted:
              if not review_text.strip():
                  st.warning("Please write something in the review!")
              else:
                  try:
                      conn = st.connection("gsheets", type=GSheetsConnection)
                      timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                      
                      new_review = pd.DataFrame([{
                          "Timestamp": timestamp,
                          "Rating": int(rating),
                          "Review Message": review_text.strip(),
                          "Username": "Anonymous"
                      }])
                      
                      conn.write(new_review, worksheet="Sheet1", mode="a")
                      
                      st.success(f"Thank you! You rated us {rating} ⭐")
                      st.balloons()
                      time.sleep(1.5)
                      st.session_state.show_review = False
                      st.rerun()
                  except Exception as e:
                      st.error(f"Error saving review: {e}")

  # --------- END REVIEW SYSTEM ----------
  st.info("Developed with ❤️ by Nilay")

# ---------------- 5. MAIN APP LOGIC (bilkul same rakha hai) ----------------
if df is not None:
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include="number").columns.tolist()
  
  if page == "🏠 Home & Visualizer":
    st.markdown("""
      <h2 style='color: #4facfe;'>📊 Professional Data Visualizer</h2>
      <hr style='margin-top: 0; margin-bottom: 20px; border: 0; height: 1px; background-image: linear-gradient(to right, #4facfe, #00f2fe, transparent);'>
      """, unsafe_allow_html=True)
   
    m1, m2, m3 = st.columns(3)
    m1.metric("📈 Rows", df.shape[0])
    m2.metric("📋 Columns", df.shape[1])
    m3.metric("⚠️ Missing Cells", int(df.isnull().sum().sum()))
    st.divider()

    st.sidebar.header("🎨 Graph Settings")
    g_type = st.sidebar.selectbox("Chart Type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    chart_title = st.sidebar.text_input("Chart Title", "My Analysis")
   
    x_ax = st.sidebar.selectbox("X-Axis", all_cols)
    y_ax = st.sidebar.selectbox("Y-Axis (Numeric)", num_cols) if num_cols else None

    st.subheader("🔍 Filter Data")
    f_col = st.selectbox("Select column to filter", all_cols)
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect("Select Values", u_vals, default=u_vals[:5] if len(u_vals)>5 else u_vals)
    df_filtered = df[df[f_col].isin(s_vals)]

    if g_type == "Auto Suggestion":
      g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
      st.info(f"✨ Suggested: {g_type} Chart")

    fig = None
    try:
      if g_type == "Heatmap":
        corr = df_filtered.corr(numeric_only=True)
        if not corr.empty:
          fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
      elif y_ax:
        if g_type == "Bar": fig = px.bar(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Line": fig = px.line(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Scatter": fig = px.scatter(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Pie": fig = px.pie(df_filtered, names=x_ax, values=y_ax, title=chart_title)
        elif g_type == "Histogram": fig = px.histogram(df_filtered, x=y_ax, title=chart_title)
        elif g_type == "Box": fig = px.box(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Area": fig = px.area(df_filtered, x=x_ax, y=y_ax, title=chart_title)

      if fig:
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
      st.error(f"Visualization Error: {e}")

    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Filtered Data (CSV)", csv, "graphico_report.csv", "text/csv")

  elif page == "🔍 Raw Insights":
    st.markdown("<h2 style='color: #00f2fe;'>🧠 Technical Data Insights</h2>", unsafe_allow_html=True)
    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
      st.subheader("📊 Descriptive Statistics")
      st.write(df.describe())
    with col2:
      st.subheader("🛠️ Column Metadata")
      st.dataframe(pd.DataFrame(df.dtypes, columns=["Type"]).astype(str))
    st.divider()
    st.subheader("❌ Missing Values Check")
    st.write(df.isnull().sum())

  else:  # Samples page
    st.title("Check before Using")
    st.video("Tutorial.mp4")   # agar video hai toh
    st.subheader("Taste it Nicely! ")
    # tera samples code yahan same rahega

else:
  st.markdown("""
    <div style='text-align: center; padding: 80px 20px;'>
      <h1 style='font-size: 3.2em; color: #4facfe;'>💎 Graphico Pro</h1>
      <p style='font-size: 1.3em; color: #a1a1a1;'>Your Smartest Data Companion</p>
      <br><br>
      <div style='background-color: #1e2130; padding: 30px; border-radius: 15px; border: 1px solid #4facfe; max-width: 600px; margin: 0 auto;'>
        <p style='font-size: 1.1em;'>👈 <b>Start by uploading your dataset from the sidebar.</b></p>
      </div>
    </div>
    """, unsafe_allow_html=True)

# Temporary message
st.info("Please submit your review with us. We have updated our review system. Thanks for your support!")
