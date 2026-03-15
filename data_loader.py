import os
import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image

DATA_ROOT = os.path.dirname(os.path.abspath(__file__))

MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500},
}

MINIMAP_FILES = {
    "AmbroseValley": "AmbroseValley_Minimap.png",
    "GrandRift":     "GrandRift_Minimap.png",
    "Lockdown":      "Lockdown_Minimap.jpg",   # original
}

# Preprocessed paths (created by preprocess.py)
PREPROCESSED_PARQUET = os.path.join(DATA_ROOT, "data", "all_events.parquet")
MINIMAP_DIR_PREPROCESSED = os.path.join(DATA_ROOT, "data", "minimaps")

DATE_FOLDERS = {
    "Feb 10": "February_10",
    "Feb 11": "February_11",
    "Feb 12": "February_12",
    "Feb 13": "February_13",
    "Feb 14": "February_14",
}
DATES_ORDERED = list(DATE_FOLDERS.keys())

# Visual style per event type
EVENT_STYLES = {
    "Position":      {"color": "#4A90D9", "symbol": "circle",         "size": 4,  "label": "Position (Human)"},
    "BotPosition":   {"color": "#8c8c8c", "symbol": "circle",         "size": 3,  "label": "Position (Bot)"},
    "Kill":          {"color": "#FF4444", "symbol": "x",              "size": 12, "label": "Kill"},
    "Killed":        {"color": "#8B0000", "symbol": "circle-cross",   "size": 12, "label": "Killed"},
    "BotKill":       {"color": "#FF8C00", "symbol": "x",              "size": 10, "label": "Bot Kill"},
    "BotKilled":     {"color": "#A0522D", "symbol": "circle-cross",   "size": 10, "label": "Bot Killed"},
    "KilledByStorm": {"color": "#9B59B6", "symbol": "triangle-down",  "size": 12, "label": "Storm Death"},
    "Loot":          {"color": "#FFD700", "symbol": "star",           "size": 10, "label": "Loot"},
}

HEATMAP_OPTIONS = {
    "High Traffic (All Movement)": {
        "events": ["Position", "BotPosition"],
        "colorscale": "Blues",
        "label": "Position events",
    },
    "Kill Zones": {
        "events": ["Kill", "BotKill"],
        "colorscale": "Reds",
        "label": "Kill events",
    },
    "Death Zones": {
        "events": ["Killed", "BotKilled"],
        "colorscale": "RdPu",
        "label": "Death events",
    },
    "Storm Deaths": {
        "events": ["KilledByStorm"],
        "colorscale": "Purples",
        "label": "Storm death events",
    },
    "Loot Hot Spots": {
        "events": ["Loot"],
        "colorscale": "YlOrBr",
        "label": "Loot events",
    },
}


def _world_to_pixel(df: pd.DataFrame):
    """Vectorised world (x, z) → minimap pixel (px, py)."""
    px = pd.Series(np.nan, index=df.index, dtype=float)
    py = pd.Series(np.nan, index=df.index, dtype=float)
    for map_id, cfg in MAP_CONFIG.items():
        mask = df["map_id"] == map_id
        if not mask.any():
            continue
        u = (df.loc[mask, "x"].astype(float) - cfg["origin_x"]) / cfg["scale"]
        v = (df.loc[mask, "z"].astype(float) - cfg["origin_z"]) / cfg["scale"]
        px[mask] = u * 1024
        py[mask] = (1 - v) * 1024
    return px, py


@st.cache_data(show_spinner="Loading match data…")
def load_all_data() -> pd.DataFrame:
    # Fast path: use the pre-processed single file created by preprocess.py
    if os.path.exists(PREPROCESSED_PARQUET):
        return pd.read_parquet(PREPROCESSED_PARQUET)

    # Fallback: scan raw folder structure (local dev without running preprocess.py)
    frames = []
    for date_label, folder in DATE_FOLDERS.items():
        folder_path = os.path.join(DATA_ROOT, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            fpath = os.path.join(folder_path, fname)
            try:
                df = pq.read_table(fpath).to_pandas()
                df["event"] = df["event"].apply(
                    lambda e: e.decode("utf-8") if isinstance(e, bytes) else e
                )
                df["date"] = date_label
                frames.append(df)
            except Exception:
                continue

    if not frames:
        return pd.DataFrame()

    full = pd.concat(frames, ignore_index=True)
    full["is_human"] = ~full["user_id"].str.match(r"^\d+$", na=False)
    full["match_id_short"] = full["match_id"].str[:8]
    full["pixel_x"], full["pixel_y"] = _world_to_pixel(full)
    full = full.sort_values(["match_id", "ts"]).reset_index(drop=True)
    ts_min_m   = full.groupby("match_id")["ts"].transform("min")
    ts_max_m   = full.groupby("match_id")["ts"].transform("max")
    ts_range_s = (ts_max_m - ts_min_m).dt.total_seconds()
    rel_raw_s  = (full["ts"] - ts_min_m).dt.total_seconds()
    full["rel_ts_norm"] = rel_raw_s / ts_range_s.where(ts_range_s > 0, 1.0)
    return full


@st.cache_data(show_spinner=False)
def get_match_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per match with pre-computed stats."""
    rows = []
    for match_id, g in df.groupby("match_id"):
        humans = g[g["is_human"]]
        duration = (g["ts"].max() - g["ts"].min()).total_seconds()
        rows.append({
            "match_id":      match_id,
            "match_short":   match_id[:8],
            "map_id":        g["map_id"].iloc[0],
            "date":          g["date"].iloc[0],
            "human_players": humans["user_id"].nunique(),
            "bots":          g[~g["is_human"]]["user_id"].nunique(),
            "kills":         g["event"].isin(["Kill", "BotKill"]).sum(),
            "deaths":        g["event"].isin(["Killed", "BotKilled", "KilledByStorm"]).sum(),
            "loot":          (g["event"] == "Loot").sum(),
            "duration_s":    round(duration),
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def get_minimap(map_id: str) -> Image.Image | None:
    # Prefer preprocessed (already 1024×1024, all PNG)
    pre = os.path.join(MINIMAP_DIR_PREPROCESSED, f"{map_id}_Minimap.png")
    if os.path.exists(pre):
        return Image.open(pre).convert("RGB")
    # Fallback: original high-res files
    fname = MINIMAP_FILES.get(map_id)
    if not fname:
        return None
    path = os.path.join(DATA_ROOT, "minimaps", fname)
    return Image.open(path).convert("RGB").resize((1024, 1024), Image.LANCZOS)


@st.cache_data(show_spinner=False)
def get_minimap_b64(map_id: str) -> str | None:
    """Return the minimap as a base64 data-URL string (cached).

    Passing a static string to Plotly's add_layout_image means the browser
    receives the exact same bytes on every render and can cache the image —
    preventing the flicker caused by re-encoding a PIL Image on each rerun.
    """
    import base64
    from io import BytesIO

    img = get_minimap(map_id)
    if img is None:
        return None
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
