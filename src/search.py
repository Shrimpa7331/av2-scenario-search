import json
from pathlib import Path
import numpy as np
import streamlit as st
from src.loader import get_scenario_dirs, load_scenario, load_map
from src.features import extract_features, is_roundabout

FLAGS_FILE = Path(__file__).parent.parent / "flags.json"

def load_flags() -> dict:
    if FLAGS_FILE.exists():
        with open(FLAGS_FILE, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    return {}


def run_search(filters: dict) -> list[dict]:
    """
    Loop through scenarios, extract features, apply filters.
    Returns a list of matching scenario result dicts.
    """
    dataset_path: Path = filters["dataset_path"]
    scenario_dirs = get_scenario_dirs(dataset_path)

   

    scan_offset = filters.get("scan_offset", 0)
    goal_results = filters["goal_results"]
    max_scans = filters["max_scans"]
    flags = load_flags()

    scenario_dirs = scenario_dirs[scan_offset:]
    total_to_scan = min(len(scenario_dirs), max_scans)

    results = []
    progress = st.progress(0, text="Searching scenarios...")

    for i, scenario_path in enumerate(scenario_dirs):
        if i >= max_scans:
            break
        if len(results) >= goal_results:
            break

        progress.progress(i / total_to_scan if total_to_scan > 0 else 1, text=f"Scanning {scan_offset + i + 1} / {scan_offset + total_to_scan} — {len(results)} found...")

        try:
            scenario = load_scenario(scenario_path)
            avm = load_map(scenario_path)
            features = extract_features(scenario, avm)
        except Exception:
            continue

        # Apply flags — override detected features with researcher corrections
        scenario_flags = flags.get(scenario_path.name, {})
        if scenario_flags.get("fake_roundabout"):
            features["fake_roundabout"] = True  # explicit flag, checked separately in apply_filters
        if scenario_flags.get("fake_crosswalk"):
            features["has_crosswalk"] = False
        if scenario_flags.get("fake_intersection"):
            features["fake_intersection"] = True  # passed to apply_filters

        # Apply filter
        if apply_filters(scenario, filters, avm, features) == False:
            continue

        results.append({
            "scenario_id": scenario_path.name,
            "scenario_path": scenario_path,
            **features,
        })

        
    progress.empty()
    return results
def apply_filters(scenario, filters: dict, avm, features: dict) -> bool:
    
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
            return False

        if max_curv > curvature_max:
            return False

    # filter num_agents
    number_oof_agents = len(scenario.tracks)

    if num_agents_min > number_oof_agents:
        return False

    if num_agents_max < number_oof_agents:
        return False

    # filter num_lanes
    nmr_lanes = len(avm.vector_lane_segments)

    if num_lanes_min > nmr_lanes:
        return False

    if num_lanes_max < nmr_lanes:
        return False

    # filter number of stop signs
    estimated_stop_signs = (
        sum(
            1 for lane in avm.vector_lane_segments.values()
            if lane.is_intersection
        ) * 4
    )

    if num_stops_min > estimated_stop_signs:
        return False

    if num_stops_max < estimated_stop_signs:
        return False

    # filter crosswalk
    num_crosswalks = len(avm.vector_pedestrian_crossings)

    if has_crosswalk and num_crosswalks == 0:
        return False

    # har roundabout — check researcher flag first, then run circularity with slider value
    if has_roundabout:
        if features.get("fake_roundabout"):
            return False
        circularity_threshold = filters.get("roundabout_circularity", 0.95)
        if not is_roundabout(avm, circularity_threshold=circularity_threshold):
            return False

    # har intersection
    if has_intersection:
        if features.get("fake_intersection"):
            return False
        if not any(lane.is_intersection for lane in avm.vector_lane_segments.values()):
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
        return False

    if max_lane_width > lane_width_max:
        return False

    return True