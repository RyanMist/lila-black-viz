# -*- coding: utf-8 -*-
import time
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from data_loader import (
    load_all_data,
    get_match_summary,
    get_minimap_b64,
    EVENT_STYLES,
    HEATMAP_OPTIONS,
    DATES_ORDERED,
    MAP_CONFIG,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LILA BLACK – Player Behavior",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Tighten metric cards */
    div[data-testid="stMetric"] {
        background: #f0f2f6;
        border-radius: 8px;
        padding: 10px 14px;
        border: 1px solid #dde0e8;
    }
    /* Tab labels */
    button[data-baseweb="tab"] { font-size: 15px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
df_all = load_all_data()

if df_all.empty:
    st.error("No parquet files found. Run this app from inside the `player_data` folder.")
    st.stop()

match_summary = get_match_summary(df_all)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR – FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎮 LILA BLACK")
    st.caption("Player Behavior Analyzer")
    st.divider()

    # ── Map ──────────────────────────────────────────
    st.subheader("Map")
    sel_map = st.selectbox(
        "Select map",
        options=sorted(df_all["map_id"].unique()),
        label_visibility="collapsed",
    )

    # ── Date ─────────────────────────────────────────
    st.subheader("Date")
    avail_dates = sorted(
        df_all[df_all["map_id"] == sel_map]["date"].unique(),
        key=lambda d: DATES_ORDERED.index(d),
    )
    sel_dates = st.multiselect(
        "Dates",
        options=avail_dates,
        default=avail_dates,
        label_visibility="collapsed",
    )
    if not sel_dates:
        sel_dates = avail_dates

    st.divider()
    st.caption("Tip: Scroll / zoom the map with your mouse.\nPlayer and event filters are in the Event Map tab.")

# ─────────────────────────────────────────────────────────────────────────────
# BASE FILTERED DATA  (map + date only — shared by all tabs)
# Event-type / player-type filtering is done per-tab where relevant.
# ─────────────────────────────────────────────────────────────────────────────
df_map = df_all[
    (df_all["map_id"] == sel_map) &
    (df_all["date"].isin(sel_dates))
].copy()

df_matches = match_summary[
    (match_summary["map_id"] == sel_map) &
    (match_summary["date"].isin(sel_dates))
].copy()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"## {sel_map}")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Matches",       f"{len(df_matches):,}")
c2.metric("Human Players", f"{df_map[df_map['is_human']]['user_id'].nunique():,}")
c3.metric("Total Kills",   f"{(df_map['event'].isin(['Kill','BotKill'])).sum():,}")
c4.metric("Storm Deaths",  f"{(df_map['event'] == 'KilledByStorm').sum():,}")
c5.metric("Loot Events",   f"{(df_map['event'] == 'Loot').sum():,}")

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# SHARED FIGURE BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def make_map_figure(map_id: str, height: int = 680, animation: bool = False) -> go.Figure:
    """Blank Plotly figure with the minimap as background.

    Uses a cached base64 data-URL for the image so the browser can cache it
    across renders — prevents flicker when the figure is re-sent to the client.
    When animation=True adds bottom margin for the Plotly animation slider.
    """
    fig = go.Figure()
    img_src = get_minimap_b64(map_id)
    if img_src is not None:
        fig.add_layout_image(
            source=img_src,
            xref="x", yref="y",
            x=0, y=0,
            sizex=1024, sizey=1024,
            xanchor="left", yanchor="top",
            sizing="stretch",
            opacity=1.0,
            layer="below",
        )
    fig.update_xaxes(
        range=[0, 1024], showgrid=False, showticklabels=False,
        zeroline=False,
    )
    fig.update_yaxes(
        range=[0, 1024], showgrid=False, showticklabels=False,
        zeroline=False, scaleanchor="x", autorange="reversed",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=36, b=110 if animation else 0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#cccccc",
            borderwidth=1,
            font=dict(color="#1a1a2e", size=11),
            itemsizing="constant",
        ),
        height=height,
        dragmode="pan",
        modebar_remove=["select", "lasso", "autoscale"],
    )
    return fig


def add_event_traces(fig: go.Figure, df: pd.DataFrame):
    """Add one scatter trace per event type to `fig`."""
    for event_type, style in EVENT_STYLES.items():
        chunk = df[df["event"] == event_type].dropna(subset=["pixel_x", "pixel_y"])
        if chunk.empty:
            continue
        is_pos = event_type in ("Position", "BotPosition")
        fig.add_trace(go.Scattergl(
            x=chunk["pixel_x"],
            y=chunk["pixel_y"],
            mode="markers",
            name=style["label"],
            marker=dict(
                color=style["color"],
                symbol=style["symbol"],
                size=style["size"],
                opacity=0.30 if is_pos else 0.80,
                line=dict(width=0) if is_pos else dict(color="white", width=0.4),
            ),
            hovertemplate=(
                f"<b>{style['label']}</b><br>"
                "Player: %{customdata[0]}<br>"
                "Match: %{customdata[1]}…<br>"
                "<extra></extra>"
            ),
            customdata=chunk[["user_id", "match_id_short"]].values,
        ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# REPLAY FRAME BUILDER  (used by tab 3)
# ─────────────────────────────────────────────────────────────────────────────
_REPLAY_NON_POS = ["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]


def _build_frame(df_match: pd.DataFrame, t: float,
                 show_pos: bool, shown_events: set):
    """Return (trail_hx,hy, trail_bx,by, dot_hx,hy, dot_bx,by, event_xy).

    All movement trails are packed into two single traces (human / bot) using
    None separators, so the total trace count stays fixed across every frame.
    """
    trail_hx: list = []; trail_hy: list = []
    trail_bx: list = []; trail_by: list = []
    dot_hx:   list = []; dot_hy:   list = []
    dot_bx:   list = []; dot_by:   list = []

    if show_pos:
        pos_all = df_match[
            df_match["event"].isin(["Position", "BotPosition"])
        ].dropna(subset=["pixel_x", "pixel_y"])

        for uid, pdata in pos_all.groupby("user_id"):
            pdata = pdata.sort_values("scaled_ts")
            is_h  = bool(pdata["is_human"].iloc[0])
            trail = pdata[pdata["scaled_ts"] <= t].tail(80)
            if trail.empty:
                continue

            tx = trail["pixel_x"].tolist()
            ty = trail["pixel_y"].tolist()
            if is_h:
                if trail_hx: trail_hx.append(None); trail_hy.append(None)
                trail_hx += tx;  trail_hy += ty
            else:
                if trail_bx: trail_bx.append(None); trail_by.append(None)
                trail_bx += tx;  trail_by += ty

            # Interpolated current-position dot
            future = pdata[pdata["scaled_ts"] > t]
            p0 = trail.iloc[-1]
            if not future.empty:
                p1   = future.iloc[0]
                span = p1["scaled_ts"] - p0["scaled_ts"]
                frac = min((t - p0["scaled_ts"]) / span, 1.0) if span > 0 else 0.0
                ix   = float(p0["pixel_x"]) + frac * (float(p1["pixel_x"]) - float(p0["pixel_x"]))
                iy   = float(p0["pixel_y"]) + frac * (float(p1["pixel_y"]) - float(p0["pixel_y"]))
            else:
                ix, iy = float(p0["pixel_x"]), float(p0["pixel_y"])

            if is_h: dot_hx.append(ix); dot_hy.append(iy)
            else:    dot_bx.append(ix); dot_by.append(iy)

    # Events up to t
    df_t = df_match[
        (df_match["scaled_ts"] <= t) &
        (~df_match["event"].isin(["Position", "BotPosition"])) &
        (df_match["event"].isin(shown_events))
    ].dropna(subset=["pixel_x", "pixel_y"])

    event_xy = {
        evt: (df_t.loc[df_t["event"] == evt, "pixel_x"].tolist(),
              df_t.loc[df_t["event"] == evt, "pixel_y"].tolist())
        for evt in _REPLAY_NON_POS
    }
    return trail_hx, trail_hy, trail_bx, trail_by, dot_hx, dot_hy, dot_bx, dot_by, event_xy


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_map, tab_heat, tab_replay = st.tabs(
    ["🗺️  Event Map", "🔥  Heatmap", "▶️  Match Replay"]
)


# ══════════════════════════════════════════
# TAB 1 – EVENT MAP (aggregate all matches)
# ══════════════════════════════════════════
with tab_map:
    # ── Inline filters (scoped to this tab only) ──────
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        st.markdown("**Players**")
        em_humans = st.checkbox("Human players", value=True,  key="em_humans")
        em_bots   = st.checkbox("Bots",          value=True,  key="em_bots")
    with fc2:
        st.markdown("**Movement**")
        em_positions = st.checkbox("Movement trails", value=False, key="em_pos")
    with fc3:
        st.markdown("**Combat**")
        em_kills  = st.checkbox("Kills & deaths", value=True, key="em_kills")
        em_storm  = st.checkbox("Storm deaths",   value=True, key="em_storm")
    with fc4:
        st.markdown("**Items**")
        em_loot   = st.checkbox("Loot pickups",   value=True, key="em_loot")

    # Build the event-type set from the tab-local checkboxes
    shown_events: set[str] = set()
    if em_positions:
        if em_humans: shown_events.add("Position")
        if em_bots:   shown_events.add("BotPosition")
    if em_kills:
        if em_humans: shown_events.update(["Kill", "Killed"])
        if em_bots:   shown_events.update(["BotKill", "BotKilled"])
    if em_loot  and em_humans: shown_events.add("Loot")
    if em_storm and em_humans: shown_events.add("KilledByStorm")

    df_filtered = df_map[df_map["event"].isin(shown_events)].dropna(
        subset=["pixel_x", "pixel_y"]
    )

    st.divider()
    st.caption(
        f"**{len(df_filtered):,}** events across **{len(df_matches)}** matches"
    )

    if df_filtered.empty:
        st.info("No events match the current filters.")
    else:
        fig_map = make_map_figure(sel_map)
        add_event_traces(fig_map, df_filtered)
        st.plotly_chart(fig_map, use_container_width=True)


# ══════════════════════════════════════════
# TAB 2 – HEATMAP
# ══════════════════════════════════════════
with tab_heat:
    col_ctrl, col_viz = st.columns([1, 3])

    with col_ctrl:
        st.markdown("#### Layer")
        heat_choice = st.radio(
            "Heatmap layer",
            options=list(HEATMAP_OPTIONS.keys()),
            label_visibility="collapsed",
        )
        cfg_h = HEATMAP_OPTIONS[heat_choice]

        st.markdown("#### Options")
        heat_opacity  = st.slider("Opacity",     0.2, 1.0, 0.65, 0.05)
        heat_smoothing = st.slider("Smoothing",   5,  30,  15)
        split_by_date = st.checkbox("Split by date", value=False)

        df_heat_base = df_all[
            (df_all["map_id"] == sel_map) &
            (df_all["date"].isin(sel_dates)) &
            (df_all["event"].isin(cfg_h["events"]))
        ].dropna(subset=["pixel_x", "pixel_y"])
        st.caption(f"**{len(df_heat_base):,}** {cfg_h['label']}")

    with col_viz:
        if df_heat_base.empty:
            st.info("No data available for this layer and filter combination.")
        else:
            if split_by_date:
                date_groups = sorted(df_heat_base["date"].unique(), key=lambda d: DATES_ORDERED.index(d))
                cols = st.columns(len(date_groups))
                for i, date in enumerate(date_groups):
                    sub = df_heat_base[df_heat_base["date"] == date]
                    fig_h = make_map_figure(sel_map, height=380)
                    fig_h.add_trace(go.Histogram2dContour(
                        x=sub["pixel_x"], y=sub["pixel_y"],
                        colorscale=cfg_h["colorscale"],
                        reversescale=False,
                        opacity=heat_opacity,
                        showscale=False,
                        ncontours=heat_smoothing,
                        contours=dict(coloring="fill", showlabels=False),
                        line=dict(width=0),
                        name=date,
                    ))
                    fig_h.update_layout(title=dict(text=date, font=dict(color="#1a1a2e"), x=0.5))
                    with cols[i]:
                        st.plotly_chart(fig_h, use_container_width=True)
            else:
                fig_h = make_map_figure(sel_map)
                fig_h.add_trace(go.Histogram2dContour(
                    x=df_heat_base["pixel_x"],
                    y=df_heat_base["pixel_y"],
                    colorscale=cfg_h["colorscale"],
                    reversescale=False,
                    opacity=heat_opacity,
                    showscale=True,
                    ncontours=heat_smoothing,
                    contours=dict(coloring="fill", showlabels=False),
                    line=dict(width=0),
                    name=heat_choice,
                    colorbar=dict(
                        title=dict(text="Density", font=dict(color="#1a1a2e")),
                        tickfont=dict(color="#1a1a2e"),
                        bgcolor="rgba(255,255,255,0.7)",
                    ),
                ))
                st.plotly_chart(fig_h, use_container_width=True)


# ══════════════════════════════════════════
# TAB 3 – MATCH REPLAY
# ══════════════════════════════════════════
with tab_replay:
    if df_matches.empty:
        st.info("No matches found for the current filters.")
        st.stop()

    # ── Match selector ────────────────────────────────
    def fmt_match(row) -> str:
        # Raw ts span is write-time (~0.34 s), not real duration — omitted
        return (
            f"[{row['date']}]  {row['match_short']}...  ·  "
            f"{row['human_players']} humans  {row['bots']} bots  ·  "
            f"{row['kills']} kills  {row['loot']} loot  {row['deaths']} deaths"
        )

    df_matches_sorted = df_matches.sort_values(
        "date", key=lambda s: s.map(lambda d: DATES_ORDERED.index(d))
    )
    df_matches_sorted["label"] = df_matches_sorted.apply(fmt_match, axis=1)

    col_match, col_dur = st.columns([4, 1])
    with col_match:
        sel_label = st.selectbox(
            "Select a match",
            options=df_matches_sorted["label"].tolist(),
        )
    with col_dur:
        playback_dur = float(st.slider(
            "Playback duration (s)",
            min_value=20, max_value=30, value=25, step=1,
        ))

    sel_match_id = df_matches_sorted.loc[
        df_matches_sorted["label"] == sel_label, "match_id"
    ].iloc[0]

    # ── Load & scale match data ───────────────────────
    # rel_ts_norm is 0→1 per match, computed at load time from flush-window ordering.
    # We scale it to playback_dur seconds so the slider shows meaningful time.
    df_match = df_all[df_all["match_id"] == sel_match_id].copy()
    df_match["scaled_ts"] = df_match["rel_ts_norm"] * playback_dur
    df_match = df_match.sort_values("scaled_ts").reset_index(drop=True)
    match_duration = playback_dur

    # ── Player filter ─────────────────────────────────
    human_ids = sorted(df_match[df_match["is_human"]]["user_id"].unique())
    sel_players = st.multiselect(
        "Focus on specific players (blank = all humans + bots)",
        options=human_ids,
        default=[],
        format_func=lambda uid: uid[:8] + "...",
    )
    if sel_players:
        df_match = df_match[
            df_match["user_id"].isin(sel_players) | ~df_match["is_human"]
        ]

    st.divider()

    # ── Build Plotly animation (all frames computed once, browser animates) ──
    # No st.rerun() needed — animation runs entirely in JS after the first render.
    NUM_FRAMES  = 60
    time_steps  = np.linspace(0, match_duration, NUM_FRAMES + 1)

    with st.spinner("Building animation frames..."):
        # Compute initial state (last frame = all events visible)
        # Replay always shows all event types and movement trails
        _replay_events = set(EVENT_STYLES.keys())
        thx, thy, tbx, tby, dhx, dhy, dbx, dby, init_evts = _build_frame(
            df_match, match_duration, show_pos=True, shown_events=_replay_events
        )

        fig_r = make_map_figure(sel_map, height=760, animation=True)

        # ── Add fixed traces (indices must stay consistent across all frames) ──
        fig_r.add_trace(go.Scatter(                            # 0: human trail
            x=thx, y=thy, mode="lines", name="Human trail",
            line=dict(color="#1a6bb5", width=1.5), opacity=0.4,
            showlegend=False, hoverinfo="skip"))
        fig_r.add_trace(go.Scatter(                            # 1: bot trail
            x=tbx, y=tby, mode="lines", name="Bot trail",
            line=dict(color="#7f7f7f", width=1.5), opacity=0.4,
            showlegend=False, hoverinfo="skip"))
        fig_r.add_trace(go.Scatter(                            # 2: human dots
            x=dhx, y=dhy, mode="markers", name="Humans",
            marker=dict(color="#1a6bb5", size=10, symbol="circle",
                        line=dict(color="white", width=1.5)),
            showlegend=True))
        fig_r.add_trace(go.Scatter(                            # 3: bot dots
            x=dbx, y=dby, mode="markers", name="Bots",
            marker=dict(color="#7f7f7f", size=8, symbol="circle",
                        line=dict(color="white", width=1)),
            showlegend=True))
        for evt in _REPLAY_NON_POS:                            # 4-9: event types
            style = EVENT_STYLES.get(evt, {})
            ex, ey = init_evts[evt]
            fig_r.add_trace(go.Scatter(
                x=ex, y=ey, mode="markers",
                name=style.get("label", evt),
                marker=dict(color=style.get("color", "#888"),
                            symbol=style.get("symbol", "circle"),
                            size=style.get("size", 8),
                            line=dict(color="white", width=0.4)),
                showlegend=True))

        # ── Build all frames ──────────────────────────────────────────────────
        frames = []
        for t in time_steps:
            fthx, fthy, ftbx, ftby, fdhx, fdhy, fdbx, fdby, fevts = _build_frame(
                df_match, t, show_pos=True, shown_events=_replay_events
            )
            fdata = [
                go.Scatter(x=fthx, y=fthy),   # human trail
                go.Scatter(x=ftbx, y=ftby),   # bot trail
                go.Scatter(x=fdhx, y=fdhy),   # human dot
                go.Scatter(x=fdbx, y=fdby),   # bot dot
            ]
            for evt in _REPLAY_NON_POS:
                ex, ey = fevts[evt]
                fdata.append(go.Scatter(x=ex, y=ey))
            frames.append(go.Frame(data=fdata, name=f"{t:.2f}"))
        fig_r.frames = frames

        # ── Plotly animation controls (Play/Pause live in the chart) ─────────
        fig_r.update_layout(
            updatemenus=[dict(
                type="buttons", showactive=False,
                y=1.06, x=0.0, xanchor="left", yanchor="top",
                pad=dict(r=10, t=0),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#cccccc",
                font=dict(color="#1a1a2e"),
                buttons=[
                    dict(
                        label="  Play",
                        method="animate",
                        args=[None, {
                            "frame":      {"duration": 60, "redraw": True},
                            "fromcurrent": True,
                            "transition": {"duration": 50, "easing": "linear"},
                        }],
                    ),
                    dict(
                        label="  Pause",
                        method="animate",
                        args=[[None], {
                            "frame":      {"duration": 0, "redraw": False},
                            "mode":       "immediate",
                            "transition": {"duration": 0},
                        }],
                    ),
                ],
            )],
            sliders=[dict(
                active=NUM_FRAMES,           # start at last frame — all events visible
                currentvalue=dict(
                    prefix="T: ", suffix="s", visible=True,
                    xanchor="center", font=dict(size=12, color="#1a1a2e"),
                ),
                pad=dict(t=55, b=5),
                len=0.88, x=0.06,
                bgcolor="#f4f5f7",
                bordercolor="#cccccc",
                tickcolor="#1a1a2e",
                font=dict(color="#1a1a2e", size=10),
                steps=[dict(
                    args=[[f"{t:.2f}"], {
                        "frame":      {"duration": 0, "redraw": True},
                        "mode":       "immediate",
                        "transition": {"duration": 0},
                    }],
                    label=f"{t:.0f}",
                    method="animate",
                ) for t in time_steps],
            )],
        )

    st.plotly_chart(fig_r, use_container_width=True)

    # ── Per-player stat table ─────────────────────────
    with st.expander("Player stats for this match"):
        human_df = df_match[df_match["is_human"]].copy()
        if human_df.empty:
            st.write("No human players in this match.")
        else:
            stats = (
                human_df.groupby("user_id")["event"]
                .value_counts()
                .unstack(fill_value=0)
                .reset_index()
            )
            stat_cols = ["user_id"] + [
                c for c in ["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]
                if c in stats.columns
            ]
            stats = stats[[c for c in stat_cols if c in stats.columns]]
            stats["user_id"] = stats["user_id"].str[:8] + "…"
            st.dataframe(stats, use_container_width=True, hide_index=True)
