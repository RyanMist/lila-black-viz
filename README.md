# LILA BLACK — Player Behavior Visualization Tool

An interactive web tool for level designers to explore 5 days of production gameplay data from **LILA BLACK**, a battle-royale extraction shooter.

**Live demo:** [Deployed URL — see below](#deployment)

---

## Features

| Tab | What it does |
|-----|-------------|
| **Event Map** | Scatter all kills, deaths, loot, and storm deaths across all matches on the minimap. Filter by player type and event type inline. |
| **Heatmap** | Density overlays for movement, kills, deaths, loot, and storm deaths. Adjustable opacity and smoothing. Split by date to see day-over-day change. |
| **Match Replay** | Pick any match and watch it unfold. Play/Pause/Scrub with a Plotly-native animation slider. Smooth interpolated movement between position samples. |

---

## Running Locally

### Requirements
- Python 3.11+
- The raw data folder structure (or the preprocessed `data/` folder)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/lila-black-viz.git
cd lila-black-viz

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add raw data (if you have the original parquet files)
#    Place the February_10 … February_14 folders and minimaps/ in the project root.
#    Then run the preprocessor:
python preprocess.py

#    If you only have the repo (data/ folder already present), skip step 3.

# 4. Launch
streamlit run app.py
```

The app opens at **http://localhost:8501**.

### Environment Variables
None required. The app reads data from local files only.

---

## Project Structure

```
lila-black-viz/
├── app.py                  # Main Streamlit application
├── data_loader.py          # Data loading, caching, coordinate transforms
├── preprocess.py           # One-time preprocessing: raw folders → data/
├── export_excel.py         # Generates player_data_verification.xlsx
├── requirements.txt
├── ARCHITECTURE.md         # Tech stack, data flow, trade-offs, insights
├── README.md
├── .streamlit/
│   └── config.toml         # Light theme
└── data/                   # Created by preprocess.py — committed to repo
    ├── all_events.parquet  # All 89,104 events, 2.9 MB gzip
    └── minimaps/           # 1024×1024 PNGs, ~700 KB each
        ├── AmbroseValley_Minimap.png
        ├── GrandRift_Minimap.png
        └── Lockdown_Minimap.png
```

---

## Tech Stack

| Component | Library | Version |
|-----------|---------|---------|
| App framework | Streamlit | 1.55+ |
| Visualisation | Plotly | 6.6+ |
| Data | PyArrow + Pandas | 23+ / 2+ |
| Images | Pillow | 9+ |
| Stats | SciPy | 1.10+ |

---

## Deployment

Deployed on **Streamlit Community Cloud**.

Steps to redeploy:
1. Fork this repo (must be public for Streamlit Cloud free tier)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your fork → set main file to `app.py`
4. Click **Deploy** — live in ~2 minutes

The `data/` folder is committed to the repo so no setup step is needed on the host.

---

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for:
- Tech stack choices and rationale
- Data flow diagram
- Trade-offs and what would be done differently
- Three game insights derived from the data
