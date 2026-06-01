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

        vectors = np.diff(points, axis=0)
        norms = np.linalg.norm(vectors, axis=1)
        valid_vectors = vectors[norms > 1e-6]

        if len(valid_vectors) < 2:
            continue

        headings = np.arctan2(valid_vectors[:, 1], valid_vectors[:, 0])
        curvature_values = np.abs(np.diff(headings))
        curvature_values = (curvature_values + np.pi) % (2 * np.pi) - np.pi
        curvature_values = np.abs(curvature_values)

        if len(curvature_values) == 0:
            continue

        avg_curv = np.mean(curvature_values)
        min_allowed_curv = avg_curv / 3
        max_allowed_curv = avg_curv * 3
        filtered_curvatures = [
            k for k in curvature_values
            if min_allowed_curv <= k <= max_allowed_curv
        ]

        if not filtered_curvatures:
            continue

        min_curv = min(filtered_curvatures)
        max_curv = max(filtered_curvatures)

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
    lane_width_values = []

    for lane in avm.vector_lane_segments.values():
        left = lane.left_lane_boundary.xyz
        right = lane.right_lane_boundary.xyz

        if len(left) < 2 or len(right) < 2:
            continue

        left_points = left[:, :2]
        right_points = right[:, :2]

        same_direction_distance = (
            np.linalg.norm(left_points[0] - right_points[0])
            + np.linalg.norm(left_points[-1] - right_points[-1])
        )
        opposite_direction_distance = (
            np.linalg.norm(left_points[0] - right_points[-1])
            + np.linalg.norm(left_points[-1] - right_points[0])
        )

        if opposite_direction_distance < same_direction_distance:
            right_points = right_points[::-1]

        left_dist = np.insert(
            np.cumsum(np.linalg.norm(np.diff(left_points, axis=0), axis=1)),
            0,
            0.0
        )
        right_dist = np.insert(
            np.cumsum(np.linalg.norm(np.diff(right_points, axis=0), axis=1)),
            0,
            0.0
        )

        if left_dist[-1] == 0 or right_dist[-1] == 0:
            continue

        sample_count = max(len(left_points), len(right_points))
        left_sample_dist = np.linspace(0.0, left_dist[-1], sample_count)
        right_sample_dist = np.linspace(0.0, right_dist[-1], sample_count)

        left_interp = np.column_stack((
            np.interp(left_sample_dist, left_dist, left_points[:, 0]),
            np.interp(left_sample_dist, left_dist, left_points[:, 1])
        ))
        right_interp = np.column_stack((
            np.interp(right_sample_dist, right_dist, right_points[:, 0]),
            np.interp(right_sample_dist, right_dist, right_points[:, 1])
        ))

        widths = np.linalg.norm(left_interp - right_interp, axis=1)

        median_width = np.median(widths)
        min_allowed_width = median_width / 3
        max_allowed_width = median_width * 3
        filtered_widths = widths[
            (widths >= min_allowed_width) & (widths <= max_allowed_width)
        ]

        if len(filtered_widths) == 0:
            continue

        lane_width_values.extend(filtered_widths)

    if not lane_width_values:
        return False

    min_lane_width = np.percentile(lane_width_values, 10)
    max_lane_width = np.percentile(lane_width_values, 90)

    if min_lane_width < lane_width_min:
        return False

    if max_lane_width > lane_width_max:
        return False

    return True

