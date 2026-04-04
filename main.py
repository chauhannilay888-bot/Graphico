import streamlit as st 
import streamlit.components.v1 as components
import io
import pandas as pd
import plotly.express as px
import os
from PIL import Image
import json
from streamlit_gsheets import GSheetsConnection
from sklearn.preprocessing import LabelEncoder, PolynomialFeatures
from sklearn.linear_model import LinearRegression
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
<meta name="msvalidate.01" content="ADE771C3184D04E01C54AFC606C27AA1" />
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
  
  page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights", "DS Hub", "📖 Samples"], index=0)
  
  uploaded_file = st.file_uploader("Upload Dataset (CSV, Excel, JSON)", type=["csv", "xlsx", "xls", "json"])
  
  df = None
  if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    df = load_data(uploaded_file, ext)
    if df is not None:
      st.success("✅ Dataset Loaded!")

  st.divider()
  if "show_review" not in st.session_state:
    st.session_state.show_review = False

  st.caption("🚀 Review us to help Nilay unlock ML features!")
  if st.button("⭐ Click here to Review Us!", use_container_width=True):
    st.session_state.show_review = not st.session_state.show_review

  if st.session_state.show_review:
    with st.expander("📝 Help Nilay Improve", expanded=True):
      st.markdown("<p style='font-size: 0.8em;'>Your feedback as a student developer's fuel! ⛽</p>", unsafe_allow_html=True)
      rating = st.selectbox("Rate us", [5, 4, 3, 2, 1], key="rev_rating")
      review_text = st.text_area("Your thoughts...", placeholder="What should I add next?", key="rev_text")
      
      if st.button("Submit Review", key="rev_submit"):
        if not review_text.strip():
          st.warning("Please write a review to submit")
        else:
          try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            try:
              existing_data = conn.read(worksheet="Sheet1", ttl=0)
            except:
              existing_data = pd.DataFrame(columns=["rating", "review"])
            
            existing_data = existing_data.dropna(how='all')
            new_row = pd.DataFrame([{"rating": int(rating), "review": review_text.strip()}])
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            
            conn.update(worksheet="Sheet1", data=updated_df)
            st.cache_data.clear()
            st.success("✅ Saved! You're a legend!")
            st.balloons()
            st.session_state.show_review = False
          except Exception as e:
            st.error(f"Error: {e}")
  
  st.info("Developed with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if df is not None:
  all_cols = df.columns.tolist()
  num_cols = df.select_dtypes(include="number").columns.tolist()

  st.toast("Enjoying the tool? Don't forget to leave a review in the sidebar! ⭐", icon="🚀")

  if page == "🏠 Home & Visualizer":
    pass

  elif page == "🔍 Raw Insights":
    pass

  elif page == "DS Hub":
    st.title("Welcome to DS Mastermind's Hub 🧠💡")
    df = pd.DataFrame(df)

    # ✅ session state init (SAFE ADD)
    if "df" not in st.session_state:
      st.session_state["df"] = df

    option_2 = st.selectbox(
      "Encode categorical variables with",
      ("Label Encoding (for 2 categories)", "One-Hot Encoding (for more than 2 categories)"),
      key="encoding_method"
    )

    if option_2 == "Label Encoding (for 2 categories)":
      colm = st.selectbox("Select a column to encode", df.columns, key="column_to_encode")
      if df[colm].dtype != 'object':
        st.info("No need to encode this column as it is numeric.")
      le = LabelEncoder()
      name = colm.lower().replace(" ", "_") + "_encoded"
      df[name] = le.fit_transform(df[colm])

    elif option_2 == "One-Hot Encoding (for more than 2 categories)":
      colm = st.selectbox("Select a column to encode", df.columns, key="column_to_one_hot_encode")
      if df[colm].dtype != 'object':
        st.info("No need to encode this column as it is numeric.")
      df = pd.get_dummies(df, columns=[colm], prefix=colm.lower().replace(" ", "_"))

    st.write(df)

    def fill_missing_values(df):
      for column in df.columns:
        if df[column].dtype == 'object':
          df[column] = df[column].fillna(df[column].mode()[0])
        else:
          df[column] = df[column].fillna(df[column].mean())
      return df

    fill_missing_values(df)

    st.info("✨ No need to worry about missing values, mastermind budy has taken care of it for you!")

    work_options = st.radio(
      "What would you like to do?",
      ("Make Predictions", "Edit DataFrame"),
      key="work_options"
    )

    # ✅ FIXED EDIT SECTION
    if work_options == "Edit DataFrame":
      edit_option = st.selectbox(
        "Choose the work to do with DataFrame",
        ("Replace a value", "Remove a row", "Remove a column"),
        key="edit_options"
      )

      df = st.session_state.get("df", df)

      if edit_option == "Replace a value":
        column_to_replace = st.selectbox("Select a column", df.columns)
        index_number = st.number_input("Enter index", min_value=0, step=1)
        new_value = st.text_input("Enter new value")

        if st.button("Replace Value"):
          try:
            index_number = int(index_number)
            if pd.api.types.is_numeric_dtype(df[column_to_replace]):
              new_value = float(new_value)

            df.at[index_number, column_to_replace] = new_value
            st.success("✅ Value replaced successfully!")
            st.session_state["df"] = df
            st.write(df)

          except Exception as e:
            st.error(f"Error: {e}")

      elif edit_option == "Remove a row":
        index_to_remove = st.number_input("Enter index", min_value=0, step=1)

        if st.button("Remove Row"):
          try:
            df.drop(index=int(index_to_remove), inplace=True)
            df.reset_index(drop=True, inplace=True)

            st.success("✅ Row removed successfully!")
            st.session_state["df"] = df
            st.write(df)

          except Exception as e:
            st.error(f"Error: {e}")

      elif edit_option == "Remove a column":
        column_to_remove = st.selectbox("Select column", df.columns)

        if st.button("Remove Column"):
          try:
            df.drop(columns=[column_to_remove], inplace=True)

            st.success("✅ Column removed successfully!")
            st.session_state["df"] = df
            st.write(df)

          except Exception as e:
            st.error(f"Error: {e}")

    else:
      try:
        df = st.session_state.get("df", df)
        st.subheader("New DataFrame for Predictions")
        st.write(df)

        X = st.selectbox("Training on column", df.columns, key="training_column")
        y = st.selectbox("Predicting column", df.columns, key="predicting_column")

        models = st.radio(
          "Select a model for predictions:",
          ("Model 1", "Model 2"),
          key="model_selection"
        )

        if models == "Model 1":
          model = LinearRegression()
          model.fit(df[[X]].values, df[y].values)

          popu = st.number_input("Enter a value to predict", key="input_value")
          predictions = model.predict([[popu]])

          st.subheader("Our obedient child is predicting...")
          st.subheader(f"Predicted value: {predictions[0]:.0f}")

        elif models == "Model 2":
          degree = st.slider("Select polynomial degree", 2, 5, 2, key="poly_degree")
          model = make_pipeline(PolynomialFeatures(degree), LinearRegression())
          model.fit(df[[X]].values, df[y].values)

          popu = st.number_input("Enter a value to predict", key="input_value_5")
          predictions = model.predict([[popu]])

          st.subheader("Smart with foresight, let's see the predictions...")
          st.subheader(f"Predicted value: {predictions[0]:.0f}")

        else:
          st.info("Out of Service, Please select another model.")

      except ValueError:
        st.error("Can't provide predictions on non-numeric data. Please select numeric columns for training and predicting.")
