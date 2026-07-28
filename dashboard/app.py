import sys
import uuid
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import text


try:
    from src.database.connection import DatabaseConnection
    HAS_REAL_DB = True
except ImportError:
    HAS_REAL_DB = False

try:
    from database.building.hvac_twin import simulate_hours
    HAS_REAL_TWIN = True
except ImportError:
    HAS_REAL_TWIN = False

try:
    from dashboard.agent_bridge import (
        ask_agent,
        new_session,
        get_history,
        list_chat_sessions,
    )
    HAS_REAL_AGENT = True
except ImportError:
    HAS_REAL_AGENT = False



def delete_chat_session(session_id: str) -> bool:
    """
    Delete a chat session and its messages from the memory database.

    Returns True if deleted, False if the memory layer doesn't support
    deletion yet (i.e. no delete_session() function exists in
    database/memory/memory_queries.py), or if running in mock mode.
    """
    if not HAS_REAL_AGENT:
        if session_id in st.session_state.mock_chats:
            del st.session_state.mock_chats[session_id]
            return True
        return False

    try:
        from database.memory.memory_queries import delete_session
    except ImportError:
        return False

    delete_session(session_id)
    return True



if "mock_chats" not in st.session_state:
    # session_id -> {"title": str, "messages": [{"role","content"}, ...]}
    st.session_state.mock_chats = {}


def mock_new_session() -> str:
    session_id = str(uuid.uuid4())
    st.session_state.mock_chats[session_id] = {
        "title": None,
        "messages": [],
    }
    return session_id


def mock_get_history(session_id: str) -> list[dict]:
    chat = st.session_state.mock_chats.get(session_id)
    return chat["messages"] if chat else []


def mock_list_chat_sessions(limit: int = 10) -> list[dict]:
    chats = []
    for session_id, chat in reversed(list(st.session_state.mock_chats.items())):
        if not chat["title"]:
            continue
        chats.append({"session_id": session_id, "title": chat["title"]})
        if len(chats) >= limit:
            break
    return chats


def mock_ask_agent(user_request: str, session_id: str) -> str:
    chat = st.session_state.mock_chats.setdefault(
        session_id, {"title": None, "messages": []}
    )

    if not chat["title"]:
        title = user_request.strip()
        if len(title) > 40:
            title = title[:37] + "..."
        chat["title"] = title

    response = (
        "[UI preview mode — her real agent isn't connected yet] "
        "This is a placeholder response so the chat layout can be "
        "tested. Once database/ and graph/ are pulled in, real "
        "answers will appear here automatically."
    )

    chat["messages"].append({"role": "user", "content": user_request})
    chat["messages"].append({"role": "assistant", "content": response})

    return response


def mock_simulate_hours(hours, dt_minutes, target_temp_c, initial_temp_c):
    """
    Simple placeholder trend (not real physics) just so the Digital
    Twin chart and metrics have something to render in UI preview mode.
    """
    steps = int((hours * 60) / dt_minutes)
    now = datetime.now()
    room_temp = initial_temp_c

    for i in range(steps):
        timestamp = now + timedelta(minutes=i * dt_minutes)
        outside_temp = 28 + 4 * math.sin(i / steps * 2 * math.pi)

        # drift room temperature toward the setpoint
        room_temp += (target_temp_c - room_temp) * 0.05
        room_temp += random.uniform(-0.15, 0.15)

        error = target_temp_c - room_temp
        hvac_power_w = max(-3000, min(3000, error * 800))

        if hvac_power_w > 100:
            hvac_status = "HEATING"
        elif hvac_power_w < -100:
            hvac_status = "COOLING"
        else:
            hvac_status = "OFF"

        yield {
            "timestamp": timestamp,
            "room_temp_c": room_temp,
            "outside_temp_c": outside_temp,
            "hvac_power_w": hvac_power_w,
            "hvac_status": hvac_status,
        }


# Wire up whichever implementation is actually available.

if not HAS_REAL_AGENT:
    new_session = mock_new_session
    get_history = mock_get_history
    list_chat_sessions = mock_list_chat_sessions
    ask_agent = mock_ask_agent

if not HAS_REAL_TWIN:
    simulate_hours = mock_simulate_hours


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

def mock_run_query(query):
    """
    Placeholder data for UI preview mode, used only when her real
    DatabaseConnection isn't available. Mimics the shape of a COUNT
    query and a SELECT * ... LIMIT preview query so the Analytics page
    still renders.
    """
    normalized = query.strip().upper()

    if normalized.startswith("SELECT COUNT"):
        return pd.DataFrame({"row_count": [random.randint(500, 5000)]})

    rows = []
    now = datetime.now()

    for i in range(25):
        rows.append({
            "id": i + 1,
            "room": f"Room {random.randint(1, 8)}",
            "floor": random.randint(1, 3),
            "temperature_c": round(random.uniform(18.0, 28.0), 1),
            "humidity_pct": round(random.uniform(30.0, 60.0), 1),
            "timestamp": now - timedelta(minutes=15 * i),
        })

    return pd.DataFrame(rows)


def run_query(query):
    """
    Run a SQL query and return the result as a Pandas DataFrame.

    Falls back to mock_run_query() when her real DatabaseConnection
    (src/database/connection.py) isn't available in this environment,
    so the Analytics page still renders during UI-only work.
    """

    if not HAS_REAL_DB:
        return mock_run_query(query)

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

if not (HAS_REAL_DB and HAS_REAL_TWIN and HAS_REAL_AGENT):
    missing = []
    if not HAS_REAL_DB:
        missing.append("database connection")
    if not HAS_REAL_TWIN:
        missing.append("digital twin simulation")
    if not HAS_REAL_AGENT:
        missing.append("chat agent")

    st.caption(
        "🧪 UI preview mode — using placeholder data for: "
        + ", ".join(missing)
        + ". This will switch to her real logic automatically once "
        "those files are pulled in."
    )


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

        history_row, delete_row = st.columns(
            [5, 1]
        )

        with history_row:

            if st.button(
                past_chat["title"],
                use_container_width=True,
                key=f"history_{past_chat['session_id']}"
            ):
                st.session_state.session_id = past_chat["session_id"]
                st.session_state.page = "chat"
                st.session_state.domain = "HVAC"

        with delete_row:

            if st.button(
                "🗑",
                key=f"delete_{past_chat['session_id']}",
                help="Delete this chat"
            ):

                deleted = delete_chat_session(past_chat["session_id"])

                if deleted:

                    # If the chat being deleted is the one currently
                    # open, fall back to a fresh chat.
                    if st.session_state.session_id == past_chat["session_id"]:
                        st.session_state.session_id = None
                        st.session_state.page = "chat"
                        st.session_state.domain = "HVAC"

                    st.rerun()

                else:

                    st.error(
                        "Delete isn't wired up in the memory layer yet "
                        "(add a delete_session() function to "
                        "database/memory/memory_queries.py)."
                    )


# ============================================================
# CENTER PANEL - MAIN CONTENT
# ============================================================

with center_panel:

    # --------------------------------------------------------
    # DIGITAL TWIN
    # --------------------------------------------------------

    if st.session_state.domain == "Digital Twin":

        st.markdown("### Digital Twin")

        st.write(
            "Physics-based room + HVAC simulation (thermal resistance/capacitance "
            "model) projected over a 24-hour cycle."
        )

        control1, control2 = st.columns(2)

        target_temp_c = control1.slider(
            "Target setpoint (°C)",
            min_value=16.0,
            max_value=30.0,
            value=22.5,
            step=0.5,
        )

        initial_temp_c = control2.slider(
            "Starting room temperature (°C)",
            min_value=16.0,
            max_value=30.0,
            value=24.0,
            step=0.5,
        )

        twin_states = list(
            simulate_hours(
                hours=24,
                dt_minutes=15,
                target_temp_c=target_temp_c,
                initial_temp_c=initial_temp_c,
            )
        )
        twin_df = pd.DataFrame(twin_states)

        final_temp = twin_df["room_temp_c"].iloc[-1]
        peak_power_kw = twin_df["hvac_power_w"].abs().max() / 1000.0
        pct_conditioning = (twin_df["hvac_status"] != "OFF").mean() * 100.0

        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Final room temp", f"{final_temp:.1f} °C")
        metric2.metric("Peak HVAC load", f"{peak_power_kw:.1f} kW")
        metric3.metric("Time conditioning", f"{pct_conditioning:.0f}%")

        chart_df = twin_df.melt(
            id_vars=["timestamp"],
            value_vars=["room_temp_c", "outside_temp_c"],
            var_name="series",
            value_name="temp_c",
        )
        chart_df["series"] = chart_df["series"].map(
            {"room_temp_c": "Room Temp", "outside_temp_c": "Outside Temp"}
        )

        temp_lines = (
            alt.Chart(chart_df)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("temp_c:Q", title="Temperature (°C)"),
                color=alt.Color(
                    "series:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["Room Temp", "Outside Temp"],
                        range=["#2a78d6", "#eb6834"],
                    ),
                ),
            )
        )
        setpoint_rule = (
            alt.Chart(pd.DataFrame({"target_temp_c": [target_temp_c]}))
            .mark_rule(strokeDash=[4, 4], color="#898781")
            .encode(y="target_temp_c:Q")
        )

        st.altair_chart(temp_lines + setpoint_rule, use_container_width=True)

   
    elif st.session_state.page == "chat":

        st.markdown("### Ask anything")

        # Show the real conversation so far for this session
        if st.session_state.session_id:

            for past_message in get_history(st.session_state.session_id):

                with st.chat_message(past_message["role"]):

                    st.write(past_message["content"])

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

        # ----------------------------------------------------
        # VISUAL INSIGHTS (simple charts, Power BI style)
        # ----------------------------------------------------

        st.markdown("#### Visual Insights")

        numeric_columns = preview.select_dtypes(
            include="number"
        ).columns.tolist()

        text_columns = preview.select_dtypes(
            exclude="number"
        ).columns.tolist()

        chart1, chart2 = st.columns(2)

        # ---- BAR CHART (numeric column across rows) ----

        with chart1:

            if numeric_columns:

                selected_numeric = st.selectbox(
                    "Select a numeric column",
                    numeric_columns,
                    key="numeric_chart_column"
                )

                st.caption(f"{selected_numeric} across rows")

                bar_df = preview[[selected_numeric]].reset_index()
                bar_df.columns = ["row", selected_numeric]

                bar_chart = (
                    alt.Chart(bar_df)
                    .mark_bar(color="#2a78d6")
                    .encode(
                        x=alt.X("row:O", title="Row"),
                        y=alt.Y(f"{selected_numeric}:Q"),
                    )
                )

                st.altair_chart(bar_chart, use_container_width=True)

            else:

                st.info(
                    "No numeric columns available for a bar chart."
                )

        # ---- PIE CHART (category distribution) ----

        with chart2:

            pie_column = None

            if text_columns:

                pie_candidates = [
                    col for col in text_columns
                    if preview[col].nunique() <= 10
                ]

                if pie_candidates:
                    pie_column = st.selectbox(
                        "Select a category column",
                        pie_candidates,
                        key="pie_chart_column"
                    )

            if pie_column:

                st.caption(f"Distribution of {pie_column}")

                pie_counts = preview[pie_column].value_counts().reset_index()
                pie_counts.columns = [pie_column, "count"]

                pie_chart = (
                    alt.Chart(pie_counts)
                    .mark_arc()
                    .encode(
                        theta=alt.Theta("count:Q"),
                        color=alt.Color(f"{pie_column}:N", title=None),
                        tooltip=[pie_column, "count"],
                    )
                )

                st.altair_chart(pie_chart, use_container_width=True)

            else:

                st.info(
                    "No suitable category column available for a pie chart."
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



if (
    st.session_state.page == "chat"
    and st.session_state.domain != "Digital Twin"
):

    chat_query = st.chat_input(
        "Ask a question about your data..."
    )

    if chat_query:

        if not st.session_state.session_id:
            st.session_state.session_id = new_session()

        with st.spinner("Thinking..."):
            ask_agent(chat_query, st.session_state.session_id)

        st.rerun()
