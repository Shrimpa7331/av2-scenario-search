import numpy as np
from av2.map.map_api import ArgoverseStaticMap


def compute_lane_widths(avm: ArgoverseStaticMap) -> list[float]:
    """Return average width per lane segment (in metres)."""
    widths = []
    for lane_seg in avm.vector_lane_segments.values():
        left = lane_seg.left_lane_boundary.xyz
        right = lane_seg.right_lane_boundary.xyz
        min_len = min(len(left), len(right))
        if min_len < 2:
            continue
        w = np.linalg.norm(left[:min_len, :2] - right[:min_len, :2], axis=1)
        widths.append(float(np.mean(w)))
    return widths


def compute_lane_curvatures(avm: ArgoverseStaticMap) -> list[float]:
    """Return absolute total heading change per lane segment (in radians)."""
    curvatures = []
    for lane_seg in avm.vector_lane_segments.values():
        left = lane_seg.left_lane_boundary.xyz
        right = lane_seg.right_lane_boundary.xyz
        min_len = min(len(left), len(right))
        if min_len < 3:
            continue
        centerline = (left[:min_len, :2] + right[:min_len, :2]) / 2
        vectors = np.diff(centerline, axis=0)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms < 1e-6, 1e-6, norms)
        unit_vecs = vectors / norms
        headings = np.arctan2(unit_vecs[:, 1], unit_vecs[:, 0])
        changes = np.diff(headings)
        changes = (changes + np.pi) % (2 * np.pi) - np.pi
        curvatures.append(float(abs(np.sum(changes))))
    return curvatures


def has_crosswalk(avm: ArgoverseStaticMap) -> bool:
    """Return True if the scenario map contains any pedestrian crossings."""
    return len(avm.vector_pedestrian_crossings) > 0


def is_roundabout(avm: ArgoverseStaticMap, min_cycle: int = 3, max_cycle: int = 10) -> bool:
    """Detect roundabout by finding a cycle in the lane successor graph (~2pi total turn)."""
    lane_segs = avm.vector_lane_segments
    successors = {lid: seg.successors for lid, seg in lane_segs.items()}

    curvature_cache = {}
    for lid, seg in lane_segs.items():
        left = seg.left_lane_boundary.xyz
        right = seg.right_lane_boundary.xyz
        min_len = min(len(left), len(right))
        if min_len < 3:
            curvature_cache[lid] = 0.0
            continue
        centerline = (left[:min_len, :2] + right[:min_len, :2]) / 2
        vectors = np.diff(centerline, axis=0)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms < 1e-6, 1e-6, norms)
        unit_vecs = vectors / norms
        headings = np.arctan2(unit_vecs[:, 1], unit_vecs[:, 0])
        changes = np.diff(headings)
        changes = (changes + np.pi) % (2 * np.pi) - np.pi
        curvature_cache[lid] = float(np.sum(changes))

    def dfs(start, current, path, visited):
        if len(path) > max_cycle:
            return None
        for nxt in successors.get(current, []):
            if nxt == start and len(path) >= min_cycle:
                return path
            if nxt not in visited and nxt in lane_segs:
                result = dfs(start, nxt, path + [nxt], visited | {nxt})
                if result is not None:
                    return result
        return None

    for lane_id in lane_segs:
        cycle = dfs(lane_id, lane_id, [lane_id], {lane_id})
        if cycle is None:
            continue
        total_turn = sum(curvature_cache.get(lid, 0.0) for lid in cycle)
        if abs(total_turn) > 4.0:
            return True

    return False


def extract_features(scenario, avm: ArgoverseStaticMap) -> dict:
    """Extract all geometric features for a scenario."""
    widths = compute_lane_widths(avm)
    curvatures = compute_lane_curvatures(avm)

    return {
        "num_agents": len(scenario.tracks),
        "avg_lane_width": float(np.mean(widths)) if widths else 0.0,
        "max_curvature": float(max(curvatures)) if curvatures else 0.0,
        "has_crosswalk": has_crosswalk(avm),
        "is_roundabout": is_roundabout(avm),
        "num_lanes": len(avm.vector_lane_segments),
    }
