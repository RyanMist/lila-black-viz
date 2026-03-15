# Architecture — LILA BLACK Player Behavior Tool

## Tech Stack Choices

| Layer | Choice | Why |
|-------|--------|-----|
| **App framework** | Streamlit | Handles data, UI, and hosting in one Python file. No separate frontend/backend to wire up. The alternative (React + FastAPI) would have been faster to animate but 3× longer to build for the same feature set. |
| **Visualisation** | Plotly | Native animation frame support — critical for the match replay. Plotly's `frames` API lets the browser handle animation in JS after a single Python render, which eliminates the flickering and CPU cost of `st.rerun()` loops. |
| **Data** | PyArrow + Pandas | PyArrow reads Parquet at near-native speed. Pandas is used for all downstream filtering and aggregation. The full dataset (89 k rows) fits comfortably in memory after a single load. |
| **Images** | Pillow | Resizes the original 4320–9000 px minimap images to 1024×1024 at preprocess time. At runtime the resized PNG is base64-encoded once and cached, so the browser caches it across renders — no flickering. |
| **Hosting** | Streamlit Community Cloud | Zero-config deployment from a GitHub repo push. The preprocessed 2.9 MB parquet + three ~700 KB minimap PNGs stay well under GitHub and Streamlit Cloud limits. |

---

## Data Flow

```
Raw parquet files (1,243 files, ~8 MB)
        |
        | preprocess.py  (run once)
        v
data/all_events.parquet  (2.9 MB, gzip)
data/minimaps/*.png      (1024x1024, ~700 KB each)
        |
        | load_all_data()  @st.cache_data
        v
In-memory DataFrame  (89,104 rows, 14 columns)
  + is_human flag
  + pixel_x / pixel_y  (world → minimap UV → pixel)
  + rel_ts_norm  (per-match 0→1 timestamp)
        |
        +-----> Event Map tab
        |         filter by player type + event type
        |         Plotly scatter on minimap background
        |
        +-----> Heatmap tab
        |         filter by event category
        |         Plotly Histogram2dContour on minimap
        |
        +-----> Match Replay tab
                  scale rel_ts_norm × playback_dur
                  pre-compute 61 Plotly animation frames
                  browser animates at 60 fps — no Python reruns
```

### Coordinate mapping
World `(x, z)` → UV `(0-1)` → pixel `(0-1024)`:
```
u         = (x - origin_x) / scale
v         = (z - origin_z) / scale
pixel_x   = u * 1024
pixel_y   = (1 - v) * 1024       # Y flipped: image origin is top-left
```
Each map has its own `scale` and `origin` defined in `MAP_CONFIG`.

### Timestamp normalisation
All events across a match are stamped with write-time (flush), not game-time.
The entire match window is ~0.34 s wide. To make the replay meaningful:
```
rel_ts_norm = (ts - match_min_ts) / (match_max_ts - match_min_ts)
scaled_ts   = rel_ts_norm × playback_dur   (default 25 s)
```
Relative ordering within the flush window is preserved; absolute values are discarded.

---

## Trade-offs

| Decision | Trade-off |
|----------|-----------|
| Streamlit over React | Faster to build; less control over animation timing. Solved by moving animation entirely into Plotly frames. |
| Pre-process to a single parquet | Startup is instant; but the user must re-run `preprocess.py` if raw data changes. Acceptable for a static dataset. |
| 61 animation frames | Smooth enough (one frame per ~0.4 s of scaled playback) while keeping the figure JSON under ~5 MB. More frames = smoother but slower initial load. |
| Timestamp normalisation | Preserves event ordering but discards real match duration. A level designer cannot know if a player spent 3 minutes or 12 minutes in a zone — only the sequence matters. |
| Plotly `Histogram2dContour` for heatmap | Easy to implement and visually clean, but does not distinguish density peaks vs noise at low event counts (e.g. GrandRift with only 192 bot kills). A KDE with a tunable bandwidth would be more accurate. |

---

## What I Would Do Differently With More Time

1. **Reconstruct real timestamps.** If the server-side event queue is FIFO, the row order within each parquet file preserves the actual sequence. Fitting a monotone spline to that order would give plausible elapsed times and make the timeline slider meaningful.

2. **DuckDB for in-browser queries.** Replacing Pandas with DuckDB (WASM or server-side) would allow SQL-style ad-hoc queries directly from the UI — e.g. "show all matches where a player died to the storm within 60 s of their first loot".

3. **Player path comparison.** Overlay two or more players' paths on the same map to compare routing strategies — useful for level designers evaluating whether players use intended vs unintended paths.

4. **Bot placement analysis.** Cross-reference BotKill coordinates with Position density to answer "are bots placed where players already go, or are they pulling players off the main path?"

---

## Three Insights From the Data

### 1. Player retention dropped 88 % in five days
Unique human players: 98 (Feb 10) → 81 → 59 → 47 → 12 (Feb 14).
The Event Map with the date filter set to a single day makes this immediately visible — the density of event markers roughly halves every two days. This is a significant early-retention signal worth investigating (onboarding friction? match quality?).

### 2. Human-vs-human combat is nearly absent
Across all 796 matches and 89 k events, there are only **5 human Kill events** total.
The game is effectively PvE: players fight bots, not each other. This could be intentional design (extraction shooter where avoiding players is the meta) or a matchmaking issue where human player counts per lobby are too low to create PvP encounters. The Event Map's Kill vs BotKill markers make the imbalance obvious at a glance.

### 3. GrandRift and Lockdown have 3x the storm death rate of AmbroseValley
Storm death rates: AmbroseValley 3.4 %, GrandRift 9.6 %, Lockdown 9.2 %.
The Heatmap's "Storm Deaths" layer shows that on GrandRift and Lockdown, storm deaths cluster near specific map edges — suggesting the storm path on those maps leaves players less escape time or fewer safe routes. This is directly actionable for a level designer: widen the extraction corridor or adjust the storm boundary on those maps.
