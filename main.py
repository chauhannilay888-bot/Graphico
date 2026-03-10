import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from io import BytesIO

# Page config
st.set_page_config(page_title="Graphico", layout="wide")

st.title("📊 Graphico")
st.subheader("Create beautiful graphs from your data instantly!")

# File uploader
uploaded_file = st.file_uploader(
    "Upload your data (JSON, CSV, Excel)",
    type=["json", "csv", "xlsx", "xls"]
)

df = None

# Load data
if uploaded_file is not None:
    try:
        file_ext = uploaded_file.name.split(".")[-1].lower()

        if file_ext == "csv":
            df = pd.read_csv(uploaded_file)

        elif file_ext in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)

        elif file_ext == "json":
            df = pd.read_json(uploaded_file)

        st.success("✅ Data loaded successfully!")
        st.dataframe(df.head(10))

    except Exception as e:
        st.error(f"Error loading file: {e}")

# If data exists
if df is not None:

    # Sidebar settings
    st.sidebar.header("Graph Settings")

    theme = st.sidebar.selectbox(
        "Graph Theme",
        ["default", "ggplot", "seaborn", "dark_background"]
    )

    plt.style.use(theme)

    color = st.sidebar.color_picker("Graph Color", "#1f77b4")
    show_grid = st.sidebar.checkbox("Show Grid", True)

    graph_type = st.sidebar.radio(
        "Graph Type",
        ["Auto (Smart Suggestion)", "Bar Graph", "Pie Chart",
         "Histogram", "Line Graph", "Scatter Plot"]
    )

    # Dataset insights
    with st.expander("📊 Dataset Insights"):
        st.write("Rows:", df.shape[0])
        st.write("Columns:", df.shape[1])
        st.write("Missing values:", df.isnull().sum().sum())
        st.write("Numeric columns:", len(df.select_dtypes(include="number").columns))
        st.write("Categorical columns:", len(df.select_dtypes(exclude="number").columns))

    # Column detection
    columns = list(df.columns)
    numeric_cols = df.select_dtypes(include="number").columns
    categorical_cols = df.select_dtypes(exclude="number").columns

    # Smart suggestion
    if graph_type == "Auto (Smart Suggestion)":

        if len(numeric_cols) >= 2:
            suggestion = "Scatter Plot"

        elif len(numeric_cols) == 1:
            suggestion = "Histogram"

        elif len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            suggestion = "Bar Graph"

        else:
            suggestion = "Line Graph"

        st.info(f"🤖 Suggested Graph: **{suggestion}**")
        graph_type = suggestion

    title = st.text_input("Graph Title")

    # ---------------- BAR GRAPH ----------------

    if graph_type == "Bar Graph":

        x_axis = st.selectbox("X-axis", columns)
        y_axis = st.selectbox("Y-axis", numeric_cols)

        if st.button("Generate Bar Graph"):

            fig, ax = plt.subplots(figsize=(10,6))
            ax.bar(df[x_axis], df[y_axis], color=color)

            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)
            ax.set_title(title)

            if show_grid:
                ax.grid(True, linestyle=":")

            st.pyplot(fig)
            st.balloons()

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
            buf.seek(0)

            st.download_button(
                "📥 Download PNG",
                buf,
                "bar_graph.png",
                "image/png"
            )

    # ---------------- PIE CHART ----------------

    elif graph_type == "Pie Chart":

        labels = st.selectbox("Labels Column", columns)
        values = st.selectbox("Values Column", numeric_cols)

        if st.button("Generate Pie Chart"):

            colors = plt.cm.tab20.colors

            fig, ax = plt.subplots()

            ax.pie(
                df[values],
                labels=df[labels],
                autopct="%1.1f%%",
                colors=colors
            )

            ax.set_title(title)

            st.pyplot(fig)

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            buf.seek(0)

            st.download_button(
                "📥 Download PNG",
                buf,
                "pie_chart.png",
                "image/png"
            )

    # ---------------- HISTOGRAM ----------------

    elif graph_type == "Histogram":

        col = st.selectbox("Column", numeric_cols)
        bins = st.slider("Bins", 5, 50, 10)

        if st.button("Generate Histogram"):

            fig, ax = plt.subplots(figsize=(10,6))

            ax.hist(df[col], bins=bins, color=color, edgecolor="black")

            ax.set_title(title)
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")

            if show_grid:
                ax.grid(True, linestyle=":")

            st.pyplot(fig)

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            buf.seek(0)

            st.download_button(
                "📥 Download PNG",
                buf,
                "histogram.png",
                "image/png"
            )

    # ---------------- LINE GRAPH ----------------

    elif graph_type == "Line Graph":

        x_axis = st.selectbox("X-axis", columns)
        y_axis = st.selectbox("Y-axis", numeric_cols)

        if st.button("Generate Line Graph"):

            fig, ax = plt.subplots(figsize=(10,6))

            ax.plot(df[x_axis], df[y_axis], color=color, marker="o")

            ax.set_title(title)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)

            if show_grid:
                ax.grid(True, linestyle=":")

            st.pyplot(fig)

            buf = BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            buf.seek(0)

            st.download_button(
                "📥 Download PNG",
                buf,
                "line_graph.png",
                "image/png"
            )

    # ---------------- SCATTER (PLOTLY) ----------------

    elif graph_type == "Scatter Plot":

        x_axis = st.selectbox("X-axis", numeric_cols)
        y_axis = st.selectbox("Y-axis", numeric_cols)

        if st.button("Generate Scatter Plot"):

            fig = px.scatter(
                df,
                x=x_axis,
                y=y_axis,
                color_discrete_sequence=[color],
                title=title
            )

            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⬆ Upload a dataset to begin creating graphs!")
