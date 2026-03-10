import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Graphico Pro",
    layout="wide",
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>

body {
background: #0f172a;
}

.block-container {
padding-top: 2rem;
}

.card {
background: rgba(255,255,255,0.06);
padding: 25px;
border-radius: 12px;
backdrop-filter: blur(12px);
box-shadow: 0 10px 30px rgba(0,0,0,0.3);
margin-bottom:20px;
}

.title {
font-size:28px;
font-weight:bold;
background: linear-gradient(90deg,#6366f1,#06b6d4);
-webkit-background-clip:text;
color:transparent;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown('<div class="title">Graphico Pro 📊</div>', unsafe_allow_html=True)
st.write("Upload datasets and generate interactive professional charts.")

px.defaults.template = "plotly_dark"

# ---------------- DATA LOADER ----------------

@st.cache_data
def load_data(file, ext):
    if ext == "csv":
        return pd.read_csv(file)
    elif ext in ["xlsx", "xls"]:
        return pd.read_excel(file)
    elif ext == "json":
        return pd.read_json(file)

# ---------------- FILE UPLOAD ----------------

uploaded_file = st.file_uploader(
    "Upload dataset",
    type=["csv", "xlsx", "xls", "json"]
)

df = None

if uploaded_file:

    ext = uploaded_file.name.split(".")[-1].lower()

    try:
        df = load_data(uploaded_file, ext)
        st.success("Dataset loaded successfully")
        st.dataframe(df.head())

    except Exception as e:
        st.error("Error loading file")
        st.stop()

# ---------------- DATA INSIGHTS ----------------

if df is not None:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rows", df.shape[0])

    with col2:
        st.metric("Columns", df.shape[1])

    with col3:
        st.metric("Missing values", int(df.isnull().sum().sum()))

# ---------------- FILTER DATA ----------------

    st.subheader("Filter Data")

    filter_col = st.selectbox("Select column to filter", df.columns)

    unique_vals = df[filter_col].dropna().unique()

    selected_vals = st.multiselect(
        "Values",
        unique_vals,
        default=unique_vals
    )

    df = df[df[filter_col].isin(selected_vals)]

# ---------------- GRAPH SETTINGS ----------------

    st.sidebar.header("Graph Settings")

    graph_type = st.sidebar.selectbox(
        "Chart type",
        [
            "Auto Suggestion",
            "Bar",
            "Line",
            "Scatter",
            "Pie",
            "Histogram",
            "Box",
            "Area",
            "Heatmap"
        ]
    )

    title = st.sidebar.text_input("Chart Title")

    numeric_cols = df.select_dtypes(include="number").columns
    columns = df.columns

    x_axis = st.sidebar.selectbox("X Axis", columns)

    if len(numeric_cols) > 0:
        y_axis = st.sidebar.selectbox("Y Axis", numeric_cols)
    else:
        st.warning("Dataset has no numeric columns")
        y_axis = None

# ---------------- SMART SUGGESTION ----------------

    if graph_type == "Auto Suggestion":

        if len(numeric_cols) >= 2:
            graph_type = "Scatter"
        elif len(numeric_cols) == 1:
            graph_type = "Histogram"
        else:
            graph_type = "Bar"

        st.info(f"Suggested graph: {graph_type}")

# ---------------- PLOTLY CHARTS ----------------

    fig = None

    if y_axis is not None:

        if graph_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, title=title)

        elif graph_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, title=title)

        elif graph_type == "Scatter":
            fig = px.scatter(df, x=x_axis, y=y_axis, title=title)

        elif graph_type == "Pie":
            fig = px.pie(df, names=x_axis, values=y_axis, title=title)

        elif graph_type == "Histogram":
            fig = px.histogram(df, x=y_axis, title=title)

        elif graph_type == "Box":
            fig = px.box(df, x=x_axis, y=y_axis, title=title)

        elif graph_type == "Area":
            fig = px.area(df, x=x_axis, y=y_axis, title=title)

    if graph_type == "Heatmap":

        corr = df.corr(numeric_only=True)

        if not corr.empty:
            fig = px.imshow(
                corr,
                text_auto=True,
                title="Correlation Heatmap"
            )
        else:
            st.warning("No numeric data for heatmap")

# ---------------- DISPLAY CHART ----------------

    if fig:

        st.plotly_chart(fig, use_container_width=True)

# ---------------- DOWNLOAD GRAPH ----------------

        try:
            img_bytes = fig.to_image(format="png")

            st.download_button(
                label="Download PNG",
                data=img_bytes,
                file_name="graph.png",
                mime="image/png"
            )

        except:
            st.info("Install kaleido for image download: pip install kaleido")

# ---------------- DOWNLOAD DATA ----------------

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered data",
        csv,
        "filtered_data.csv",
        "text/csv"
    )
