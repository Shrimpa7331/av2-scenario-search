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
    """Return max heading change between neighbouring lane segments (in radians)."""
    curvatures = []
    for lane_seg in avm.vector_lane_segments.values():
        left = lane_seg.left_lane_boundary.xyz
        right = lane_seg.right_lane_boundary.xyz
        min_len = min(len(left), len(right))
        if min_len < 3:
            continue
        centerline = (left[:min_len, :2] + right[:min_len, :2]) / 2
        vectors = np.diff(centerline, axis=0)
        norms = np.linalg.norm(vectors, axis=1)
        valid_vectors = vectors[norms > 1e-6]
        if len(valid_vectors) < 2:
            continue
        headings = np.arctan2(valid_vectors[:, 1], valid_vectors[:, 0])
        changes = np.diff(headings)
        changes = (changes + np.pi) % (2 * np.pi) - np.pi
        curvatures.append(float(np.max(np.abs(changes))))
    return curvatures


def has_crosswalk(avm: ArgoverseStaticMap) -> bool:
    """Return True if the scenario map contains any pedestrian crossings."""
    return len(avm.vector_pedestrian_crossings) > 0


def is_roundabout(avm: ArgoverseStaticMap, min_cycle: int = 3, max_cycle: int = 10, circularity_min: float = 0.5, circularity_max: float = 1.0) -> bool:
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

    def cycle_circularity(cycle):
        """Compute isoperimetric circularity of the cycle's centerline points.
        Perfect circle = 1.0; elongated shapes approach 0."""
        points = []
        for lid in cycle:
            seg = lane_segs[lid]
            left = seg.left_lane_boundary.xyz
            right = seg.right_lane_boundary.xyz
            min_len = min(len(left), len(right))
            if min_len < 2:
                continue
            centerline = (left[:min_len, :2] + right[:min_len, :2]) / 2
            points.append(centerline)
        if not points:
            return 0.0
        pts = np.concatenate(points, axis=0)

        # Perimeter
        diffs = np.diff(pts, axis=0)
        perimeter = float(np.sum(np.linalg.norm(diffs, axis=1)))
        if perimeter < 1e-6:
            return 0.0

        # Area via shoelace
        x, y = pts[:, 0], pts[:, 1]
        area = abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))) / 2

        # Circularity: 4π·area / perimeter²  (1.0 = perfect circle)
        return (4 * np.pi * area) / (perimeter ** 2)

    for lane_id in lane_segs:
        cycle = dfs(lane_id, lane_id, [lane_id], {lane_id})
        if cycle is None:
            continue
        total_turn = sum(curvature_cache.get(lid, 0.0) for lid in cycle)
        if abs(total_turn) > 4.0:
            circularity = cycle_circularity(cycle)
            if circularity_min <= circularity <= circularity_max:
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
