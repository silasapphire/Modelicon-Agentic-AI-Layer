import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from sqlalchemy import text

from src.database.connection import DatabaseConnection


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
        st.session_state.page = "chat"
        st.session_state.domain = "HVAC"

    st.divider()

    st.markdown("### Chat History")

    st.button(
        "HVAC Temperature Analysis",
        use_container_width=True
    )

    st.button(
        "Fault Analysis",
        use_container_width=True
    )

    st.button(
        "Energy Performance",
        use_container_width=True
    )


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

        query = st.chat_input(
            "Ask a question about your data..."
        )

        if query:

            # Show user's message
            with st.chat_message("user"):

                st.write(query)

            # Dummy AI response
            with st.chat_message("assistant"):

                st.write(
                    "This is a demo response."
                )

                st.write(
                    "The Agent KI / AI API will be connected "
                    "to this query interface in the next phase."
                )

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