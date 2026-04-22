import streamlit as st
from pathlib import Path
from ui.sidebar import render_sidebar
from ui.results_view import render_results
from ui.map_view import render_map

st.set_page_config(
    page_title="AV2 Scenario Search",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Argoverse 2 Scenario Search")
st.markdown("Search and explore motion forecasting scenarios by road geometry.")

# Sidebar — dataset path + filters
filters = render_sidebar()

# Main area
if filters["dataset_path"] is None:
    # Welcome screen
    st.info("👈 Start by entering the path to your Argoverse 2 dataset in the sidebar.")
    st.markdown("""
    ### How to use
    1. Enter the path to your local Argoverse 2 dataset folder in the sidebar
    2. Set your filters — lane width, curvature, road features
    3. Hit **Search** to find matching scenarios
    4. Click any result to view its HD map
    """)

elif not filters["searched"]:
    # Dataset loaded, waiting for search
    st.success(f"✅ Dataset loaded: `{filters['dataset_path']}`")
    st.markdown("Set your filters in the sidebar and hit **Search** to find scenarios.")

else:
    # Show results
    render_results(filters)
