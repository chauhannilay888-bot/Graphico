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

    page = st.radio("✨ Navigation", 
                    ["🏠 Home & Visualizer", "🔍 Raw Insights", "DS Hub", "📖 Samples"], 
                    index=0)

    uploaded_file = st.file_uploader("Upload Dataset (CSV, Excel, JSON)", 
                                     type=["csv", "xlsx", "xls", "json"])

    df = None
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        df = load_data(uploaded_file, ext)
        if df is not None:
            st.success("✅ Dataset Loaded!")

    # --------- ⭐ GOOGLE SHEETS REVIEW SYSTEM ----------
    st.divider()
    if "show_review" not in st.session_state:
        st.session_state.show_review = False

    st.caption("🚀 Review us to help Nilay unlock ML features!")

    if st.button("⭐ Click here to Review Us!", use_container_width=True):
        st.session_state.show_review = not st.session_state.show_review

    if st.session_state.show_review:
        with st.expander("📝 Help Nilay Improve", expanded=True):
            st.markdown("<p style='font-size: 0.8em;'>Your feedback as a student developer's fuel! ⛽</p>", 
                        unsafe_allow_html=True)
            
            rating = st.selectbox("Rate us", [5, 4, 3, 2, 1], key="rev_rating")
            review_text = st.text_area("Your thoughts...", 
                                       placeholder="What should I add next?", 
                                       key="rev_text")
            
            if st.button("Submit", key="rev_submit"):
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

    elif page == "DS Hub":
        st.title("Welcome to DS Mastermind's Hub 🧠💡")
        df = pd.DataFrame(df)
        
        option_2 = st.selectbox(
            "Encode categorical variables with", 
            ("Label Encoding (for 2 categories)", "One-Hot Encoding (for more than 2 categories)"),
            key="encoding_method"
        )

        if option_2 == "Label Encoding (for 2 categories)":
            colm = st.selectbox("Select a column to encode", df.columns, key="column_to_encode")
            if df[colm].dtype != 'object':
                st.info("No need to encode this column as it is numeric.")
            else:
                le = LabelEncoder()
                name = colm.lower().replace(" ", "_") + "_encoded"
                df[name] = le.fit_transform(df[colm])

        elif option_2 == "One-Hot Encoding (for more than 2 categories)":
            colm = st.selectbox("Select a column to encode", df.columns, key="column_to_one_hot_encode")
            if df[colm].dtype != 'object':
                st.info("No need to encode this column as it is numeric.")
            else:
                df = pd.get_dummies(df, columns=[colm], prefix=colm.lower().replace(" ", "_"))

        st.write(df)

        # Fill missing values
        def fill_missing_values(df):
            for column in df.columns:
                if df[column].dtype == 'object':
                    df[column] = df[column].fillna(df[column].mode()[0])
                else:
                    df[column] = df[column].fillna(df[column].mean())
            return df

        fill_missing_values(df)
        st.info("✨ No need to worry about missing values, mastermind buddy has taken care of it for you!")

        work_options = st.radio(
            "What would you like to do?",
            ("Make Predictions", "Edit DataFrame"),
            key="work_options"
        )

        if work_options == "Edit DataFrame":
            edit_option = st.selectbox(
                "Choose the work to do with DataFrame",
                ("Replace a value", "Remove a row", "Remove a column"),
                key="edit_options"
            )

            if edit_option == "Replace a value":
                column_to_replace = st.selectbox("Select a column to replace values", df.columns, key="replacement_column")
                index_number = st.number_input("Enter the index number of the value to replace", key="replacement_index")
                new_value = st.text_input("Enter the new value", key="replacement_new_value")
                if st.button("Replace Value", key="replace_button"):
                    df.at[index_number, column_to_replace] = new_value
                    st.success("Value replaced successfully!")
                    st.write(df)

            elif edit_option == "Remove a row":
                index_to_remove = st.number_input("Enter the index number of the row to remove", key="row_removal_index")
                if st.button("Remove Row", key="remove_row_button"):
                    df.drop(index=index_to_remove, inplace=True)
                    st.success("Row removed successfully!")
                    st.write(df)

            elif edit_option == "Remove a column":
                column_to_remove = st.selectbox("Select a column to remove", df.columns, key="column_removal")
                if st.button("Remove Column", key="remove_column_button"):
                    df.drop(columns=[column_to_remove], inplace=True)
                    st.success("Column removed successfully!")
                    st.write(df)

        elif page == "Ds Hub":  # Make Predictions
            try:
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

            except ValueError:
                st.error("Can't provide predictions on non-numeric data. Please select numeric columns for training and predicting.")
        else:
          st.title("Check before Using")
          st.video("Tutorial.mp4")
          st.subheader("Taste it Nicely! ")
          files = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
          for i in range(0, len(files), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
              if i + j < len(files):
                col.image(Image.open(os.path.join("tutorial_PNGs", files[i+j])), use_container_width=True)


elif page == "📖 Samples":
    st.title("Check before Using")
    st.video("Tutorial.mp4")
    st.subheader("Taste it Nicely! ")
    files = [f for f in os.listdir("tutorial_PNGs") if f.endswith(".png")]
    for i in range(0, len(files), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(files):
                col.image(Image.open(os.path.join("tutorial_PNGs", files[i+j])), use_container_width=True)

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
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://graphico.streamlit.app</loc>
    <lastmod>2026-03-31</lastmod>
    <priority>1.0</priority>
  </url>
</urlset>"""
    st.text(sitemap_xml)
    st.stop()
