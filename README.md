# AV2 Scenario Search

An interactive tool for searching and filtering Argoverse 2 motion forecasting scenarios by road geometry. Built with Streamlit, it lets you visually explore scenarios by lane width, curvature, roundabout detection, intersections, crosswalks, and more.

---

## Project Description

This tool was developed as part of a course project to explore and filter the Argoverse 2 motion forecasting dataset by geometric road properties. The interface allows researchers to define geometric filters, scan large scenario datasets, view HD maps with agent trajectories, bookmark interesting scenarios, and flag false detections for correction.

---

## Dependencies

- Python 3.10 or higher
- See `requirements.txt` for all required packages

Install dependencies with:

```bash
pip install -r requirements.txt
```

> **Note:** The `av2` package (Argoverse 2 API) may require additional system dependencies. See the official installation guide at https://argoverse.github.io/user-guide/getting_started.html

---

## Setup

1. Clone or download this repository
2. Install dependencies (see above)
3. Download the Argoverse 2 Motion Forecasting dataset from https://www.argoverse.org/av2.html
4. (Optional) Use `extract_city_scenarios.py` to extract scenarios from a specific city into a smaller folder for faster searching (see below)

---

## How to Run

From inside the `av2-scenario-search` folder, run:

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (typically http://localhost:8501) in your browser.

---

## Using the App

1. Enter the path to your local Argoverse 2 scenario folder in the sidebar, or select a saved preset
2. Set your filters (lane width, curvature, number of agents, roundabout, etc.)
3. Click **Search** to find matching scenarios
4. Click any result to view its HD map and agent trajectories
5. Bookmark scenarios of interest or flag incorrect detections

---

## Sample Data

The `miami_scenarios/` folder contains a small subset of Argoverse 2 scenarios recorded in Miami, USA. This is sufficient to test all features of the tool. The full dataset can be downloaded from https://www.argoverse.org/av2.html — these sample scenarios are a direct subset of the motion forecasting training split.

---

## Utility Script: extract_city_scenarios.py

Extracts scenarios from a specific city out of the full Argoverse 2 training split:

```bash
python extract_city_scenarios.py <city> <amount> <path_to_train_folder>
```

Example:

```bash
python extract_city_scenarios.py miami 500 "D:/argoverse2/train"
```

This copies up to 500 Miami scenarios into a new folder called `miami_scenarios/` next to the train folder.

---

## Assumptions and Limitations

- Roundabout detection uses a graph-cycle + circularity heuristic and may produce false positives on complex intersections. Use the flag system in the UI to mark and correct these.
- Stop sign counts are estimated (not directly available in AV2 map data).
- The tool is designed for local use with a downloaded copy of the dataset — it does not stream data from the internet.
- Tested on Windows with Python 3.11.
