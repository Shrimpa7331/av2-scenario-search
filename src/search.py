from pathlib import Path
import streamlit as st
from src.loader import get_scenario_dirs, load_scenario, load_map
from src.features import extract_features


def run_search(filters: dict) -> list[dict]:
    """
    Loop through scenarios, extract features, apply filters.
    Returns a list of matching scenario result dicts.
    """
    dataset_path: Path = filters["dataset_path"]
    scenario_dirs = get_scenario_dirs(dataset_path)

    lane_width_min, lane_width_max = filters["lane_width"]
    curvature_min, curvature_max = filters["curvature"]
    agents_min, agents_max = filters["num_agents"]
    max_results = filters["max_results"]

    results = []
    progress = st.progress(0, text="Searching scenarios...")

    for i, scenario_path in enumerate(scenario_dirs):
        progress.progress(i / len(scenario_dirs), text=f"Scanning scenario {i+1} / {len(scenario_dirs)}...")

        try:
            scenario = load_scenario(scenario_path)
            avm = load_map(scenario_path)
            features = extract_features(scenario, avm)
        except Exception:
            continue

        # Apply filters
        if not (lane_width_min <= features["avg_lane_width"] <= lane_width_max):
            continue
        if not (curvature_min <= features["max_curvature"] <= curvature_max):
            continue
        if not (agents_min <= features["num_agents"] <= agents_max):
            continue
        if filters["has_crosswalk"] and not features["has_crosswalk"]:
            continue
        if filters["has_roundabout"] and not features["is_roundabout"]:
            continue

        results.append({
            "scenario_id": scenario_path.name,
            "scenario_path": scenario_path,
            **features,
        })

        if len(results) >= max_results:
            break

    progress.empty()
    return results
