# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
"""
preprocess.py  —  run ONCE before first launch (or before pushing to GitHub).

Reads all raw parquet files from February_10 … February_14, applies every
transformation the app needs, writes a single compressed parquet to data/ and
resizes the three minimap images to 1024×1024 in data/minimaps/.

Usage:
    python preprocess.py
"""

import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))

DATE_FOLDERS = {
    "February_10": "February_10",
    "February_11": "February_11",
    "February_12": "February_12",
    "February_13": "February_13",
    "February_14": "February_14",
}

MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500},
}

MINIMAP_SRC = {
    "AmbroseValley": "minimaps/AmbroseValley_Minimap.png",
    "GrandRift":     "minimaps/GrandRift_Minimap.png",
    "Lockdown":      "minimaps/Lockdown_Minimap.jpg",
}

MINIMAP_DST = {
    "AmbroseValley": "data/minimaps/AmbroseValley_Minimap.png",
    "GrandRift":     "data/minimaps/GrandRift_Minimap.png",
    "Lockdown":      "data/minimaps/Lockdown_Minimap.png",
}

OUT_PARQUET = os.path.join(ROOT, "data", "all_events.parquet")


def load_raw() -> pd.DataFrame:
    frames = []
    total_files = 0
    for date_label, folder in DATE_FOLDERS.items():
        folder_path = os.path.join(ROOT, folder)
        if not os.path.isdir(folder_path):
            print(f"  [skip] {folder} not found")
            continue
        files = os.listdir(folder_path)
        for fname in files:
            fpath = os.path.join(folder_path, fname)
            try:
                df = pq.read_table(fpath).to_pandas()
                df["event"] = df["event"].apply(
                    lambda e: e.decode("utf-8") if isinstance(e, bytes) else e
                )
                df["date"] = date_label
                frames.append(df)
                total_files += 1
            except Exception:
                continue
        print(f"  {date_label}: {len(files)} files")
    print(f"  Total files loaded: {total_files:,}")
    return pd.concat(frames, ignore_index=True)


def add_computed_columns(full: pd.DataFrame) -> pd.DataFrame:
    # Human vs bot
    full["is_human"] = ~full["user_id"].str.match(r"^\d+$", na=False)
    full["match_id_short"] = full["match_id"].str[:8]

    # Minimap pixel coordinates
    px = pd.Series(np.nan, index=full.index, dtype=float)
    py = pd.Series(np.nan, index=full.index, dtype=float)
    for map_id, cfg in MAP_CONFIG.items():
        mask = full["map_id"] == map_id
        if not mask.any():
            continue
        u = (full.loc[mask, "x"].astype(float) - cfg["origin_x"]) / cfg["scale"]
        v = (full.loc[mask, "z"].astype(float) - cfg["origin_z"]) / cfg["scale"]
        px[mask] = u * 1024
        py[mask] = (1 - v) * 1024
    full["pixel_x"] = px
    full["pixel_y"] = py

    # Per-match normalised timestamp (0 → 1)
    full = full.sort_values(["match_id", "ts"]).reset_index(drop=True)
    ts_min   = full.groupby("match_id")["ts"].transform("min")
    ts_max   = full.groupby("match_id")["ts"].transform("max")
    ts_range = (ts_max - ts_min).dt.total_seconds()
    rel_raw  = (full["ts"] - ts_min).dt.total_seconds()
    full["rel_ts_norm"] = rel_raw / ts_range.where(ts_range > 0, 1.0)

    return full


def resize_minimaps():
    dst_dir = os.path.join(ROOT, "data", "minimaps")
    os.makedirs(dst_dir, exist_ok=True)
    for map_id, src_rel in MINIMAP_SRC.items():
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(ROOT, MINIMAP_DST[map_id])
        if not os.path.exists(src):
            print(f"  [skip] {src_rel} not found")
            continue
        img = Image.open(src).convert("RGB").resize((1024, 1024), Image.LANCZOS)
        img.save(dst, format="PNG", optimize=True)
        size_kb = os.path.getsize(dst) / 1024
        print(f"  {map_id}: saved to {dst}  ({size_kb:.0f} KB)")


def main():
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

    print("\n── Loading raw parquet files ──────────────────────────────")
    full = load_raw()
    print(f"  Rows: {len(full):,}")

    print("\n── Computing derived columns ──────────────────────────────")
    full = add_computed_columns(full)
    print(f"  Columns: {list(full.columns)}")

    print("\n── Writing data/all_events.parquet ────────────────────────")
    full.to_parquet(OUT_PARQUET, compression="gzip", index=False)
    size_mb = os.path.getsize(OUT_PARQUET) / 1024 / 1024
    print(f"  Saved: {OUT_PARQUET}  ({size_mb:.2f} MB)")

    print("\n── Resizing minimap images ─────────────────────────────────")
    resize_minimaps()

    print("\n Done. You can now run:  streamlit run app.py\n")


if __name__ == "__main__":
    main()
