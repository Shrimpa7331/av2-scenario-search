import streamlit as st
from pathlib import Path
from src.loader import count_scenarios


def render_sidebar() -> dict:
    """Render sidebar filters and return current filter state."""

    st.sidebar.header("📁 Dataset")

    dataset_path_str = st.sidebar.text_input(
        "Dataset path",
        placeholder=r"e.g. D:\argoverse2\val",
        help="Path to your local Argoverse 2 motion forecasting folder"
    )

    dataset_path = None
    scenario_count = 0

    if dataset_path_str:
        p = Path(dataset_path_str)
        if p.exists() and p.is_dir():
            scenario_count = count_scenarios(p)
            st.sidebar.success(f"✅ {scenario_count} scenarios found")
            dataset_path = p
        else:
            st.sidebar.error("❌ Path not found")

    st.sidebar.divider()

    # --- Filters ---
    st.sidebar.header("🔍 Filters")

    lane_width = st.sidebar.slider(
        "Lane width (m)",
        min_value=1.0, max_value=10.0,
        value=(2.0, 5.0), step=0.1,
        help="Filter scenarios by average lane width"
    )

    curvature = st.sidebar.slider(
        "Lane curvature (rad)",
        min_value=0.0, max_value=3.0,
        value=(0.0, 3.0), step=0.1,
        help="Filter scenarios by maximum lane curvature"
    )

    num_agents = st.sidebar.slider(
        "Number of agents",
        min_value=1, max_value=150,
        value=(1, 150), step=1,
        help="Filter by number of agents in the scenario"
    )

    has_crosswalk = st.sidebar.checkbox("Must have crosswalk", value=False)
    has_roundabout = st.sidebar.checkbox("Must be roundabout", value=False)

    st.sidebar.divider()

    max_results = st.sidebar.number_input(
        "Max results to show",
        min_value=1, max_value=100,
        value=10, step=1
    )

    searched = False
    if dataset_path is not None:
        searched = st.sidebar.button("🔎 Search", use_container_width=True, type="primary")

    return {
        "dataset_path": dataset_path,
        "lane_width": lane_width,
        "curvature": curvature,
        "num_agents": num_agents,
        "has_crosswalk": has_crosswalk,
        "has_roundabout": has_roundabout,
        "max_results": max_results,
        "searched": searched,
    }
