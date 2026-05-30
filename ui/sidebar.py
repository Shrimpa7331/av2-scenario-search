import streamlit as st
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback

import tomli_w
from src.loader import count_scenarios

CONFIG_PATH = Path(__file__).parent.parent / "config.toml"


def load_presets() -> dict:
    """Load presets from config.toml in the project root."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
    return config.get("presets", {})


def save_presets(presets: dict):
    """Write all presets back to config.toml."""
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump({"presets": presets}, f)


def _apply_preset_to_state(preset: dict):
    """Push preset values into session state so widgets pick them up."""
    st.session_state["filter_path"] = preset.get("path", "")
    st.session_state["filter_lane_width"] = (
        float(preset.get("lane_width_min", 2.0)),
        float(preset.get("lane_width_max", 5.0)),
    )
    st.session_state["filter_curvature"] = (
        float(preset.get("curvature_min", 0.0)),
        float(preset.get("curvature_max", 3.0)),
    )
    st.session_state["filter_num_agents"] = (
        int(preset.get("num_agents_min", 1)),
        int(preset.get("num_agents_max", 150)),
    )
    st.session_state["filter_has_crosswalk"] = bool(preset.get("has_crosswalk", False))
    st.session_state["filter_has_roundabout"] = bool(preset.get("has_roundabout", False))
    st.session_state["filter_max_results"] = int(preset.get("max_results", 10))


def render_sidebar() -> dict:
    """Render sidebar filters and return current filter state."""

    st.sidebar.header("📁 Dataset")

    # --- Preset selector ---
    presets = load_presets()
    preset_keys = list(presets.keys())
    preset_labels = [presets[k]["label"] for k in preset_keys]

    selected_label = st.sidebar.selectbox(
        "Load preset",
        options=preset_labels,
        index=0,
        key="selected_preset_label",
        help="Load a predefined dataset path and filter configuration"
    )

    selected_key = preset_keys[preset_labels.index(selected_label)]

    # Detect preset change — only push values into state when the preset actually switches
    if st.session_state.get("_last_preset") != selected_key:
        _apply_preset_to_state(presets[selected_key])
        st.session_state["_last_preset"] = selected_key

    # --- Dataset path ---
    dataset_path_str = st.sidebar.text_input(
        "Dataset path",
        key="filter_path",
        placeholder=r"e.g. D:\argoverse2\val",
        help="Path to your local Argoverse 2 motion forecasting folder"
    )

    dataset_path = None

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
        min_value=1.0, max_value=50.0,
        key="filter_lane_width",
        step=0.1,
        help="Filter scenarios by average lane width"
    )

    curvature = st.sidebar.slider(
        "Lane curvature (rad)",
        min_value=0.0, max_value=30.0,
        key="filter_curvature",
        step=0.1,
        help="Filter scenarios by maximum lane curvature"
    )

    num_agents = st.sidebar.slider(
        "Number of agents",
        min_value=1, max_value=150,
        key="filter_num_agents",
        step=1,
        help="Filter by number of agents in the scenario"
    )
    num_lanes = st.sidebar.slider(
        "Number of lanes",
        min_value=1, max_value=200,
        value=(1, 200), step=1,
        help="Filter by number of lanes in the scenario"
    )
    num_stops = st.sidebar.slider(
        "Number of stop signs",
        min_value=0, max_value=150,
        value=(0, 150), step=1,
        help="Filter by number of lanes in the scenario"
    )

    has_crosswalk = st.sidebar.checkbox(
        "Must have crosswalk",
        key="filter_has_crosswalk"
    )
    has_roundabout = st.sidebar.checkbox(
        "Must be roundabout",
        key="filter_has_roundabout"
    )
    has_intersection = st.sidebar.checkbox(
        "Must have intersection",
        key="filter_has_intersection"
    )
    st.sidebar.divider()

    max_results = st.sidebar.number_input(
        "Max searches",
        min_value=1, max_value=20000,
        key="filter_max_results",
        step=1
    )

    searched = False
    if dataset_path is not None:
        searched = st.sidebar.button("🔎 Search", use_container_width=True, type="primary")

    st.sidebar.divider()

    # --- Preset management ---
    st.sidebar.header("💾 Manage Presets")

    with st.sidebar.expander("Save current settings as preset"):
        new_label = st.text_input("Preset name", placeholder="e.g. EU Urban Night")
        if st.button("💾 Save preset", use_container_width=True):
            if not new_label.strip():
                st.error("Please enter a name for the preset.")
            else:
                new_key = new_label.strip().lower().replace(" ", "_")
                presets[new_key] = {
                    "label": new_label.strip(),
                    "path": dataset_path_str,
                    "lane_width_min": lane_width[0],
                    "lane_width_max": lane_width[1],
                    "curvature_min": curvature[0],
                    "curvature_max": curvature[1],
                    "num_agents_min": num_agents[0],
                    "num_agents_max": num_agents[1],
                    "has_crosswalk": has_crosswalk,
                    "has_roundabout": has_roundabout,
                    "max_results": int(max_results),
                    "has_intersection": has_intersection
                }
                save_presets(presets)
                st.success(f"✅ Preset '{new_label.strip()}' saved!")
                st.rerun()

    if selected_key != "default":
        if st.sidebar.button(f"🗑️ Delete preset '{selected_label}'", use_container_width=True):
            del presets[selected_key]
            save_presets(presets)
            st.rerun()

    return {
        "dataset_path": dataset_path,
        "lane_width": lane_width,
        "curvature": curvature,
        "num_agents": num_agents,
        "num_lanes": num_lanes,
        "num_stops": num_stops,
        "has_crosswalk": has_crosswalk,
        "has_roundabout": has_roundabout,
        "has_intersection": has_intersection,
        "max_results": max_results,
        "searched": searched,

    }
