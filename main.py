import streamlit as st
import pandas as pd
import time
import plotly.express as px
import os
import json
from PIL import Image

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Graphico Pro", layout="wide")

# ---------------- SESSION STATE ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'page' not in st.session_state:
    st.session_state.page = "login"

# ---------------- USER DATABASE ----------------
USER_DB = r"C:\Users\chauh\OneDrive\Desktop\Graphico Pro\User_Data.json"

# Load user data
if os.path.exists(USER_DB):
    with open(USER_DB, 'r') as f:
        data_list = json.load(f)
    data = pd.DataFrame(data_list)
else:
    data = pd.DataFrame(columns=["Username", "E-Mail", "GApassword"])
    with open(USER_DB, 'w') as f:
        json.dump([], f, indent=4)

# ---------------- LOGIN PAGE ----------------
if st.session_state.page == "login" and not st.session_state.logged_in:
    st.title("Login To Your Graphico Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')

    if username and password:
        if st.button("Login"):
            match = data[(data['Username'] == username) & (data['GApassword'] == password)]
            if not match.empty:
                st.success("LOGGED IN SUCCESSFULLY! ")
                st.info("Redirecting to the app")
                time.sleep(2)
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("No Account Found! ")

    if st.button("New User? Create Account!"):
        st.session_state.page = "signup"
        st.rerun()

# ---------------- SIGNUP PAGE ----------------
if st.session_state.page == "signup":
    st.title("WELCOME USER! ")
    name = st.text_input("Username")
    key1 = st.text_input("Set an all-time Graphico Password ")
    key_conf = st.text_input("Conform Password ")
    fill = (name and key1 and key_conf)

    if fill:
        if st.button("Create Account"):
            if name in data["Username"].values:
                st.error("Username already taken ")
            elif key_conf != key1:
                st.error("Password should match! ")
            elif key_conf in data["GApassword"].values:
                st.error("Password already taken")
            else:
                new_user = {"Username": name, "GApassword": key_conf}
                data_list = data.to_dict('records')
                data_list.append(new_user)
                with open(USER_DB, 'w') as f:
                    json.dump(data_list, f, indent=4)
                st.success("Account created successfully! "); time.sleep(2)
                st.session_state.page = "login"
                st.rerun()

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ---------------- MAIN APP ----------------
if st.session_state.logged_in:
    st.sidebar.button("Logout", on_click=lambda: [
        st.session_state.update(logged_in=False, current_user=None, page="login"),
        st.rerun()
    ])

    # ---------------- CUSTOM CSS ----------------
    st.markdown("""
    <style>
    body { background: #0f172a; }
    .block-container { padding-top: 2rem; }
    .card { background: rgba(255,255,255,0.06); padding: 25px; border-radius: 12px;
    backdrop-filter: blur(12px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); margin-bottom:20px; }
    .title { font-size:28px; font-weight:bold;
    background: linear-gradient(90deg,#6366f1,#06b6d4);
    -webkit-background-clip:text; color:transparent; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title">Graphico Pro 📊</div>', unsafe_allow_html=True)
    st.title(f"Welcome {st.session_state.current_user}! ")
    st.subheader("What's your mind today? ")
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

    uploaded_file = st.file_uploader(
        "Upload dataset", type=["csv", "xlsx", "xls", "json"]
    )

    df = None
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        try:
            df = load_data(uploaded_file, ext)
            st.success("Dataset loaded successfully")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Error loading file: {e}")
            st.stop()

    # ---------------- DATA INSIGHTS ----------------
    if df is not None:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Rows", df.shape[0])
        with col2: st.metric("Columns", df.shape[1])
        with col3: st.metric("Missing values", int(df.isnull().sum().sum()))

    # ---------------- FILTER DATA ----------------
    if df is not None:
        st.subheader("Filter Data")
        filter_col = st.selectbox("Select column to filter", df.columns)
        unique_vals = df[filter_col].dropna().unique()
        selected_vals = st.multiselect("Values", unique_vals, default=unique_vals)
        df = df[df[filter_col].isin(selected_vals)]

    # ---------------- GRAPH SETTINGS ----------------
    if df is not None:
        st.sidebar.header("Graph Settings")
        graph_type = st.sidebar.selectbox(
            "Chart type",
            ["Auto Suggestion","Bar","Line","Scatter","Pie","Histogram","Box","Area","Heatmap"]
        )
        title = st.sidebar.text_input("Chart Title", "My Chart")
        numeric_cols = df.select_dtypes(include="number").columns
        columns = df.columns
        x_axis = st.sidebar.selectbox("X Axis", columns)
        y_axis = None
        if len(numeric_cols) > 0:
            y_axis = st.sidebar.selectbox("Y Axis", numeric_cols)
        else:
            st.warning("No numeric columns available for Y axis.")
        
        if st.sidebar.button("HISTORY"):
            base_folder = r"C:\Users\chauh\OneDrive\Desktop\Graphico Pro\USER HISTORY"
            main_folder = st.session_state.current_user
            history_folder = os.path.join(base_folder, main_folder)
            if not os.listdir(history_folder):
                st.info("No History Yet")
            else:
                png_files = [f for f in os.listdir(history_folder) if f.endswith(".png")]
                st.title("Your History")
                cols = st.columns(4)
                for idx, file in enumerate(png_files):
                    img_path = os.path.join(history_folder, file)
                    image = Image.open(img_path)
                    with cols[idx % 4]:
                        st.image(image, caption=file, use_container_width=True)

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
        if graph_type != "Heatmap" and y_axis is not None:
            if graph_type == "Bar": fig = px.bar(df, x=x_axis, y=y_axis, title=title)
            elif graph_type == "Line": fig = px.line(df, x=x_axis, y=y_axis, title=title)
            elif graph_type == "Scatter": fig = px.scatter(df, x=x_axis, y=y_axis, title=title)
            elif graph_type == "Pie": fig = px.pie(df, names=x_axis, values=y_axis, title=title)
            elif graph_type == "Histogram": fig = px.histogram(df, x=y_axis, title=title)
            elif graph_type == "Box": fig = px.box(df, x=x_axis, y=y_axis, title=title)
            elif graph_type == "Area": fig = px.area(df, x=x_axis, y=y_axis, title=title)

        if graph_type == "Heatmap":
            corr = df.corr(numeric_only=True)
            if not corr.empty:
                fig = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
            else:
                st.warning("No numeric data available for heatmap.")

    # ---------------- DISPLAY CHART ----------------
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            base_path = r"C:\Users\chauh\OneDrive\Desktop\Graphico Pro\USER HISTORY"
            folder_name = st.session_state.current_user
            folder_path = os.path.join(base_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, title + ".png")
            fig.write_image(file_path)

    # ---------------- DOWNLOAD DATA ----------------
        if df is not None:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download filtered data", csv, "filtered_data.csv", "text/csv")
