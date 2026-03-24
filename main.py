import streamlit as st
import streamlit.components.v1 as components
import io

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
# HTML Component ko render karo
components.html(ga_code, height=0)


import pandas as pd
import plotly.express as px

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

@st.cache_data
def load_data(file, ext):
    if ext == "csv": return pd.read_csv(file)
    elif ext in ["xlsx", "xls"]:
      try:
            df = pd.read_excel(io.BytesIO(file.read()), engine='openpyxl')
      except Exception as e:
            st.error(f"Excel Error: {e}")
    elif ext == "json":
      df = pd.read_json(file)
        
uploaded_file = st.file_uploader("Upload dataset", type=["csv", "xlsx", "xls", "json"])
df = None

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        df = load_data(uploaded_file, ext)
        st.success("Dataset loaded successfully")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

if df is not None:
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Missing", int(df.isnull().sum().sum()))

    # Filter
    st.subheader("Filter Data")
    f_col = st.selectbox("Select column to filter", df.columns)
    u_vals = df[f_col].dropna().unique()
    s_vals = st.multiselect("Values", u_vals, default=u_vals)
    df = df[df[f_col].isin(s_vals)]

    # Sidebar Settings
    st.sidebar.header("Graph Settings")
    g_type = st.sidebar.selectbox("Chart type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
    chart_title = st.sidebar.text_input("Chart Title", "My Chart")
    
    num_cols = df.select_dtypes(include="number").columns
    x_ax = st.sidebar.selectbox("X Axis", df.columns)
    y_ax = st.sidebar.selectbox("Y Axis", num_cols) if len(num_cols) > 0 else None

    if g_type == "Auto Suggestion":
        g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
        st.info(f"Suggested: {g_type}")

    fig = None
    if g_type != "Heatmap" and y_ax:
        if g_type == "Bar": fig = px.bar(df, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Line": fig = px.line(df, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Scatter": fig = px.scatter(df, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Pie": fig = px.pie(df, names=x_ax, values=y_ax, title=chart_title)
        elif g_type == "Histogram": fig = px.histogram(df, x=y_ax, title=chart_title)
        elif g_type == "Box": fig = px.box(df, x=x_ax, y=y_ax, title=chart_title)
        elif g_type == "Area": fig = px.area(df, x=x_ax, y=y_ax, title=chart_title)
    
    if g_type == "Heatmap":
        corr = df.corr(numeric_only=True)
        if not corr.empty: fig = px.imshow(corr, text_auto=True, title="Heatmap")

    if fig: st.plotly_chart(fig, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data", csv, "filtered_data.csv", "text/csv")
