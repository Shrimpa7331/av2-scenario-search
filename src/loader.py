from pathlib import Path
import streamlit as st
from av2.datasets.motion_forecasting import scenario_serialization
from av2.map.map_api import ArgoverseStaticMap


def count_scenarios(dataset_path: Path) -> int:
    """Count how many scenario folders exist in the dataset path."""
    return sum(1 for p in dataset_path.iterdir() if p.is_dir())


@st.cache_data
def get_scenario_dirs(dataset_path: Path) -> list[Path]:
    """Return sorted list of all scenario directories. Cached so it only reads disk once."""
    return sorted([p for p in dataset_path.iterdir() if p.is_dir()])


@st.cache_data
def load_scenario(scenario_path: Path):
    """Load trajectory data for a scenario. Cached per path."""
    parquet_file = next(scenario_path.glob("*.parquet"))
    return scenario_serialization.load_argoverse_scenario_parquet(parquet_file)


@st.cache_data
def load_map(scenario_path: Path) -> ArgoverseStaticMap:
    """Load HD map for a scenario. Cached per path."""
    map_file = next(scenario_path.glob("log_map_archive_*.json"))
    return ArgoverseStaticMap.from_json(map_file)
