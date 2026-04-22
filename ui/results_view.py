import streamlit as st
from src.search import run_search
from ui.map_view import render_map


def render_results(filters: dict):
    """Run search and display results."""

    results = run_search(filters)

    if not results:
        st.warning("No scenarios matched your filters. Try adjusting the sliders.")
        return

    st.success(f"Found **{len(results)}** matching scenario(s)")

    for i, result in enumerate(results):
        with st.expander(f"📍 Scenario {i+1}: `{result['scenario_id']}`"):
            # Feature summary
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg lane width", f"{result['avg_lane_width']:.2f} m")
            col2.metric("Max curvature", f"{result['max_curvature']:.2f} rad")
            col3.metric("Agents", result["num_agents"])

            col4, col5, col6 = st.columns(3)
            col4.metric("Lanes", result["num_lanes"])
            col5.metric("Crosswalk", "✅" if result["has_crosswalk"] else "❌")
            col6.metric("Roundabout", "✅" if result["is_roundabout"] else "❌")

            # HD map
            st.markdown("**HD Map**")
            render_map(result["scenario_path"])
