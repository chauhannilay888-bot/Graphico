import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import json as js
import time

# Dopamine music
import streamlit as st

st.set_page_config(page_title="Graph Creator", layout="wide")

st.title("Create Anytime, Anywhere")
st.subheader("Upload your data and make beautiful graphs instantly!")

# File uploader
uploaded_file = st.file_uploader("Upload your data (JSON, CSV, or Excel)", type=["json", "csv", "xlsx", "xls"])

# Data loading
df = None
if uploaded_file is not None:
    try:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        if file_ext == 'json':
            df = pd.read_json(uploaded_file)
        elif file_ext in ['csv', 'xlsx', 'xls']:
            if file_ext == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format!")
            df = None
        
        if df is not None:
            time.sleep(2)
            st.success("Data loaded successfully!")
            st.dataframe(df)  # Preview
        
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        df = None

# Sidebar for graph type
graph_type = st.sidebar.radio(
    "Choose the type of graph",
    options=["Bar Graph", "Pie Chart", "Histogram", "Line Graph", "Scatter Plot"]
)
st.sidebar.write("Wan't a music? ")
st.sidebar.audio("music.mp3", loop=True)

if df is not None:
    columns = list(df.columns)
    
    color = st.sidebar.color_picker("Choose color", value="#1f77b4")
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    
    if graph_type == "Bar Graph":
        x_axis = st.selectbox("Horizontal axis (X-axis)", options=columns)
        y_axis = st.selectbox("Vertical axis (Y-axis)", options=columns)
        
        if st.button("Plot Bar Graph"):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(df[x_axis], df[y_axis], color=color)
            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)
            ax.tick_params(axis='x', rotation=45)
            if show_grid:
                ax.grid(True, linestyle=':', alpha=0.7)
            plt.tight_layout()
            st.pyplot(fig)
            st.balloons()
    
    elif graph_type == "Pie Chart":
        labels_col = st.selectbox("Labels column", options=columns)
        values_col = st.selectbox("Values column", options=columns)
        
        if st.button("Plot Pie Chart"):
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(df[values_col], labels=df[labels_col], autopct='%1.1f%%', colors=[color, '#ff7f0e', '#2ca02c', '#d62728'])
            ax.set_title(f"Pie Chart: {values_col}")
            st.pyplot(fig)
            st.balloons()
    
    elif graph_type == "Histogram":
        col = st.selectbox("Column for Histogram", options=columns)
        bins = st.number_input("Number of Bins", min_value=5, max_value=50, value=10)
        
        if st.button("Plot Histogram"):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(df[col], bins=bins, color=color, edgecolor='black')
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")
            if show_grid:
                ax.grid(True, linestyle=':', alpha=0.7)
            st.pyplot(fig)
            st.balloons()
    
    elif graph_type == "Line Graph":
        x_axis = st.selectbox("Horizontal axis (X-axis)", options=columns)
        y_axis = st.selectbox("Vertical axis (Y-axis)", options=columns)
        line_style = st.selectbox("Line Style", ["Solid", "Dashed", "Dotted"])
        marker_style = st.selectbox("Marker Style", ["None", "Circle", "Square", "Triangle Up", "Triangle Down", "Diamond"])
        
        if st.button("Plot Line Graph"):
            fig, ax = plt.subplots(figsize=(10, 6))
            linestyle_map = {"Solid": '-', "Dashed": '--', "Dotted": ':'}
            marker_map = {"None": None, "Circle": 'o', "Square": 's', "Triangle Up": '^', "Triangle Down": 'v', "Diamond": 'D'}
            
            ax.plot(df[x_axis], df[y_axis], color=color, linestyle=linestyle_map[line_style], marker=marker_map[marker_style])
            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)
            ax.tick_params(axis='x', rotation=45)
            if show_grid:
                ax.grid(True, linestyle=':', alpha=0.7)
            plt.tight_layout()
            st.pyplot(fig)
            st.balloons()
    
    elif graph_type == "Scatter Plot":
        x_axis = st.selectbox("Horizontal axis (X-axis)", options=columns)
        y_axis = st.selectbox("Vertical axis (Y-axis)", options=columns)
        marker_style = st.selectbox("Marker Style", ["Circle", "Square", "Triangle Up", "Triangle Down", "Diamond"])
        
        if st.button("Plot Scatter Plot"):
            fig, ax = plt.subplots(figsize=(10, 6))
            marker_map = {"Circle": 'o', "Square": 's', "Triangle Up": '^', "Triangle Down": 'v', "Diamond": 'D'}
            
            ax.scatter(df[x_axis], df[y_axis], color=color, marker=marker_map[marker_style])
            ax.set_xlabel(x_axis)
            ax.set_ylabel(y_axis)
            ax.tick_params(axis='x', rotation=45)
            if show_grid:
                ax.grid(True, linestyle=':', alpha=0.7)
            st.pyplot(fig)
            st.balloons()

else:
    st.info("Upload a JSON, CSV, or Excel file to start creating graphs!")

# Bottom watermark (blue, transparent)
st.markdown("""
<style>
  .bottom-watermark {
    position: fixed;
    bottom: 15px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 14px;
    font-weight: 500;
    color: #1e90ff;
    background: transparent;
    padding: 5px 15px;
    border-radius: 8px;
    z-index: 5;
    pointer-events: none;
    user-select: none;
    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
  }
</style>

<div class="bottom-watermark">
  🌸 Crafted with love by Nilay Chauhan 🌸
</div>
""", unsafe_allow_html=True)