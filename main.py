import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import plotly.express as px

# ---------GOOGLE SITE VERIFICATION-----------
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-FHN9KEP6KN');
</script>
<meta name="google-site-verification" content="zINnwjOarj-lAgHmEFrOPaihJvA5iwrmzhapCKGuqj0" />
"""
components.html(ga_code, height=0)

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Graphico Pro - Data Visualizations & Insights Tool",
    page_icon="📊",
    layout="wide",
    menu_items={
        'About': "Graphico Pro: Easiest tool for making impressive charts from Excel/CSV."
    }
)

# ---------------- HEADER ----------------
st.title("Welcome to Graphico Pro!")
st.subheader("Data se Graph Banayein - Fast & Professional")
st.write("Upload datasets and generate interactive professional charts.")

px.defaults.template = "plotly_dark"

# ---------------- DATA LOADING ----------------
@st.cache_data
def load_data(file_content, ext):
    try:
        if ext == "csv":
            return pd.read_csv(io.BytesIO(file_content))
        elif ext in ["xlsx", "xls"]:
            # engine='openpyxl' for .xlsx files
            return pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        elif ext == "json":
            return pd.read_json(io.BytesIO(file_content))
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

uploaded_file = st.file_uploader("Upload dataset", type=["csv", "xlsx", "xls", "json"])
df = None

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    # file.read() pointer ko aage le jata hai, isliye content save kar rahe hain
    file_content = uploaded_file.read()
    df = load_data(file_content, ext)
    
    if df is not None:
        st.success("Dataset loaded successfully!")
        st.subheader("Data Preview (Top 5 Rows)")
        st.dataframe(df.head())
    else:
        st.stop()

# ---------------- MAIN APP LOGIC ----------------
if df is not None:
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Missing Values", int(df.isnull().sum().sum()))

    # Filter Section
    st.divider()
    st.subheader("🔍 Filter Your Data")
    f_col = st.selectbox("Select column to filter", df.columns)
    
    # Bug Fix: Dropna to avoid errors in multiselect
    u_vals = df[f_col].dropna().unique().tolist()
    s_vals = st.multiselect(f"Values in '{f_col}'", u_vals, default=u_vals)
    
    # Filter apply karna
    df_filtered = df[df[f_col].isin(s_vals)]

    # Sidebar Settings
    st.sidebar.header("🎨 Graph Settings")
    g_type = st.sidebar.selectbox("Chart type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    chart_title = st.sidebar.text_input("Chart Title", "My Analysis Chart")
    
    num_cols = df_filtered.select_dtypes(include="number").columns.tolist()
    all_cols = df_filtered.columns.tolist()

    x_ax = st.sidebar.selectbox("X Axis (Horizontal)", all_cols)
    y_ax = st.sidebar.selectbox("Y Axis (Vertical - Numeric)", num_cols) if len(num_cols) > 0 else None

    # Auto Suggestion Logic
    if g_type == "Auto Suggestion":
        if len(num_cols) >= 2:
            g_type = "Scatter"
        else:
            g_type = "Bar"
        st.sidebar.info(f"Auto-selected: {g_type}")

    # Chart Generation
    st.divider()
    fig = None
    
    try:
        if g_type == "Heatmap":
            corr = df_filtered.corr(numeric_only=True)
            if not corr.empty:
                fig = px.imshow(corr, text_auto=True, title="Feature Correlation Heatmap")
            else:
                st.warning("Heatmap ke liye numeric data nahi mila!")
        
        elif y_ax:
            if g_type == "Bar": fig = px.bar(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Line": fig = px.line(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Scatter": fig = px.scatter(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Pie": fig = px.pie(df_filtered, names=x_ax, values=y_ax, title=chart_title)
            elif g_type == "Histogram": fig = px.histogram(df_filtered, x=y_ax, title=chart_title)
            elif g_type == "Box": fig = px.box(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Area": fig = px.area(df_filtered, x=x_ax, y=y_ax, title=chart_title)
        else:
            st.warning("Please ensure you have numeric columns for this chart type.")

        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Download Button for Filtered Data
            st.divider()
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv,
                file_name="graphico_pro_data.csv",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"Visualization Error: {e}")

else:
    st.info("👆 Please upload a CSV, Excel, or JSON file to start.")
