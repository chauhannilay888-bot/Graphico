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
    layout="wide"
)

# ---------------- DATA LOADING FUNCTION ----------------
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
        st.error(f"File Load Error: {e}")
        return None

# ---------------- SIDEBAR NAVIGATION ----------------
st.sidebar.title("🚀 Graphico Pro Menu")
page = st.sidebar.radio("Go to:", ["Home & Visualizer", "Raw Insights"])

st.sidebar.divider()

# ---------------- FILE UPLOADER ----------------
uploaded_file = st.sidebar.file_uploader("Upload dataset", type=["csv", "xlsx", "xls", "json"])
df = None

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    df = load_data(uploaded_file, ext)
    if df is not None:
        st.sidebar.success("Data Loaded!")
    else:
        st.stop()

# ---------------- MAIN LOGIC ----------------

if df is not None:
    # COMMON DATA INFO (Available on both pages)
    num_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()

    # --- PAGE 1: VISUALIZER ---
    if page == "Home & Visualizer":
        st.title("📊 Data Visualizer")
        
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Rows", df.shape[0])
        c2.metric("Total Columns", df.shape[1])
        c3.metric("Total Missing Cells", int(df.isnull().sum().sum()))

        st.divider()
        
        # Filter Section
        st.subheader("🔍 Filter Data")
        f_col = st.selectbox("Select column to filter", all_cols)
        u_vals = df[f_col].dropna().unique().tolist()
        s_vals = st.multiselect("Select Values", u_vals, default=u_vals)
        df_filtered = df[df[f_col].isin(s_vals)]

        # Graph Settings
        st.sidebar.subheader("🎨 Graph Settings")
        g_type = st.sidebar.selectbox("Chart type", ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"])
        chart_title = st.sidebar.text_input("Chart Title", "My Analysis Chart")
        
        x_ax = st.sidebar.selectbox("X Axis", all_cols)
        y_ax = st.sidebar.selectbox("Y Axis", num_cols) if len(num_cols) > 0 else None

        if g_type == "Auto Suggestion":
            g_type = "Scatter" if len(num_cols) >= 2 else "Bar"
            st.sidebar.info(f"Suggested: {g_type}")

        # Plotting
        fig = None
        try:
            if g_type == "Heatmap":
                corr = df_filtered.corr(numeric_only=True)
                if not corr.empty:
                    fig = px.imshow(corr, text_auto=True, title="Heatmap")
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
            st.error(f"Chart Error: {e}")

        # Download
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Filtered Data", csv, "filtered_data.csv", "text/csv")

    # --- PAGE 2: RAW INSIGHTS ---
    elif page == "Raw Insights":
        st.title("🧠 Technical Data Insights")
        
        st.subheader("Raw Data Preview")
        st.dataframe(df)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Descriptive Statistics")
            st.write(df.describe())
            
            st.subheader("📏 Data Shape")
            st.write(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")

        with col2:
            st.subheader("🛠️ Column Data Types")
            # Converter into dataframe for better display
            dtype_df = pd.DataFrame(df.dtypes, columns=["Data Type"]).astype(str)
            st.dataframe(dtype_df)

        st.divider()
        
        st.subheader("❌ Missing Values Analysis")
        m_col1, m_col2 = st.columns(2)
        
        with m_col1:
            st.write("Missing Value Map (True = Missing)")
            st.dataframe(df.isnull())
            
        with m_col2:
            st.write("Count of Missing Values per Column")
            st.dataframe(df.isnull().sum())

else:
    # Welcome Screen
    st.title("Welcome to Graphico Pro! 📊")
    st.info("Side menu se apni CSV ya Excel file upload karein aur magic dekhein!")
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&q=80&w=1000", caption="Turn Data into Insights")
