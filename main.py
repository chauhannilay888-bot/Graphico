import streamlit as st
import streamlit.components.v1 as components
import io
import pandas as pd
import plotly.express as px

# --------- 1. GOOGLE ANALYTICS & CUSTOM CSS (FOR FONTS & STYLING) -----------
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
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    .main {
        background-color: #0e1117;
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

# ---------------- 2. PAGE CONFIG & THEME ----------------
st.set_page_config(
    page_title="Graphico Pro | AI-Powered Data Tool",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme for Plotly
px.defaults.template = "plotly_dark"
px.defaults.color_continuous_scale = px.colors.sequential.Viridis

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

# ---------------- 4. SIDEBAR NAVIGATION & BRANDING ----------------
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #4facfe;'>💎 GRAPHICO PRO</h1>", unsafe_content_type=True)
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>Empowering Your Data Journey</p>", unsafe_content_type=True)
    st.divider()
    
    page = st.radio("✨ Navigation", ["🏠 Home & Visualizer", "🔍 Raw Insights"], index=0)
    st.divider()
    
    st.subheader("📥 Upload Dataset")
    uploaded_file = st.file_uploader("Drop your file here", type=["csv", "xlsx", "xls", "json"])
    
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        df = load_data(uploaded_file, ext)
        if df is not None:
            st.sidebar.success("✅ System Ready!")
        else:
            st.stop()
    else:
        df = None

    st.divider()
    st.info("Developed with ❤️ by Nilay")

# ---------------- 5. MAIN LOGIC ----------------

if df is not None:
    all_cols = df.columns.tolist()
    num_cols = df.select_dtypes(include="number").columns.tolist()

    if page == "🏠 Home & Visualizer":
        # Professional Header with Gradient Style (Via Markdown)
        st.markdown("""
            <h2 style='color: #4facfe;'>📊 Professional Data Visualizer</h2>
            <hr style='margin-top: 0; margin-bottom: 20px; border: 0; height: 1px; background-image: linear-gradient(to right, #4facfe, #00f2fe, transparent);'>
            """, unsafe_content_type=True)
        
        # --- METRICS SECTION ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📈 Rows", df.shape[0])
        m2.metric("📋 Columns", df.shape[1])
        m3.metric("⚠️ Missing Cells", int(df.isnull().sum().sum()))
        m4.metric("⚙️ Data Types", len(df.dtypes.unique()))

        # --- FILTER & PLOT SECTION ---
        col_main, col_side = st.columns([3, 1])

        with col_side:
            st.markdown("### 🛠️ Configuration")
            f_col = st.selectbox("🎯 Filter Column", all_cols)
            u_vals = df[f_col].dropna().unique().tolist()
            s_vals = st.multiselect("Filter Values", u_vals, default=u_vals[:5] if len(u_vals)>5 else u_vals)
            df_filtered = df[df[f_col].isin(s_vals)]

            st.divider()
            g_type = st.selectbox("📈 Chart Type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
            chart_title = st.text_input("📝 Title", "Custom Data Analysis")
            x_ax = st.selectbox("📏 X-Axis", all_cols)
            y_ax = st.selectbox("📏 Y-Axis", num_cols) if num_cols else None

        with col_main:
            # Auto Suggestion Logic
            if g_type == "Auto Suggestion":
                g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
                st.caption(f"✨ AI Insight: Based on your data, we suggest a **{g_type} Chart**.")

            fig = None
            try:
                with st.spinner("Generating beautiful chart..."):
                    if g_type == "Heatmap":
                        corr = df_filtered.corr(numeric_only=True)
                        if not corr.empty:
                            fig = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r')
                    elif y_ax:
                        chart_map = {
                            "Bar": px.bar, "Line": px.line, "Scatter": px.scatter,
                            "Pie": px.pie, "Histogram": px.histogram, "Box": px.box, "Area": px.area
                        }
                        if g_type == "Pie":
                            fig = chart_map[g_type](df_filtered, names=x_ax, values=y_ax, title=chart_title)
                        else:
                            fig = chart_map[g_type](df_filtered, x=x_ax, y=y_ax, title=chart_title, template="plotly_dark")
                    
                    if fig:
                        fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), hovermode="x unified")
                        st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Visualization Error: {e}")

            # DOWNLOAD SECTION
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Filtered Data (CSV)", csv, "graphico_report.csv", "text/csv")

    elif page == "🔍 Raw Insights":
        st.markdown("<h2 style='color: #00f2fe;'>🧠 Technical Deep-Dive</h2>", unsafe_content_type=True)
        
        with st.expander("📂 View Full Dataset", expanded=True):
            st.dataframe(df, use_container_width=True)

        i_col1, i_col2 = st.columns(2)
        with i_col1:
            st.markdown("#### 📊 Statistics Summary")
            st.table(df.describe().T) # Transposed for better reading
        
        with i_col2:
            st.markdown("#### 🛠️ Metadata")
            dtype_df = pd.DataFrame(df.dtypes, columns=["Type"]).astype(str)
            st.dataframe(dtype_df, use_container_width=True)

        st.divider()
        st.markdown("#### ❌ Null Value Heatmap (Quality Check)")
        st.dataframe(df.isnull().sum().to_frame(name="Missing Count"), use_container_width=True)

else:
    # --- STYLISH WELCOME SCREEN ---
    st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h1 style='font-size: 3.5em; color: #4facfe;'>💎 Graphico Pro</h1>
            <p style='font-size: 1.2em; color: #a1a1a1;'>The future of Data Visualization is here.</p>
            <br>
            <div style='background-color: #1e2130; padding: 20px; border-radius: 15px; border: 1px solid #4facfe;'>
                <p>👈 <b>Start by uploading your dataset in the sidebar.</b></p>
                <p style='font-size: 0.9em;'>Supports CSV, Excel (XLSX), and JSON formats.</p>
            </div>
        </div>
        """, unsafe_content_type=True)
    st.image("https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&q=80&w=1200", use_container_width=True)
