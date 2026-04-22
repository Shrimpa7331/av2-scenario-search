import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
from pathlib import Path
from src.loader import load_scenario, load_map


def render_map(scenario_path: Path):
    """Render HD map + agent trajectories for a scenario."""
    scenario = load_scenario(scenario_path)
    avm = load_map(scenario_path)

    fig, ax = plt.subplots(figsize=(10, 8))

    # Draw lane boundaries
    for lane_seg in avm.vector_lane_segments.values():
        left = lane_seg.left_lane_boundary.xyz
        right = lane_seg.right_lane_boundary.xyz
        ax.plot(left[:, 0], left[:, 1], color="lightgray", linewidth=0.8)
        ax.plot(right[:, 0], right[:, 1], color="lightgray", linewidth=0.8)

    # Draw crosswalks
    for crosswalk in avm.vector_pedestrian_crossings.values():
        ax.plot(crosswalk.edge1.xyz[:, 0], crosswalk.edge1.xyz[:, 1], color="yellow", linewidth=1.5)
        ax.plot(crosswalk.edge2.xyz[:, 0], crosswalk.edge2.xyz[:, 1], color="yellow", linewidth=1.5)

    # Draw agent trajectories
    color_map = {
        "vehicle": "steelblue",
        "pedestrian": "tomato",
        "cyclist": "limegreen",
        "motorcyclist": "orange",
        "bus": "purple",
    }

    for track in scenario.tracks:
        xs = [s.position[0] for s in track.object_states]
        ys = [s.position[1] for s in track.object_states]
        observed = [s.observed for s in track.object_states]

        obj_type = track.object_type.value.lower()
        color = color_map.get(obj_type, "gray")
        is_focal = track.track_id == scenario.focal_track_id
        lw = 2.5 if is_focal else 1.0
        alpha = 1.0 if is_focal else 0.5

        obs_xs = [x for x, o in zip(xs, observed) if o]
        obs_ys = [y for y, o in zip(ys, observed) if o]
        fut_xs = [x for x, o in zip(xs, observed) if not o]
        fut_ys = [y for y, o in zip(ys, observed) if not o]

        ax.plot(obs_xs, obs_ys, color=color, linewidth=lw, alpha=alpha)
        ax.plot(fut_xs, fut_ys, color=color, linewidth=lw, alpha=alpha, linestyle="--")

        if is_focal and xs:
            ax.plot(xs[0], ys[0], "*", color="gold", markersize=12, zorder=10)

    ax.set_aspect("equal")
    ax.set_facecolor("dimgray")
    ax.set_title(f"Scenario: {scenario_path.name}", fontsize=10)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    plt.tight_layout()

    st.pyplot(fig)
    plt.close(fig)
