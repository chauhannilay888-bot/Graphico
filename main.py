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

# ---------------- 3. ANTI-TABAHI CLEANING LOGIC (Only when needed) ----------------
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
                if ext == "csv": 
                    data = pd.read_csv(u_file)
                elif ext in ["xlsx", "xls"]: 
                    data = pd.read_excel(u_file)
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
    if st.session_state.action_count % 3 == 0 and st.session_state.action_count > 0:
        st.toast("💡 Loving Graphico? Please leave a quick review in the sidebar!", icon="⭐")

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
        st.title("Welcome to DS Hub, the only agent optimised for your data!")
        
        df = df.copy()
        
        if df.isnull().values.any():
            def fill_missing_values(df):
                for column in df.columns:
                    if df[column].isnull().any():
                        if pd.api.types.is_numeric_dtype(df[column]):
                            df[column].fillna(df[column].mean(), inplace=True)
                        else:
                            mode_vals = df[column].mode()
                            df[column].fillna(mode_vals[0] if not mode_vals.empty else "Unknown", inplace=True)
                return df
            df = fill_missing_values(df)
            st.info("✨ Missing values handled by Mr Mastermind")

        le = LabelEncoder()
        encoding_type = st.selectbox("Select the type of Encoding", 
                                     ("Label Encoding", "One-Hot Encoding"))
        t_colm = st.selectbox("Select the column to encode", df.columns)
        
        if encoding_type == "Label Encoding":
            encd_colm_name = str(t_colm) + "_encoded"
            df[encd_colm_name] = le.fit_transform(df[t_colm])
            st.write(df)
        elif encoding_type == "One-Hot Encoding":
            df = pd.get_dummies(df, columns=[t_colm])
            st.session_state.df = df 
            st.write(df)
            st.rerun()
          
        work_option = st.radio("Select the option to work on",
                               ("Edit DataFrame", "Make Predictions"))

        if work_option == "Edit DataFrame":
            df = st.session_state.get('df', df)

            op = st.selectbox("Select the editing option",
                              ("Remove Column", "Remove Row", "Replace or Add Value"))

            if op == "Remove Column":
                col_to_remove = st.selectbox("Select the column to remove", df.columns)
                if st.button("Remove Column"):
                    df.drop(columns=[col_to_remove], inplace=True)
                    st.success(f"Column '{col_to_remove}' has been removed.")
                    st.session_state['df'] = df
                    st.rerun()

            elif op == "Remove Row":
                row_to_remove = st.number_input("Enter the index of the row to remove",
                                                min_value=0,
                                                max_value=len(df)-1,
                                                step=1)
                if st.button("Remove Row"):
                    df.drop(index=row_to_remove, inplace=True)
                    st.success(f"Row with index {row_to_remove} has been removed.")
                    st.session_state['df'] = df
                    st.rerun()

            elif op == "Replace or Add Value":
                col_to_edit = st.selectbox("Select the column to edit", df.columns)
                row_to_edit = st.number_input("Enter the index of the row to edit",
                                              min_value=0,
                                              max_value=len(df)-1,
                                              step=1)
                new_value = st.text_input("Enter the new value")
               
                if st.button("Update Value"):
                    try:
                        df.at[row_to_edit, col_to_edit] = new_value
                        st.success(f"Value at row {row_to_edit}, column '{col_to_edit}' updated to '{new_value}'.")
                        st.session_state['df'] = df
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
           
            st.write("**Updated DataFrame:**")
            st.dataframe(df)

        elif work_option == "Make Predictions":
            df = st.session_state.get('df', df)
           
            st.subheader("Model Training and Predictions")
           
            feature_column = st.selectbox("Select the column for training (input)",
                                          df.columns, key="feature_col")
       
            target_column = st.selectbox("Select the target column for prediction (output)",
                                         df.columns, key="target_col")
           
            # ==================== PERFECT TRY-EXCEPT SAFETY ====================
            try:
                if df[feature_column].dtype == 'object' or df[target_column].dtype == 'object':
                    st.error("❌ Both feature and target columns must be numeric for model training.")
                    st.info("Tip: Use Label Encoding or One-Hot Encoding first to convert text columns.")
                else:
                    models = st.radio("Select the model to train", ("Model 1", "Model 2"))
                   
                    if models == "Model 1":
                        model = LinearRegression()
                        model.fit(df[[feature_column]], df[[target_column]])
                        st.success("Model 1 has been trained successfully.")
                       
                        to_predict = st.number_input("Enter a value to predict", step=0.01)
                        if st.button("Predict with Model 1"):
                            prediction = model.predict([[to_predict]])
                            st.subheader(f"Predicted value for input {to_predict}: {prediction[0][0]:.0f}")
                   
                    else:
                        degree = st.slider("Select the degree for polynomial features",
                                           min_value=1, max_value=10, value=2)
                        model = make_pipeline(PolynomialFeatures(degree=degree), LinearRegression())
                        model.fit(df[[feature_column]], df[[target_column]])
                        st.success("Model 2 has been trained successfully.")
                       
                        to_predict = st.number_input("Enter a value to predict", step=0.01)
                        if st.button("Predict with Model 2"):
                            prediction = model.predict([[to_predict]])
                            st.subheader(f"Predicted value for input {to_predict}: {prediction[0][0]:.0f}")
            except Exception as e:
                st.error(f"Model Error: {e}")
                st.info("Please make sure both columns are numeric.")

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

if st.query_params.get("sitemap") == "true":
    st.text("Engine Status: 100% Operational")
    st.stop()
