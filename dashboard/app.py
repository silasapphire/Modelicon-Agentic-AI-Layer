import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from sqlalchemy import text

from pipeline_src.database.connection import DatabaseConnection
from dashboard.agent_bridge import (
    ask_agent,
    new_session,
    get_history,
    list_chat_sessions,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Data Platform",
    page_icon="🤖",
    layout="wide"
)

# Hide the default Streamlit sidebar completely
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="collapsedControl"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE HELPER
# ============================================================

def run_query(query):
    """
    Run a SQL query and return the result as a Pandas DataFrame.
    """

    database = DatabaseConnection()
    engine = database.get_engine()

    data = pd.read_sql(
        text(query),
        engine
    )

    database.close()

    return data


# ============================================================
# SESSION STATE
# ============================================================

# Session state remembers which screen is currently open.

if "page" not in st.session_state:
    st.session_state.page = "chat"

if "domain" not in st.session_state:
    st.session_state.domain = "HVAC"

if "session_id" not in st.session_state:
    st.session_state.session_id = None


# ============================================================
# TOP NAVIGATION
# ============================================================

logo_path = PROJECT_ROOT / "logo.jpeg"

if logo_path.exists():
    st.image(str(logo_path), width=180)

nav_left, nav1, nav2 = st.columns(
    [4, 2, 2]
)

with nav_left:
    st.markdown("### Digital Twin Platform")

with nav1:
    analytics_button = st.button(
        "📊 Analytics",
        use_container_width=True
    )

with nav2:
    upload_button = st.button(
        "⬆ Upload Data",
        use_container_width=True
    )


# Change page when top buttons are clicked

if analytics_button:
    st.session_state.page = "analytics"

if upload_button:
    st.session_state.page = "upload"


st.divider()


# ============================================================
# MAIN LAYOUT - THREE COLUMNS
# ============================================================

left_panel, center_panel, right_panel = st.columns(
    [2, 6, 2]
)


# ============================================================
# LEFT PANEL - LOGO + DIGITAL TWIN MENU
# ============================================================

with left_panel:

    if st.button(
        "Digital Twin",
        use_container_width=True,
        type="secondary"
    ):
        st.session_state.domain = "Digital Twin"

    st.button(
        "Building Systems",
        use_container_width=True
    )

    st.button(
        "Adsorption",
        use_container_width=True
    )

    st.button(
        "Nuclear Power",
        use_container_width=True
    )


# ============================================================
# RIGHT PANEL - CHAT HISTORY (moved from sidebar)
# ============================================================

with right_panel:

    if st.button(
        "＋ New Chat",
        use_container_width=True
    ):
        st.session_state.session_id = None
        st.session_state.page = "chat"
        st.session_state.domain = "HVAC"

    st.divider()

    st.markdown("### Chat History")

    for past_chat in list_chat_sessions():

        if st.button(
            past_chat["title"],
            use_container_width=True,
            key=f"history_{past_chat['session_id']}"
        ):
            st.session_state.session_id = past_chat["session_id"]
            st.session_state.page = "chat"
            st.session_state.domain = "HVAC"


# ============================================================
# CENTER PANEL - MAIN CONTENT
# ============================================================

with center_panel:

    # --------------------------------------------------------
    # DIGITAL TWIN PLACEHOLDER
    # --------------------------------------------------------

    if st.session_state.domain == "Digital Twin":

        st.markdown("### Digital Twin")

        st.info(
            "Digital Twin is currently a demo module."
        )

        st.write(
            "Future Digital Twin functionality will appear here."
        )

    # --------------------------------------------------------
    # CHAT / QUERY PAGE
    # --------------------------------------------------------

    elif st.session_state.page == "chat":

        st.markdown("### Ask anything")

        # Show the real conversation so far for this session
        if st.session_state.session_id:

            for past_message in get_history(st.session_state.session_id):

                with st.chat_message(past_message["role"]):

                    st.write(past_message["content"])

        query = st.chat_input(
            "Ask a question about your data..."
        )

        if query:

            if not st.session_state.session_id:
                st.session_state.session_id = new_session()

            # Show user's message
            with st.chat_message("user"):

                st.write(query)

            # Real AI response, routed through the agentic ai layer
            with st.chat_message("assistant"):

                with st.spinner("Thinking..."):
                    response = ask_agent(query, st.session_state.session_id)

                st.write(response)

    # --------------------------------------------------------
    # ANALYTICS PAGE
    # --------------------------------------------------------

    elif st.session_state.page == "analytics":

        st.markdown("### HVAC Data Analytics")

        st.write(
            "This section demonstrates the structured-data "
            "pipeline built using PostgreSQL."
        )

        # ----------------------------------------------------
        # PIPELINE OVERVIEW
        # ----------------------------------------------------

        st.markdown("#### Data Pipeline")

        st.code(
            """
RAW DATA
   ↓
BRONZE
   ↓
DATA QUALITY
   ↓
SILVER
   ↓
GOLD
            """
        )

        # ----------------------------------------------------
        # DATA LAYER SELECTOR
        # ----------------------------------------------------

        layer = st.selectbox(
            "Select Data Layer",
            [
                "Raw Features",
                "Raw Targets",
                "Bronze Features",
                "Bronze Targets",
                "Silver",
                "Gold"
            ]
        )

        table_map = {

            "Raw Features":
                "hvac_features",

            "Raw Targets":
                "hvac_targets",

            "Bronze Features":
                "bronze_hvac_features",

            "Bronze Targets":
                "bronze_hvac_targets",

            "Silver":
                "silver_hvac",

            "Gold":
                "gold_hvac"
        }

        table_name = table_map[layer]

        # ----------------------------------------------------
        # GET TABLE INFORMATION
        # ----------------------------------------------------

        count_query = f"""
        SELECT COUNT(*) AS row_count
        FROM {table_name}
        """

        row_count = run_query(
            count_query
        )["row_count"][0]

        preview_query = f"""
        SELECT *
        FROM {table_name}
        LIMIT 100
        """

        preview = run_query(
            preview_query
        )

        # ----------------------------------------------------
        # DISPLAY METRICS
        # ----------------------------------------------------

        metric1, metric2 = st.columns(2)

        metric1.metric(
            "Total Rows",
            f"{row_count:,}"
        )

        metric2.metric(
            "Total Columns",
            len(preview.columns)
        )

        # ----------------------------------------------------
        # DISPLAY DATA
        # ----------------------------------------------------

        st.markdown(
            f"#### {layer} Data Preview"
        )

        st.dataframe(
            preview,
            use_container_width=True
        )

    # --------------------------------------------------------
    # UPLOAD PAGE
    # --------------------------------------------------------

    elif st.session_state.page == "upload":

        st.markdown("### Upload Structured Data")

        st.write(
            "Upload new structured data for ingestion "
            "into the data platform."
        )

        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"]
        )

        if uploaded_file is not None:

            data = pd.read_csv(
                uploaded_file
            )

            st.success(
                "File uploaded successfully."
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "Rows",
                len(data)
            )

            col2.metric(
                "Columns",
                len(data.columns)
            )

            st.markdown("#### Data Preview")

            st.dataframe(
                data.head(100),
                use_container_width=True
            )

            st.info(
                "This is currently a demo upload. "
                "Database ingestion rules will be added later."
            )