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
  .main-header {
    color: #4facfe;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
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

# ---------------- 3. DATA LOADING & CLEANING ----------------
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
  st.markdown("<p style='text-align: center; font-size: 0.8em;'>Empowering Your Data Journey</p>", unsafe_allow_html=True)
  st.divider()
  
  page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights", "🧠 DS Hub", "📖 Samples"], index=0)
  
  uploaded_file = st.file_uploader("Upload Dataset (CSV, Excel, JSON)", type=["csv", "xlsx", "xls", "json"])
  
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    if "df" not in st.session_state:
        raw_df = load_data(uploaded_file, ext)
        if raw_df is not None:
            st.session_state.df = fill_missing_values(raw_df)
    st.success("✅ Dataset Loaded!")

  # --------- ⭐ REVIEW SYSTEM ----------
  st.divider()
  if "show_review" not in st.session_state:
      st.session_state.show_review = False

  st.caption("🚀 Review us to help Nilay unlock ML features!")
  if st.button("⭐ Click here to Review Us!", use_container_width=True):
      st.session_state.show_review = not st.session_state.show_review

  if st.session_state.show_review:
      with st.expander("📝 Feedback Form", expanded=True):
          rating = st.selectbox("Rate us", [5, 4, 3, 2, 1], key="rev_rating")
          review_text = st.text_area("Your thoughts...", key="rev_text")
          if st.button("Submit Review"):
              try:
                  conn = st.connection("gsheets", type=GSheetsConnection)
                  existing = conn.read(worksheet="Sheet1", ttl=0)
                  new_row = pd.DataFrame([{"rating": int(rating), "review": review_text.strip()}])
                  updated_df = pd.concat([existing, new_row], ignore_index=True).dropna(how='all')
                  conn.update(worksheet="Sheet1", data=updated_df)
                  st.success("✅ Legend! Review Saved.")
                  st.balloons()
                  st.session_state.show_review = False
              except: st.error("Link error. Check Google Sheets connection!")
  
  st.info("Developed with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if "df" in st.session_state:
  df = st.session_state.df
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include=np.number).columns.tolist()
  st.toast("Enjoying the tool? Leave a review! ⭐", icon="🚀")

  # --- PAGE 1: VISUALIZER ---
  if page == "🏠 Home & Visualizer":
    st.markdown("<h2 class='main-header'>📊 Professional Data Visualizer</h2>", unsafe_allow_html=True)
    
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
    f_col = st.selectbox("Filter by Column", all_cols)
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect("Select Values", u_vals, default=u_vals[:5] if len(u_vals)>5 else u_vals)
    df_filtered = df[df[f_col].isin(s_vals)]
    
    if g_type == "Auto Suggestion":
      g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
      st.info(f"✨ Mastermind Suggested: {g_type}")
    
    try:
      fig = None
      if g_type == "Heatmap":
        corr = df_filtered.corr(numeric_only=True)
        if not corr.empty: fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
      elif y_ax:
        if g_type == "Bar": fig = px.bar(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Line": fig = px.line(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Scatter": fig = px.scatter(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Pie": fig = px.pie(df_filtered, names=x_ax, values=y_ax, title=chart_title)
        elif g_type == "Histogram": fig = px.histogram(df_filtered, x=y_ax, title=chart_title)
        elif g_type == "Box": fig = px.box(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Area": fig = px.area(df_filtered, x=x_ax, y=y_ax, title=chart_title)
      
      if fig: st.plotly_chart(fig, use_container_width=True)
      else: st.warning("Please select a numeric column for Y-axis.")
    except Exception as e: st.error(f"Visualization Error: {e}")
    
    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Filtered Data (CSV)", csv, "graphico_report.csv", "text/csv")

  # --- PAGE 2: RAW INSIGHTS ---
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
    st.subheader("❌ Missing Values Breakdown")
    st.write(df.isnull().sum())
    st.info("Missing values handled by 'Mastermind Buddy' logic! ✅")

  # --- PAGE 3: DS HUB (ML & EDITOR) ---
  elif page == "🧠 DS Hub":
    st.title("Welcome to DS Mastermind's Hub 🧠💡")
    
    # Indentation Fix for DS Hub Logic
    st.subheader("Handling Missing Values & Encoding")
    st.info("✨ Missing values are already managed by the system!")

    option_2 = st.selectbox(
      "Encode categorical variables with",
      ("Label Encoding (for 2 categories)", "One-Hot Encoding (for more than 2 categories)"),
      key="encoding_method"
    )

    if option_2 == "Label Encoding (for 2 categories)":
      colm = st.selectbox("Select a column to encode", df.columns, key="column_to_encode")
      if df[colm].dtype != 'object':
        st.info("No need to encode this column as it is numeric.")
      if st.button("Apply Label Encoding"):
        le = LabelEncoder()
        name = colm.lower().replace(" ", "_") + "_encoded"
        df[name] = le.fit_transform(df[colm].astype(str))
        st.session_state.df = df
        st.success(f"Added column: {name}")

    elif option_2 == "One-Hot Encoding (for more than 2 categories)":
      colm = st.selectbox("Select a column to encode", df.columns, key="column_to_one_hot_encode")
      if df[colm].dtype != 'object':
        st.info("No need to encode this column as it is numeric.")
      if st.button("Apply One-Hot Encoding"):
        df = pd.get_dummies(df, columns=[colm], prefix=colm.lower().replace(" ", "_"))
        st.session_state.df = df
        st.success("One-Hot Encoding applied!")

    st.write(df.head())
    st.divider()

    work_options = st.radio("What would you like to do?", ("Make Predictions", "Edit DataFrame"), key="work_options")

    if work_options == "Edit DataFrame":
      edit_option = st.selectbox("Choose Action", ("Replace a value", "Remove a row", "Remove a column"), key="edit_options")

      if edit_option == "Replace a value":
        column_to_replace = st.selectbox("Select column", df.columns, key="replacement_column")
        index_number = st.number_input("Enter Index", 0, len(df)-1, key="replacement_index")
        new_value = st.text_input("Enter New Value", key="replacement_new_value")
        if st.button("Replace Value", key="replace_button"):
          df.at[index_number, column_to_replace] = new_value
          st.session_state.df = df
          st.success("Value replaced successfully!")
          st.rerun()

      elif edit_option == "Remove a row":
        index_to_remove = st.number_input("Index to remove", 0, len(df)-1, key="row_removal_index")
        if st.button("Remove Row"):
          df.drop(index=index_to_remove, inplace=True)
          st.session_state.df = df
          st.success("Row removed!")
          st.rerun()

      elif edit_option == "Remove a column":
        column_to_remove = st.selectbox("Select column to remove", df.columns, key="column_removal")
        if st.button("Remove Column"):
          df.drop(columns=[column_to_remove], inplace=True)
          st.session_state.df = df
          st.success("Column removed!")
          st.rerun()

    else:
      st.subheader("AI Prediction Suite")
      try:
          X_pred = st.selectbox("Training on column (X)", num_cols, key="training_column")
          y_pred = st.selectbox("Predicting column (y)", num_cols, key="predicting_column")
          models = st.radio("Select Model:", ("Model 1 (Linear)", "Model 2 (Polynomial)"), key="model_selection")

          if models == "Model 1 (Linear)":
            model = LinearRegression()
            model.fit(df[[X_pred]].values, df[y_pred].values)
            popu = st.number_input("Enter value to predict")
            if st.button("Predict"):
              predictions = model.predict([[popu]])
              st.subheader("Our obedient child is predicting...")
              st.subheader(f"Predicted value: {predictions[0]:.2f}")

          elif models == "Model 2 (Polynomial)":
            degree = st.slider("Select degree", 2, 5, 2)
            model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
            model.fit(df[[X_pred]].values, df[y_pred].values)
            popu = st.number_input("Enter value to predict")
            if st.button("Smart Predict"):
              predictions = model.predict([[popu]])
              st.subheader("Smart with foresight...")
              st.subheader(f"Predicted value: {predictions[0]:.2f}")
      except: st.error("Ensure you have numeric data for predictions!")

  # --- PAGE 4: SAMPLES ---
  elif page == "📖 Samples":
    st.title("Check before Using")
    if os.path.exists("Tutorial.mp4"): st.video("Tutorial.mp4")
    st.subheader("Tutorial Gallery")
    if os.path.exists("tutorial_PNGs"):
      files = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
      for i in range(0, len(files), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
          if i+j < len(files):
            col.image(Image.open(os.path.join("tutorial_PNGs", files[i+j])), use_container_width=True)
    else: st.info("Sample gallery assets not found.")

# --- LANDING PAGE ---
else:
  st.markdown("""
    <div style='text-align: center; padding: 100px;'>
      <h1 style='font-size: 4em; color: #4facfe;'>💎 Graphico Pro</h1>
      <p style='font-size: 1.5em; color: #a1a1a1;'>Your Smartest Data Companion</p>
      <br>
      <div style='background-color: #1e2130; padding: 30px; border-radius: 20px; border: 1px solid #4facfe;'>
        <h3>👈 Start by uploading your dataset in the sidebar.</h3>
        <p>Supports CSV, Excel, and JSON formats.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

# Sitemap Generator
if st.query_params.get("sitemap") == "true":
  sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://graphico.streamlit.app</loc><lastmod>2026-04-05</lastmod><priority>1.0</priority></url>
</urlset>"""
  st.text(sitemap_xml)
  st.stop()
