import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import plotly.express as px
import os
from PIL import Image

# --------- 1. GOOGLE ANALYTICS & SEARCH CONSOLE VERIFICATION -----------
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-FHN9KEP6KN"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-FHN9KEP6KN');
</script>
<meta name="google-site-verification" content="zINnwjOarj-lAgHmEFrOPaihJvA5iwrmzhapCKGuqj0" />
<link rel="canonical" href="https://graphico.streamlit.app" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="css"]  {
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
    page_title="Graphico Pro | AI-Powered Data Tool",
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
    page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights & Cleaning", "📖 Samples"], index=0)
    
    uploaded_file = st.file_uploader("Upload Dataset (CSV, Excel, JSON)", type=["csv", "xlsx", "xls", "json"])
    
    df = None
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        df = load_data(uploaded_file, ext)
        if df is not None:
            st.success("✅ Dataset Loaded!")
    st.info("Developed with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------
if df is not None:
    # --- DATA CLEANING LOGIC (Applied globally if user chooses) ---
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include="number").columns.tolist()

    if page == "🏠 Home & Visualizer":
        st.markdown("<h2 style='color: #4facfe;'>📊 Professional Data Visualizer</h2>", unsafe_allow_html=True)
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("📈 Rows", df.shape[0])
        m2.metric("📋 Columns", df.shape[1])
        m3.metric("⚠️ Missing Cells", int(df.isnull().sum().sum()))

        st.divider()

        # Sidebar for Graph Settings
        st.sidebar.header("🎨 Graph Settings")
        g_type = st.sidebar.selectbox("Chart Type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
        chart_title = st.sidebar.text_input("Chart Title", "My Analysis")
        x_ax = st.sidebar.selectbox("X-Axis", all_cols)
        y_ax = st.sidebar.selectbox("Y-Axis (Numeric)", num_cols) if num_cols else None

        # Filter Section with SELECT ALL
        st.subheader("🔍 Filter Data")
        f_col = st.selectbox("Select column to filter", all_cols)
        u_vals = df[f_col].dropna().unique().tolist()
        
        col_all, col_multi = st.columns([1, 4])
        with col_all:
            select_all = st.checkbox("Select All")
        
        if select_all:
            s_vals = u_vals
            st.multiselect("Values", u_vals, default=u_vals, disabled=True)
        else:
            s_vals = st.multiselect("Select Values", u_vals, default=u_vals[:5] if len(u_vals)>5 else u_vals)
        
        df_filtered = df[df[f_col].isin(s_vals)]

        # Plotting logic... (same as before)
        if g_type == "Auto Suggestion":
            g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
        
        try:
            fig = None
            if g_type == "Bar": fig = px.bar(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Line": fig = px.line(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Scatter": fig = px.scatter(df_filtered, x=x_ax, y=y_ax, title=chart_title)
            elif g_type == "Pie": fig = px.pie(df_filtered, names=x_ax, values=y_ax, title=chart_title)
            elif g_type == "Histogram": fig = px.histogram(df_filtered, x=y_ax, title=chart_title)
            elif g_type == "Heatmap":
                corr = df_filtered.corr(numeric_only=True)
                if not corr.empty: fig = px.imshow(corr, text_auto=True)
            
            if fig: st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

    elif page == "🔍 Raw Insights & Cleaning":
        st.markdown("<h2 style='color: #00f2fe;'>🧠 Data Studio & Cleaning</h2>", unsafe_allow_html=True)
        
        # --- CLEANING TOOLS ---
        st.subheader("🛠️ Quick Clean Actions")
        c1, c2, c3 = st.columns(3)
        
        if c1.button("Drop Missing Columns"):
            df = df.dropna(axis=1, how='all')
            st.rerun()
            
        if c2.button("Fill Numeric with Mean"):
            for col in num_cols:
                df[col] = df[col].fillna(df[col].mean())
            st.success("Mean Imputation Done!")
            st.rerun()

        custom_val = st.text_input("Fill ALL missing values with custom text/number:")
        if st.button("Apply Custom Fill"):
            df = df.fillna(custom_val)
            st.rerun()

        st.divider()
        st.subheader("Data Preview")
        st.dataframe(df, use_container_width=True)

    elif page == "📖 Samples":
        st.title("Tutorial & Samples")
        if os.path.exists("Tutorial.mp4"):
            st.video("Tutorial.mp4")
        
        folder = "tutorial_PNGs"
        if os.path.exists(folder):
            files = [f for f in os.listdir(folder) if f.endswith((".png", ".jpg"))]
            for i in range(0, len(files), 4):
                cols = st.columns(4)
                for j, col in enumerate(cols):
                    if i+j < len(files):
                        col.image(Image.open(os.path.join(folder, files[i+j])), use_container_width=True)

else:
    st.markdown("<div style='text-align: center; padding: 50px;'><h1 style='color: #4facfe;'>💎 Graphico Pro</h1><p>Upload a dataset to start</p></div>", unsafe_allow_html=True)

# Sitemap Generator
if st.query_params.get("sitemap") == "true":
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://graphico.streamlit.app</loc><lastmod>2026-03-28</lastmod><priority>1.0</priority></url>
</urlset>"""
    st.text(sitemap_xml)
    st.stop()
