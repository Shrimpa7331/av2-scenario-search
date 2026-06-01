import streamlit as st
import json
from pathlib import Path
from src.search import run_search
from ui.map_view import render_map

BOOKMARKS_FILE = Path(__file__).parent.parent / "bookmarks.json"
FLAGS_FILE = Path(__file__).parent.parent / "flags.json"

FLAG_OPTIONS = {
    "fake_roundabout": "Roundabout",
    "fake_crosswalk": "Crosswalk",
    "fake_intersection": "Intersection",
}


def load_bookmarks() -> list:
    if BOOKMARKS_FILE.exists():
        with open(BOOKMARKS_FILE, "r") as f:
            return json.load(f)
    return []


def save_bookmarks(bookmarks: list):
    with open(BOOKMARKS_FILE, "w") as f:
        json.dump(bookmarks, f, indent=2)


def load_flags() -> dict:
    if FLAGS_FILE.exists():
        with open(FLAGS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_flags(flags: dict):
    with open(FLAGS_FILE, "w") as f:
        json.dump(flags, f, indent=2)


def render_results(filters: dict):
    """Run search and display results."""

    # Init session state
    if "bookmarks" not in st.session_state:
        st.session_state["bookmarks"] = load_bookmarks()
    if "flags" not in st.session_state:
        st.session_state["flags"] = load_flags()

    # Use cached results unless Search was just pressed (cache cleared in app.py)
    if st.session_state.get("_search_results") is None:
        st.session_state["_search_results"] = run_search(filters)

    results = st.session_state["_search_results"]

    if not results:
        st.warning("No scenarios matched your filters. Try adjusting the sliders.")
        return

    st.success(f"Found **{len(results)}** matching scenario(s)")

    # Bookmarks panel
    bookmarks = st.session_state["bookmarks"]
    if bookmarks:
        with st.expander(f"⭐ Bookmarked scenarios ({len(bookmarks)})", expanded=False):
            for bm in bookmarks:
                col1, col2 = st.columns([5, 1])
                col1.code(bm["scenario_id"])
                if col2.button("🗑️", key=f"del_bm_{bm['scenario_id']}"):
                    st.session_state["bookmarks"] = [
                        b for b in bookmarks if b["scenario_id"] != bm["scenario_id"]
                    ]
                    save_bookmarks(st.session_state["bookmarks"])
                    st.rerun()

            if st.button("📋 Copy all IDs to clipboard"):
                ids = "\n".join(b["scenario_id"] for b in bookmarks)
                st.code(ids)

    st.divider()

    # Results
    for i, result in enumerate(results):
        scenario_id = result["scenario_id"]
        is_bookmarked = any(b["scenario_id"] == scenario_id for b in st.session_state["bookmarks"])
        scenario_flags = st.session_state["flags"].get(scenario_id, {})
        has_flags = any(scenario_flags.values())

        label = ("⭐" if is_bookmarked else "📍")
        if has_flags:
            label = "🚩"
        with st.expander(f"{label} Scenario {i+1}: `{scenario_id}`"):
            # Feature summary
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg lane width", f"{result['avg_lane_width']:.2f} m")
            col2.metric("Max curvature", f"{result['max_curvature']:.2f} rad")
            col3.metric("Agents", result["num_agents"])

            col4, col5, col6 = st.columns(3)
            col4.metric("Lanes", result["num_lanes"])
            col5.metric("Crosswalk", "✅" if result["has_crosswalk"] else "❌")
            col6.metric("Roundabout", "✅" if result["is_roundabout"] else "❌")

            # Action buttons row
            bcol1, bcol2 = st.columns(2)

            # Bookmark
            with bcol1:
                if is_bookmarked:
                    if st.button("⭐ Remove bookmark", key=f"bm_{scenario_id}"):
                        st.session_state["bookmarks"] = [
                            b for b in st.session_state["bookmarks"] if b["scenario_id"] != scenario_id
                        ]
                        save_bookmarks(st.session_state["bookmarks"])
                        st.rerun()
                else:
                    if st.button("☆ Bookmark", key=f"bm_{scenario_id}"):
                        st.session_state["bookmarks"].append({
                            "scenario_id": scenario_id,
                            "path": str(result["scenario_path"]),
                        })
                        save_bookmarks(st.session_state["bookmarks"])
                        st.rerun()

            # Flag as fake
            with bcol2:
                with st.popover("🚩 Flag as fake detection"):
                    st.markdown("**Mark features as incorrectly detected:**")
                    updated = dict(scenario_flags)
                    changed = False
                    for flag_key, flag_label in FLAG_OPTIONS.items():
                        val = st.checkbox(
                            f"Fake {flag_label}",
                            value=bool(scenario_flags.get(flag_key, False)),
                            key=f"flag_{scenario_id}_{flag_key}"
                        )
                        if val != scenario_flags.get(flag_key, False):
                            updated[flag_key] = val
                            changed = True
                    if changed:
                        st.session_state["flags"][scenario_id] = updated
                        save_flags(st.session_state["flags"])
                        st.success("Flag saved — takes effect on next search.")

            # HD map
            st.markdown("**HD Map**")
            render_map(result["scenario_path"])
