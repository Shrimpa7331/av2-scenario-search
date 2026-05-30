from pathlib import Path
import numpy as np
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

   

    max_results = filters["max_results"]
    

    results = []
    progress = st.progress(0, text="Searching scenarios...")

    for i, scenario_path in enumerate(scenario_dirs):
        if i >= max_results:
            return results

        progress.progress(i / len(scenario_dirs), text=f"Scanning scenario {i+1} / {len(scenario_dirs)}...")

        try:
            scenario = load_scenario(scenario_path)
            avm = load_map(scenario_path)
            features = extract_features(scenario, avm)
        except Exception:
            continue

        # Apply filter
        
        if apply_filters(scenario, filters, avm) == False:
          continue

        results.append({
            "scenario_id": scenario_path.name,
            "scenario_path": scenario_path,
            **features,
        })

        
    progress.empty()
    return results
def apply_filters(scenario, filters :dict, avm) -> bool:
    
    lane_width_min, lane_width_max = filters["lane_width"]
    curvature_min, curvature_max = filters["curvature"]
    num_agents_min, num_agents_max = filters["num_agents"]
    num_lanes_min, num_lanes_max = filters["num_lanes"]
    num_stops_min, num_stops_max = filters["num_stops"]

    has_crosswalk = filters["has_crosswalk"]
    has_roundabout = filters["has_roundabout"]
    has_intersection = filters["has_intersection"]

    # check curvature
    for lane in avm.vector_lane_segments.values():

        left = lane.left_lane_boundary.xyz
        right = lane.right_lane_boundary.xyz

        n = min(len(left), len(right))

        points = (left[:n, :2] + right[:n, :2]) / 2
        n = len(points)

        if n < 3:
            continue

        step = max(1, n // 10)

        max_curv = 0.0
        min_curv = float("inf")

        for i in range(0, n - 2 * step, step):

            p1 = points[i]
            p2 = points[i + step]
            p3 = points[i + 2 * step]

            a = np.linalg.norm(p2 - p1)
            b = np.linalg.norm(p3 - p2)
            c = np.linalg.norm(p3 - p1)

            area = abs(np.cross(p2 - p1, p3 - p1)) / 2

            if area < 1e-9:
                continue

            k = 4 * area / (a * b * c)

            max_curv = max(max_curv, k)
            min_curv = min(min_curv, k)

        if min_curv < curvature_min:
            st.write(
                f"FAIL curvature_min: actual={min_curv:.4f}, filter={curvature_min:.4f}"
            )
            return False

        if max_curv > curvature_max:
            st.write(
                f"FAIL curvature_max: actual={max_curv:.4f}, filter={curvature_max:.4f}"
            )
            return False

    # filter num_agents
    number_oof_agents = len(scenario.tracks)

    if num_agents_min > number_oof_agents:
        st.write(
            f"FAIL num_agents_min: actual={number_oof_agents}, filter={num_agents_min}"
        )
        return False

    if num_agents_max < number_oof_agents:
        st.write(
            f"FAIL num_agents_max: actual={number_oof_agents}, filter={num_agents_max}"
        )
        return False

    # filter num_lanes
    nmr_lanes = len(avm.vector_lane_segments)

    if num_lanes_min > nmr_lanes:
        st.write(
            f"FAIL num_lanes_min: actual={nmr_lanes}, filter={num_lanes_min}"
        )
        return False

    if num_lanes_max < nmr_lanes:
        st.write(
            f"FAIL num_lanes_max: actual={nmr_lanes}, filter={num_lanes_max}"
        )
        return False

    # filter number of stop signs
    estimated_stop_signs = (
        sum(
            1 for lane in avm.vector_lane_segments.values()
            if lane.is_intersection
        ) * 4
    )

    if num_stops_min > estimated_stop_signs:
        st.write(
            f"FAIL num_stops_min: actual={estimated_stop_signs}, filter={num_stops_min}"
        )
        return False

    if num_stops_max < estimated_stop_signs:
        st.write(
            f"FAIL num_stops_max: actual={estimated_stop_signs}, filter={num_stops_max}"
        )
        return False

    # filter crosswalk
    num_crosswalks = len(avm.vector_pedestrian_crossings)

    if has_crosswalk and num_crosswalks == 0:
        st.write(
            f"FAIL crosswalk: actual={num_crosswalks}"
        )
        return False

    # har roundabout
    if has_roundabout:

        found_roundabout = False

        for lane in avm.vector_lane_segments.values():

            left = lane.left_lane_boundary.xyz
            right = lane.right_lane_boundary.xyz

            n = min(len(left), len(right))

            if n < 2:
                continue

            points = (left[:n, :2] + right[:n, :2]) / 2

            start_point = points[0]
            end_point = points[-1]

            if np.linalg.norm(end_point - start_point) < 5.0:
                found_roundabout = True
                break

        if not found_roundabout:
            st.write("FAIL roundabout")
            return False

    # har intersection
    for lane in avm.vector_lane_segments.values():
        if lane.is_intersection == False and has_intersection:
            st.write("FAIL intersection")
            return False

    # filter lane width
    min_lane_width = float("inf")
    max_lane_width = 0.0

    for lane in avm.vector_lane_segments.values():
        left = lane.left_lane_boundary.xyz
        right = lane.right_lane_boundary.xyz

        n = min(len(left), len(right))

        widths = np.linalg.norm(
            left[:n, :2] - right[:n, :2],
            axis=1
        )

        min_lane_width = min(min_lane_width, np.min(widths))
        max_lane_width = max(max_lane_width, np.max(widths))
        avg_width = np.mean(widths)

        min_lane_width1 = 0.5 * avg_width
        max_lane_width1 = 2.0 * avg_width
        if min_lane_width < min_lane_width1:
            min_lane_width = min_lane_width1
        if max_lane_width > max_lane_width1:
            max_lane_width = max_lane_width1
    if min_lane_width < lane_width_min:
        st.write(
            f"FAIL lane_width_min: actual={min_lane_width:.2f} m, filter={lane_width_min:.2f} m"
        )
        return False

    if max_lane_width > lane_width_max:
        st.write(
            f"FAIL lane_width_max: actual={max_lane_width:.2f} m, filter={lane_width_max:.2f} m"
        )
        return False

    return True