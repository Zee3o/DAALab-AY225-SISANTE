"""
generate_network.py
-------------------
Produces a self-contained node_map.html and (when a CSV is pre-loaded) a
path_stats.png.  All three libraries are used for their core strengths:

  pandas     – CSV loading, column normalisation, numeric coercion
  pyvis      – vis.js physics-option generation + node/edge data preparation
  matplotlib – hop-by-hop statistics chart (embedded as base64 in the HTML)

Expected CSV columns (header row required, order flexible):
    From Node | To Node | Distance (km) | Time (mins) | Fuel (Liters)

Usage:
    python generate_network.py                                     # drag & drop mode
    python generate_network.py network.csv                         # interactive node pick
    python generate_network.py network.csv --start A --end B
    python generate_network.py network.csv --criteria fuel --out-dir ./out
    python generate_network.py network.csv --mode tour --start A
    python generate_network.py network.csv --mode tour --start A --criteria fuel
"""

import argparse
import base64
import heapq
import json
import os
import re
import sys
import webbrowser
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from pyvis.network import Network


# ── Shared constants (mirror the JS side) ────────────────────────────────────
UNIT    = {"distance": "km",   "time": "mins", "fuel": "L"}
ICON    = {"distance": "📍",   "time": "⏱",   "fuel": "⛽"}
LABEL   = {"distance": "Distance (km)", "time": "Time (mins)", "fuel": "Fuel (L)"}
METRICS = ["distance", "time", "fuel"]
CHART_COLS = ["#4FC3F7", "#FFD740", "#00E676"]

# Column keyword → canonical name
_COL_KEYWORDS = {"from": "from", "to": "to", "distance": "distance",
                 "time": "time", "fuel": "fuel"}


# ════════════════════════════════════════════════════════════════════════════
# 1. pandas – CSV loading & validation
# ════════════════════════════════════════════════════════════════════════════
def load_graph(csv_path: str) -> pd.DataFrame:
    """
    Load the edge CSV with pandas.
    Matches columns by keyword so header order doesn't matter.
    Returns a clean DataFrame: from | to | distance | time | fuel
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    col_map = {
        col: canonical
        for col in df.columns
        for keyword, canonical in _COL_KEYWORDS.items()
        if keyword in col.lower()
    }

    missing = {"from", "to", "distance", "time", "fuel"} - set(col_map.values())
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    df = df.rename(columns=col_map)[["from", "to", "distance", "time", "fuel"]]
    df = df.dropna(subset=["from", "to"])
    df[["distance", "time", "fuel"]] = (
        df[["distance", "time", "fuel"]]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )
    df["from"] = df["from"].astype(str).str.strip()
    df["to"]   = df["to"].astype(str).str.strip()
    return df.reset_index(drop=True)


# ════════════════════════════════════════════════════════════════════════════
# 2. pyvis – vis.js options + node/edge data preparation
# ════════════════════════════════════════════════════════════════════════════
def _tooltip_table_rows(out_edges: pd.DataFrame) -> str:
    """Build inner <tr> rows for a node tooltip table using fast itertuples."""
    return "".join(
        f"<tr>"
        f"<td style='padding:2px 8px;color:#E0E0E0'>{r.to}</td>"
        f"<td style='padding:2px 8px;color:#4FC3F7'>{r.distance} km</td>"
        f"<td style='padding:2px 8px;color:#FFD740'>{r.time} min</td>"
        f"<td style='padding:2px 8px;color:#00E676'>{r.fuel} L</td>"
        f"</tr>"
        for r in out_edges.itertuples(index=False)
    )


_TOOLTIP_TH = (
    "<table style='margin-top:6px;font-size:11px;border-collapse:collapse'>"
    "<tr>"
    "<th style='padding:2px 8px;color:#607080'>To</th>"
    "<th style='padding:2px 8px;color:#4FC3F7'>km</th>"
    "<th style='padding:2px 8px;color:#FFD740'>min</th>"
    "<th style='padding:2px 8px;color:#00E676'>L</th>"
    "</tr>"
)


def prepare_graph_data(df: pd.DataFrame) -> dict:
    """
    Use pyvis Network to:
      a) Configure Barnes-Hut physics and extract the vis.js options JSON.
      b) Prepare node and edge data lists in vis.js format.
      c) Build tooltip HTML strings stored separately to avoid JSON escaping.

    Returns a dict ready to embed as JSON in the HTML template.
    """
    net = Network(directed=True, bgcolor="#0d0d0f", font_color="#E0E0E0")
    net.barnes_hut(
        gravity=-20000, central_gravity=0.3,
        spring_length=250, spring_strength=0.05, damping=0.09
    )

    all_nodes = sorted(pd.concat([df["from"], df["to"]]).unique().tolist())

    for node in all_nodes:
        net.add_node(node, label=node, color="#4FC3F7", size=28, title="")

    for row in df.itertuples(index=False):
        net.add_edge(row.from_, row.to, label="", title="", color="#AAAAAA", width=1)

    # ── Extract vis.js options via pyvis's generate_html ─────────────────
    vis_options: dict = {}
    try:
        raw_html = net.generate_html()
        m = re.search(r"var options = (\{.*?\})\s*;", raw_html, re.DOTALL)
        if m:
            vis_options = json.loads(m.group(1))
    except Exception:
        pass

    # ── Build tooltip HTML ────────────────────────────────────────────────
    node_tooltips: dict = {}
    for node in all_nodes:
        rows = _tooltip_table_rows(df[df["from"] == node])
        node_tooltips[node] = (
            f"<b style='font-size:14px;color:#E0E0E0'>{node}</b>"
            + (f"{_TOOLTIP_TH}{rows}</table>" if rows else "")
        )

    edge_tooltips: list = [
        f"<b style='color:#E0E0E0'>{r.from_} &rarr; {r.to}</b><br>"
        f"<span style='color:#4FC3F7'>📍 {r.distance} km</span><br>"
        f"<span style='color:#FFD740'>⏱ {r.time} mins</span><br>"
        f"<span style='color:#00E676'>⛽ {r.fuel} L</span>"
        for r in df.itertuples(index=False)
    ]

    return {
        "nodes_list":    all_nodes,
        "edges_data":    df.to_dict(orient="records"),
        "node_tooltips": node_tooltips,
        "edge_tooltips": edge_tooltips,
        "vis_options":   vis_options,
    }


# ════════════════════════════════════════════════════════════════════════════
# 3. Python Dijkstra — single-pair (path mode) + all-pairs (tour mode)
# ════════════════════════════════════════════════════════════════════════════
def _build_adjacency(df: pd.DataFrame) -> dict:
    """Pre-compute adjacency list from DataFrame for O(1) edge lookup."""
    adj: dict = {}
    for row in df.itertuples(index=False):
        adj.setdefault(row.from_, []).append((row.to, row.distance, row.time, row.fuel))
    return adj


def dijkstra(df: pd.DataFrame, start: str, end: str, weight: str):
    """Min-heap Dijkstra; returns (path, total_cost)."""
    adj: dict = {}
    for row in df.itertuples(index=False):
        w = float(getattr(row, weight))
        adj.setdefault(row.from_, []).append((row.to, w))

    dist: dict = {n: float("inf") for n in pd.concat([df["from"], df["to"]]).unique()}
    prev: dict = {n: None for n in dist}
    dist[start] = 0.0
    heap = [(0.0, start)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        if u == end:
            break
        for v, w in adj.get(u, []):
            alt = d + w
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    path: list = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    if not path or path[0] != start:
        return [], float("inf")
    return path, round(dist[end], 4)


def dijkstra_full(df: pd.DataFrame, start: str, weight: str) -> tuple:
    """
    Run Dijkstra from `start` to ALL nodes.
    Returns (dist_dict, prev_dict) for full path reconstruction.
    """
    adj: dict = {}
    for row in df.itertuples(index=False):
        w = float(getattr(row, weight))
        adj.setdefault(row.from_, []).append((row.to, w))

    all_nodes = pd.concat([df["from"], df["to"]]).unique()
    dist: dict = {n: float("inf") for n in all_nodes}
    prev: dict = {n: None for n in all_nodes}
    dist[start] = 0.0
    heap = [(0.0, start)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj.get(u, []):
            alt = d + w
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    return dist, prev



def reconstruct_sub_path(prev: dict, start: str, end: str) -> list:
    """Reconstruct path from prev-dict produced by dijkstra_full."""
    path: list = []
    cur = end
    while cur is not None:
        path.append(cur)
        if cur == start:
            break
        cur = prev.get(cur)
    path.reverse()
    return path if path and path[0] == start else []


def sssp_tour(df: pd.DataFrame, start: str, weight: str) -> tuple:
    """
    Single-Source Shortest Paths tour.
    Run Dijkstra once from `start`; find the cheapest path to every other
    node independently, then sum all those individual costs.

    Returns:
        node_results  – list of dicts {node, cost, path}, sorted cheapest first
        total_cost    – sum of all individual cheapest-path costs
        unreachable   – sorted list of nodes with no path from start
    """
    dist, prev = dijkstra_full(df, start, weight)
    all_nodes  = sorted(pd.concat([df["from"], df["to"]]).unique().tolist())

    node_results: list = []
    unreachable:  list = []
    total_cost:   float = 0.0

    for node in all_nodes:
        if node == start:
            continue
        d = dist.get(node, float("inf"))
        if d == float("inf"):
            unreachable.append(node)
            continue
        path = reconstruct_sub_path(prev, start, node)
        total_cost += d
        node_results.append({"node": node, "cost": round(d, 4), "path": path})

    node_results.sort(key=lambda x: x["cost"])
    return node_results, round(total_cost, 4), unreachable


def sum_path(df: pd.DataFrame, path: list) -> dict:
    """Sum all metrics along a path using a pre-built edge lookup dict."""
    lookup = {(r.from_, r.to): r for r in df.itertuples(index=False)}
    totals = {m: 0.0 for m in METRICS}
    for a, b in zip(path[:-1], path[1:]):
        row = lookup.get((a, b))
        if row:
            for m in METRICS:
                totals[m] += float(getattr(row, m))
    return {k: round(v, 4) for k, v in totals.items()}


# ════════════════════════════════════════════════════════════════════════════
# 4. matplotlib – path statistics chart → base64 PNG
# ════════════════════════════════════════════════════════════════════════════
def make_chart_b64(df: pd.DataFrame, path: list, weight: str) -> str:
    """Generate a dark-mode path stats chart and return it as a base64 PNG string."""
    C_BG, C_PANEL = "#0d0d0f", "#141418"

    hops       = list(zip(path[:-1], path[1:]))
    hop_lbls   = [f"{a}→{b}" for a, b in hops]
    lookup     = {(r.from_, r.to): r for r in df.itertuples(index=False)}
    hop_edges  = [lookup.get(pair) for pair in hops]
    totals     = sum_path(df, path)

    fig = plt.figure(figsize=(14, 8.5), facecolor=C_BG)
    fig.suptitle(
        f"Path Analysis  ·  {path[0]} → {path[-1]}  ·  Optimised by {LABEL[weight]}",
        color="#E0E0E0", fontsize=12, fontweight="bold", y=0.97
    )

    ax1 = fig.add_axes([0.05, 0.52, 0.53, 0.37])
    ax1.set_facecolor(C_PANEL)
    if hop_lbls:
        bottoms = [0.0] * len(hop_lbls)
        for metric, colour in zip(METRICS, CHART_COLS):
            vals = [float(getattr(e, metric)) if e is not None else 0.0 for e in hop_edges]
            bars = ax1.bar(hop_lbls, vals, bottom=bottoms, color=colour, alpha=0.85,
                           label=f"{metric.capitalize()} ({UNIT[metric]})",
                           edgecolor=C_BG, linewidth=0.5)
            for bar, v in zip(bars, vals):
                if v > 0:
                    ax1.text(bar.get_x() + bar.get_width() / 2,
                             bar.get_y() + bar.get_height() / 2,
                             str(v), ha="center", va="center",
                             fontsize=7.5, color="#0d0d0f", fontweight="bold")
            bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax1.set_title("Hop-by-Hop Breakdown (Stacked)", color="#90A4AE", fontsize=9, pad=5)
    ax1.tick_params(colors="#607080", labelsize=7.5)
    plt.setp(ax1.get_xticklabels(), rotation=22, ha="right")
    for sp in ax1.spines.values(): sp.set_edgecolor("#2a2a2a")
    ax1.legend(fontsize=7.5, labelcolor="#ccc",
               facecolor="#1c1c22", edgecolor="#333", loc="upper right")

    ax2 = fig.add_axes([0.63, 0.52, 0.34, 0.37])
    ax2.set_facecolor(C_PANEL)
    ax2.axis("off")
    ax2.set_title("Route Totals", color="#90A4AE", fontsize=9, pad=5)
    for i, (metric, colour) in enumerate(zip(METRICS, CHART_COLS)):
        ypos = 0.76 - i * 0.30
        ax2.add_patch(mpatches.FancyBboxPatch(
            (0.04, ypos - 0.07), 0.92, 0.24,
            boxstyle="round,pad=0.02", facecolor="#1c1c22",
            edgecolor=colour, linewidth=1.4,
            transform=ax2.transAxes, zorder=2
        ))
        ax2.text(0.12, ypos + 0.06, ICON[metric],
                 transform=ax2.transAxes, fontsize=18, va="center", zorder=3)
        ax2.text(0.30, ypos + 0.10, str(totals[metric]),
                 transform=ax2.transAxes, fontsize=20, fontweight="bold",
                 color=colour, va="center", zorder=3)
        ax2.text(0.30, ypos + 0.00, UNIT[metric],
                 transform=ax2.transAxes, fontsize=8.5, color="#607080",
                 va="center", zorder=3)
        ax2.text(0.65, ypos + 0.05, metric.capitalize(),
                 transform=ax2.transAxes, fontsize=8.5, color="#90A4AE",
                 va="center", zorder=3)
    opt_i = METRICS.index(weight)
    ax2.text(0.96, 0.76 - opt_i * 0.30 + 0.17, "★ optimised",
             transform=ax2.transAxes, fontsize=7.5, color=CHART_COLS[opt_i],
             ha="right", va="top", zorder=3)

    for i, (metric, colour) in enumerate(zip(METRICS, CHART_COLS)):
        ax = fig.add_axes([0.05 + i * 0.32, 0.06, 0.27, 0.35])
        ax.set_facecolor(C_PANEL)
        all_vals = df[metric].dropna().values
        ax.hist(all_vals, bins=min(15, max(1, len(all_vals))),
                color=colour, alpha=0.72, edgecolor=C_BG, linewidth=0.4)
        path_vals = [float(getattr(e, metric)) for e in hop_edges if e is not None]
        for pv in path_vals:
            ax.axvline(pv, color=colour, linewidth=1.6, linestyle="--", alpha=0.9)
        ax.set_title(f"All-Edge {LABEL[metric]}", color="#90A4AE", fontsize=8.5, pad=4)
        ax.tick_params(colors="#607080", labelsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor("#2a2a2a")
        ax.legend(
            handles=[mpatches.Patch(color=colour, linestyle="--", fill=False,
                                    label="Path edges")],
            fontsize=7, labelcolor="#ccc", facecolor="#1c1c22", edgecolor="#333"
        )

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ════════════════════════════════════════════════════════════════════════════
# 4b. matplotlib – TOUR (SSSP) statistics chart → base64 PNG
# ════════════════════════════════════════════════════════════════════════════
def make_tour_chart_b64(df: pd.DataFrame, start: str, node_results: list,
                        weight: str, unreachable: list) -> str:
    """
    Generate a dark-mode tour stats chart for SSSP mode.
    Each bar = cheapest path cost from `start` to that destination node.
    node_results is a list of {node, cost, path} dicts, sorted by cost.
    """
    C_BG, C_PANEL = "#0d0d0f", "#141418"
    lookup = {(r.from_, r.to): r for r in df.itertuples(index=False)}

    # Per-destination metric sums along each individual shortest path
    dest_lbls: list = [r["node"] for r in node_results]
    dest_metric_vals: dict = {m: [] for m in METRICS}
    for res in node_results:
        sums = {m: 0.0 for m in METRICS}
        path = res["path"]
        for a, b in zip(path[:-1], path[1:]):
            row = lookup.get((a, b))
            if row:
                for m in METRICS:
                    sums[m] += float(getattr(row, m))
        for m in METRICS:
            dest_metric_vals[m].append(round(sums[m], 2))

    # Grand totals = sum across all individual paths
    totals = {m: round(sum(dest_metric_vals[m]), 4) for m in METRICS}

    fig = plt.figure(figsize=(14, 8.5), facecolor=C_BG)
    n_dest = len(node_results)
    fig.suptitle(
        f"Tour Analysis  ·  Start: {start}  ·  {n_dest} destinations reached"
        f"  ·  Optimised by {LABEL[weight]}"
        + (f"  ·  ⚠ {len(unreachable)} unreachable" if unreachable else ""),
        color="#E0E0E0", fontsize=11, fontweight="bold", y=0.97
    )

    # ── Top-left: per-destination stacked bars (sorted cheapest → costliest) ─
    ax1 = fig.add_axes([0.05, 0.52, 0.53, 0.37])
    ax1.set_facecolor(C_PANEL)
    if dest_lbls:
        bottoms = [0.0] * len(dest_lbls)
        for metric, colour in zip(METRICS, CHART_COLS):
            vals = dest_metric_vals[metric]
            bars = ax1.bar(dest_lbls, vals, bottom=bottoms, color=colour, alpha=0.85,
                           label=f"{metric.capitalize()} ({UNIT[metric]})",
                           edgecolor=C_BG, linewidth=0.5)
            for bar, v in zip(bars, vals):
                if v > 0:
                    ax1.text(bar.get_x() + bar.get_width() / 2,
                             bar.get_y() + bar.get_height() / 2,
                             str(v), ha="center", va="center",
                             fontsize=7, color="#0d0d0f", fontweight="bold")
            bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax1.set_title(f"Cost from {start} → Each Destination (Stacked, Cheapest First)",
                  color="#90A4AE", fontsize=9, pad=5)
    ax1.tick_params(colors="#607080", labelsize=7.5)
    plt.setp(ax1.get_xticklabels(), rotation=28, ha="right")
    for sp in ax1.spines.values(): sp.set_edgecolor("#2a2a2a")
    ax1.legend(fontsize=7.5, labelcolor="#ccc",
               facecolor="#1c1c22", edgecolor="#333", loc="upper left")

    # ── Top-right: grand totals card ─────────────────────────────────────
    ax2 = fig.add_axes([0.63, 0.52, 0.34, 0.37])
    ax2.set_facecolor(C_PANEL)
    ax2.axis("off")
    ax2.set_title("Summed Totals (All Destinations)", color="#90A4AE", fontsize=9, pad=5)
    for i, (metric, colour) in enumerate(zip(METRICS, CHART_COLS)):
        ypos = 0.76 - i * 0.30
        ax2.add_patch(mpatches.FancyBboxPatch(
            (0.04, ypos - 0.07), 0.92, 0.24,
            boxstyle="round,pad=0.02", facecolor="#1c1c22",
            edgecolor=colour, linewidth=1.4,
            transform=ax2.transAxes, zorder=2
        ))
        ax2.text(0.12, ypos + 0.06, ICON[metric],
                 transform=ax2.transAxes, fontsize=18, va="center", zorder=3)
        ax2.text(0.30, ypos + 0.10, str(totals[metric]),
                 transform=ax2.transAxes, fontsize=20, fontweight="bold",
                 color=colour, va="center", zorder=3)
        ax2.text(0.30, ypos + 0.00, UNIT[metric],
                 transform=ax2.transAxes, fontsize=8.5, color="#607080",
                 va="center", zorder=3)
        ax2.text(0.65, ypos + 0.05, metric.capitalize(),
                 transform=ax2.transAxes, fontsize=8.5, color="#90A4AE",
                 va="center", zorder=3)
    opt_i = METRICS.index(weight)
    ax2.text(0.96, 0.76 - opt_i * 0.30 + 0.17, "★ optimised",
             transform=ax2.transAxes, fontsize=7.5, color=CHART_COLS[opt_i],
             ha="right", va="top", zorder=3)

    # ── Bottom row: distribution histograms with per-destination cost markers ─
    for i, (metric, colour) in enumerate(zip(METRICS, CHART_COLS)):
        ax = fig.add_axes([0.05 + i * 0.32, 0.06, 0.27, 0.35])
        ax.set_facecolor(C_PANEL)
        all_edge_vals = df[metric].dropna().values
        ax.hist(all_edge_vals, bins=min(15, max(1, len(all_edge_vals))),
                color=colour, alpha=0.72, edgecolor=C_BG, linewidth=0.4)
        for pv in dest_metric_vals[metric]:
            ax.axvline(pv, color=colour, linewidth=1.4, linestyle="--", alpha=0.7)
        ax.set_title(f"All-Edge {LABEL[metric]}", color="#90A4AE", fontsize=8.5, pad=4)
        ax.tick_params(colors="#607080", labelsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor("#2a2a2a")
        ax.legend(
            handles=[mpatches.Patch(color=colour, linestyle="--", fill=False,
                                    label="Dest costs")],
            fontsize=7, labelcolor="#ccc", facecolor="#1c1c22", edgecolor="#333"
        )

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ════════════════════════════════════════════════════════════════════════════
# 5. HTML generation
# ════════════════════════════════════════════════════════════════════════════
def generate_html(graph_data: dict = None, chart_b64: str = None) -> str:
    """
    Build the complete self-contained HTML.
    graph_data  – dict from prepare_graph_data(); None = drag-and-drop mode.
    chart_b64   – matplotlib PNG as base64 string; None = no chart panel.
    """
    embedded = "null"
    vis_opts = "{}"
    if graph_data:
        payload = {k: graph_data[k] for k in
                   ("nodes_list", "edges_data", "node_tooltips", "edge_tooltips")}
        embedded = json.dumps(payload)
        vis_opts = json.dumps(graph_data.get("vis_options", {}))

    chart_html = ""
    if chart_b64:
        chart_html = (
            '<div id="chart-panel">'
            '<div class="divider"></div>'
            '<div id="chart-toggle" onclick="toggleChart()">'
            '<span>&#128202; Path Statistics Chart</span>'
            '<span id="chart-arrow" style="font-size:10px">&#9650;</span>'
            '</div>'
            '<div id="chart-content">'
            f'<img src="data:image/png;base64,{chart_b64}" '
            'style="width:100%;border-radius:8px;margin-top:8px;display:block;"/>'
            '</div>'
            '</div>'
        )

    return (_HTML_TEMPLATE
            .replace("__EMBEDDED_DATA__", embedded)
            .replace("__VIS_OPTIONS__",   vis_opts)
            .replace("__CHART_SECTION__", chart_html))


# ════════════════════════════════════════════════════════════════════════════
# 6. HTML template
#    __EMBEDDED_DATA__  ->  JSON object or null
#    __VIS_OPTIONS__    ->  vis.js options JSON from pyvis
#    __CHART_SECTION__  ->  optional chart panel HTML
# ════════════════════════════════════════════════════════════════════════════
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Network Path Finder</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link  href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0d0f;--panel-bg:#141418;--panel-border:rgba(255,255,255,0.07);
  --accent:#4FC3F7;--gold:#FFD740;--green:#00E676;--red:#FF5252;
  --purple:#CE93D8;--orange:#FFAB40;
  --text:#E0E0E0;--muted:#607080;--font:'Segoe UI',system-ui,sans-serif;
  --path-label:#FFFFFF;--path-label-stroke:#000000;
}
html,body{height:100%;width:100%;background:var(--bg);color:var(--text);
  font-family:var(--font);overflow:hidden}

#network-container{position:fixed;inset:0;background:var(--bg)}
.vis-tooltip{display:none !important}

#custom-tooltip{
  position:fixed;background:#141418;
  border:1px solid rgba(79,195,247,.35);
  border-radius:8px;padding:10px 14px;font-size:12px;color:#E0E0E0;
  pointer-events:none;z-index:2000;display:none;max-width:280px;
  box-shadow:0 6px 24px rgba(0,0,0,.75);line-height:1.7;
}

#panel{
  position:fixed;top:20px;left:20px;width:310px;
  max-height:calc(100vh - 40px);overflow-y:auto;
  background:var(--panel-bg);border:1px solid var(--panel-border);
  border-radius:14px;padding:22px 20px;
  box-shadow:0 8px 40px rgba(0,0,0,.7);
  scrollbar-width:thin;scrollbar-color:#333 transparent;z-index:10;
}
#panel h3{font-size:17px;font-weight:700;letter-spacing:.5px;
  color:var(--accent);margin-bottom:14px}

/* ── Mode tabs ── */
.mode-tabs{
  display:flex;gap:5px;margin-bottom:14px;
  background:#111116;border-radius:10px;padding:4px;
  border:1px solid rgba(255,255,255,.06);
}
.mode-tab{
  flex:1;padding:7px 6px;border:none;border-radius:7px;
  font-size:11.5px;font-weight:700;cursor:pointer;
  background:transparent;color:var(--muted);
  transition:background .15s,color .15s;letter-spacing:.2px;
  white-space:nowrap;
}
.mode-tab.active{background:var(--accent);color:#001a2e}
.mode-tab:hover:not(.active){
  background:rgba(79,195,247,.1);color:var(--accent)}
.mode-tab:disabled{opacity:.3;cursor:not-allowed}

/* ── Drop zone ── */
#drop-zone{
  border:2px dashed rgba(79,195,247,.35);border-radius:10px;
  padding:22px 16px;text-align:center;cursor:pointer;
  transition:border-color .2s,background .2s;
  margin-bottom:16px;user-select:none;
}
#drop-zone:hover,#drop-zone.drag-over{
  border-color:var(--accent);background:rgba(79,195,247,.07)}
#drop-zone svg{display:block;margin:0 auto 10px;opacity:.55}
#drop-zone p{font-size:13px;color:#90A4AE;line-height:1.5}
#drop-zone span{color:var(--accent);font-weight:600;cursor:pointer}
#file-input{display:none}
#file-status{font-size:12px;text-align:center;margin-bottom:12px;
  min-height:16px;color:var(--green);word-break:break-all}
#file-status.error{color:var(--red)}

.divider{border:none;border-top:1px solid var(--panel-border);margin:14px 0}

/* ── Shared controls ── */
label{display:block;font-size:11px;font-weight:700;letter-spacing:1.1px;
  text-transform:uppercase;color:var(--muted);margin-bottom:5px}
select{
  width:100%;padding:9px 11px;margin-bottom:13px;
  background:#1c1c22;color:var(--text);
  border:1px solid rgba(255,255,255,0.1);border-radius:7px;
  font-size:14px;outline:none;cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23607080' d='M1 1l5 5 5-5'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
}
select:focus{border-color:var(--accent)}
select:disabled{opacity:.35;cursor:not-allowed}
button{width:100%;padding:10px;border:none;border-radius:7px;
  font-size:14px;font-weight:700;cursor:pointer;
  transition:background .15s,transform .1s}
button:active{transform:scale(.98)}

/* ── Path mode ── */
#find-btn{background:var(--accent);color:#002233;margin-bottom:8px}
#find-btn:hover{background:#29B6F6}
#find-btn:disabled{opacity:.35;cursor:not-allowed}
#reset-btn{background:#1e2832;color:#90A4AE;font-size:12px;
  padding:7px;display:none}
#reset-btn:hover{background:#263342}

/* ── Tour mode ── */
#tour-find-btn{
  background:linear-gradient(135deg,var(--purple),#9C4DCC);
  color:#fff;margin-bottom:8px}
#tour-find-btn:hover{filter:brightness(1.1)}
#tour-find-btn:disabled{opacity:.35;cursor:not-allowed}
#tour-reset-btn{background:#1e2832;color:#90A4AE;font-size:12px;
  padding:7px;display:none}
#tour-reset-btn:hover{background:#263342}

/* ── Show-all toggle ── */
.toggle-row{
  display:flex;align-items:center;justify-content:space-between;
  background:#1c1c22;border:1px solid rgba(255,255,255,0.08);
  border-radius:8px;padding:9px 12px;margin-bottom:13px;
  cursor:pointer;user-select:none;transition:border-color .2s,background .2s;
}
.toggle-row:hover{border-color:rgba(79,195,247,.3);background:#1e1e28}
.toggle-row.disabled{opacity:.35;cursor:not-allowed;pointer-events:none}
.toggle-label{display:flex;align-items:center;gap:7px;
  font-size:12px;font-weight:600;color:var(--text);letter-spacing:.2px}
.toggle-label .t-icon{font-size:14px}
.pill{position:relative;width:36px;height:20px;background:#2a2a38;
  border-radius:20px;transition:background .2s;flex-shrink:0}
.pill::after{content:'';position:absolute;top:3px;left:3px;
  width:14px;height:14px;border-radius:50%;background:#607080;
  transition:transform .2s,background .2s}
.toggle-row.active .pill{background:rgba(79,195,247,.25);
  border:1px solid rgba(79,195,247,.5)}
.toggle-row.active .pill::after{transform:translateX(16px);background:var(--accent)}

/* ── Same-node warning ── */
#same-node-tip{
  display:none;align-items:center;gap:8px;
  background:rgba(255,82,82,.12);border:1px solid rgba(255,82,82,.4);
  border-radius:8px;padding:9px 12px;margin-bottom:10px;
  animation:fadeUp .25s ease;
}
#same-node-tip .tip-icon{font-size:16px;flex-shrink:0}
#same-node-tip .tip-text{font-size:12px;font-weight:600;
  color:#FF8A80;line-height:1.4}

/* ── Criteria badge ── */
.criteria-badge{
  display:inline-block;background:rgba(79,195,247,.15);
  border:1px solid rgba(79,195,247,.3);border-radius:20px;
  padding:1px 8px;font-size:10px;font-weight:700;color:var(--accent);
  letter-spacing:.5px;margin-left:6px;vertical-align:middle;
}

/* ── Path result cards ── */
#result{
  display:none;margin-top:14px;padding:14px 16px;
  background:linear-gradient(135deg,#0f1f0f,#0f0f1f);
  border:1px solid rgba(255,215,64,.4);border-radius:10px;
  box-shadow:0 0 18px rgba(255,215,64,.18);animation:fadeUp .35s ease;
}
#result-secondary{
  display:none;margin-top:8px;padding:12px 14px;
  .result-card,
.tour-result,
.secondary-card {
  background: linear-gradient(145deg, #1e293b, #111827);
  border-radius: 14px;
  padding: 18px;
  box-shadow:
    0 10px 30px rgba(0,0,0,0.5),
    inset 0 1px 1px rgba(255,255,255,0.05);
}
}

/* ── Tour result cards ── */
#tour-result{
  display:none;margin-top:14px;padding:14px 16px;
  background:linear-gradient(135deg,#160d1e,#0f0f1f);
  border:1px solid rgba(206,147,216,.4);border-radius:10px;
  box-shadow:0 0 18px rgba(206,147,216,.15);animation:fadeUp .35s ease;
}
#tour-result-secondary{
  display:none;margin-top:8px;padding:12px 14px;
  background:#111118;border:1px solid rgba(255,255,255,0.07);
  border-radius:10px;animation:fadeUp .4s ease;
}
#tour-unreachable{
  display:none;margin-top:8px;padding:10px 13px;
  background:rgba(255,82,82,.08);border:1px solid rgba(255,82,82,.3);
  border-radius:8px;animation:fadeUp .4s ease;
}
#tour-unreachable .u-title{
  font-size:10px;font-weight:700;letter-spacing:1.2px;
  text-transform:uppercase;color:#FF5252;margin-bottom:6px;
}
#tour-unreachable .u-nodes{font-size:12px;color:#FF8A80;line-height:1.6}

/* Tour visit list */
.tour-visit-list{
  max-height:180px;overflow-y:auto;margin-top:10px;
  scrollbar-width:thin;scrollbar-color:#333 transparent;
}
.tour-stop{
  display:flex;align-items:center;gap:8px;
  padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);
}
.tour-stop:last-child{border-bottom:none}
.stop-num{
  min-width:22px;height:22px;border-radius:50%;
  background:rgba(206,147,216,.2);border:1px solid rgba(206,147,216,.4);
  display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:800;color:var(--purple);flex-shrink:0;
}
.stop-num.start-num{
  background:rgba(0,230,118,.2);border-color:rgba(0,230,118,.4);color:var(--green)}
.stop-node-col{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
.stop-node{font-size:13px;font-weight:700;color:#E0E0E0}
.stop-node.start-node{color:var(--green)}
.stop-via{font-size:10px;color:#3a5060;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;letter-spacing:.1px}
.stop-leg{
  font-size:10px;color:var(--muted);text-align:right;
  white-space:nowrap;flex-shrink:0;
}
.stop-leg span{
  display:inline-block;background:rgba(206,147,216,.1);
  border:1px solid rgba(206,147,216,.2);
  border-radius:10px;padding:1px 6px;color:var(--purple);
  font-weight:700;
}
.heuristic-badge{
  display:inline-block;background:rgba(206,147,216,.12);
  border:1px solid rgba(206,147,216,.25);border-radius:12px;
  padding:1px 7px;font-size:9px;font-weight:700;
  color:var(--purple);letter-spacing:.5px;margin-left:6px;vertical-align:middle;
}

/* Shared result sub-elements */
#result-secondary .sec-label,
#tour-result-secondary .sec-label{
  font-size:10px;font-weight:700;letter-spacing:1.4px;
  text-transform:uppercase;color:var(--muted);margin-bottom:10px;
}
.sec-metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.sec-metric-item{
  background:#1a1a22;border:1px solid rgba(255,255,255,0.06);
  border-radius:8px;padding:9px 10px;
}
.sec-metric-item .sm-icon{font-size:15px;margin-bottom:3px}
.sec-metric-item .sm-value{font-size:18px;font-weight:800;
  color:#7A8FA0;line-height:1}
.sec-metric-item .sm-unit{font-size:10px;color:#3a4a58;
  font-weight:600;letter-spacing:.5px;margin-top:2px}
.sec-metric-item .sm-name{font-size:10px;color:#3d5060;
  font-weight:700;letter-spacing:.8px;text-transform:uppercase;margin-top:1px}

@keyframes fadeUp{
  from{opacity:0;transform:translateY(-6px)}
  to  {opacity:1;transform:translateY(0)}
}
.result-label{font-size:10px;font-weight:700;letter-spacing:1.6px;
  text-transform:uppercase;color:var(--gold);opacity:.75;margin-bottom:9px}
.tour-result-label{font-size:10px;font-weight:700;letter-spacing:1.6px;
  text-transform:uppercase;color:var(--purple);opacity:.75;margin-bottom:9px}
.path-line{display:flex;flex-wrap:wrap;align-items:center;gap:3px;
  font-size:13px;font-weight:600;line-height:1.8}
.node-chip{padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: .5px;
  background: #334155;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4);}
.node-chip.start{background: #22c55e;
  color: #022c22;}
.node-chip.end{background: #ef4444;
  color: #450a0a;}
.edge-badge{
  display:inline-flex;align-items:center;gap:3px;
  background:rgba(255,215,64,.1);border:1px solid rgba(255,215,64,.3);
  border-radius:20px;padding:1px 7px;font-size:11px;
  font-weight:700;color:var(--gold);
}
.arrow{color:var(--gold);font-weight:900;font-size:11px}
.metric-row{display:flex;align-items:center;gap:8px;margin-top:11px}
.metric-icon{font-size:18px}
.metric-value{font-size:24px;font-weight:800;color:var(--gold);
  text-shadow:0 0 12px rgba(255,215,64,.55)}
.tour-metric-value{font-size:24px;font-weight:800;color:var(--purple);
  text-shadow:0 0 12px rgba(206,147,216,.45)}
.metric-unit{font-size:13px;color:var(--muted)}
.hop-count{margin-top:7px;font-size:11px;color:var(--muted)}

/* Chart panel */
#chart-toggle{
  display:flex;align-items:center;justify-content:space-between;
  cursor:pointer;font-size:12px;font-weight:700;color:#90A4AE;
  padding:8px 2px;user-select:none;letter-spacing:.3px;
}
#chart-toggle:hover{color:var(--accent)}
#chart-content{overflow:hidden;
  max-height:1200px;transition:max-height .3s ease}
#chart-content.collapsed{max-height:0}

/* Empty overlay */
#overlay{
  position:fixed;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  pointer-events:none;z-index:5;gap:12px;
}
#overlay p{font-size:15px;color:rgba(255,255,255,.18);letter-spacing:.3px}

/* Calculating spinner for tour */
#tour-computing{
  display:none;align-items:center;gap:10px;
  background:rgba(206,147,216,.08);border:1px solid rgba(206,147,216,.2);
  border-radius:8px;padding:10px 13px;margin-bottom:10px;
}
#tour-computing .spin{
  width:16px;height:16px;border:2px solid rgba(206,147,216,.3);
  border-top-color:var(--purple);border-radius:50%;
  animation:spin .7s linear infinite;flex-shrink:0;
}
@keyframes spin{to{transform:rotate(360deg)}}
#tour-computing span{font-size:12px;color:var(--purple);font-weight:600}
</style>
</head>
<body>

<div id="custom-tooltip"></div>

<div id="overlay">
  <svg width="64" height="64" viewBox="0 0 24 24" fill="none"
       stroke="rgba(255,255,255,.12)" stroke-width="1.2"
       stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="5" r="2"/><circle cx="5"  cy="19" r="2"/>
    <circle cx="19" cy="19" r="2"/>
    <line x1="12" y1="7"  x2="5"  y2="17"/>
    <line x1="12" y1="7"  x2="19" y2="17"/>
    <line x1="7"  y1="19" x2="17" y2="19"/>
  </svg>
  <p>Upload a CSV to visualise your network</p>
</div>

<div id="network-container"></div>

<div id="panel">
  <h3>&#11041; Network Path Finder</h3>

  <!-- Drop zone -->
  <div id="drop-zone">
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
         stroke="#4FC3F7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
    <p>Drag &amp; drop a CSV here<br/>or <span id="browse-link">browse files</span></p>
  </div>
  <input type="file" id="file-input" accept=".csv"/>
  <div id="file-status"></div>

  <hr class="divider"/>

  <!-- Mode tabs -->
  <div class="mode-tabs">
    <button class="mode-tab active" data-mode="path" onclick="switchMode('path')"
            id="tab-path">&#128269; Path Finder</button>
    <button class="mode-tab" data-mode="tour" onclick="switchMode('tour')"
            id="tab-tour" disabled>&#128506; Tour Planner</button>
  </div>

  <!-- Shared controls -->
  <label>
    Optimise By
    <span class="criteria-badge" id="criteria-badge">km</span>
  </label>
  <select id="criteria" disabled>
    <option value="distance">Distance (km)</option>
    <option value="time">Time (mins)</option>
    <option value="fuel">Fuel (Liters)</option>
  </select>

  <div id="show-all-toggle" class="toggle-row disabled" onclick="toggleShowAll()">
    <span class="toggle-label">
      <span class="t-icon">&#128065;</span>
      Show All Values
    </span>
    <span class="pill" id="toggle-pill"></span>
  </div>

  <!-- ════ PATH FINDER SECTION ════ -->
  <div id="path-section">
    <label>Start Node</label>
    <select id="start" disabled></select>

    <label>End Node</label>
    <select id="end" disabled></select>

    <div id="same-node-tip">
      <span class="tip-icon">&#9888;&#65039;</span>
      <span class="tip-text">Start and End nodes must be different to find a path.</span>
    </div>

    <button id="find-btn" disabled onclick="findPath()">Find Shortest Path</button>

    <div id="result"></div>
    <div id="result-secondary"></div>
    <button id="reset-btn" onclick="resetAll()">&#10005; Clear Highlights</button>
  </div>

  <!-- ════ TOUR PLANNER SECTION ════ -->
  <div id="tour-section" style="display:none">
    <label>Start Node</label>
    <select id="tour-start" disabled></select>

    <div id="tour-computing">
      <div class="spin"></div>
      <span>Computing cheapest tour&hellip;</span>
    </div>

    <button id="tour-find-btn" disabled onclick="findTour()">
      &#128506; Find Cheapest Tour
    </button>

    <div id="tour-result"></div>
    <div id="tour-result-secondary"></div>
    <div id="tour-unreachable"></div>
    <button id="tour-reset-btn" onclick="resetTour()">&#10005; Clear Tour</button>
  </div>

  __CHART_SECTION__
</div>

<script>
// ── Colour tokens ─────────────────────────────────────────────────────────
const C = {
  nodeDef: "#5DADE2",
  nodeDim: "#1f2937",
  edgeDef: "#9CA3AF",
  edgeDim: "#2c3440",

  pathNode: "#FFD166",
  pathEdge: "#FFC300",

  tourNode: "#C084FC",
  tourEdge: "#A855F7",

  start: "#22C55E",
  end: "#EF4444",

  fontDim: "#9CA3AF",
  pathLabel: "#ffffff",
  pathLabelStroke: "#000000"
};

const UNIT  = {distance:"km",   time:"mins", fuel:"L"};
const ICON  = {distance:"📍",  time:"⏱",   fuel:"⛽"};
const LABEL = {distance:"Total Distance", time:"Total Time", fuel:"Total Fuel"};
const BADGE = {distance:"km",  time:"mins", fuel:"L"};
const ALL_WEIGHTS = ["distance","time","fuel"];

// ── Cached DOM refs ───────────────────────────────────────────────────────
let $ = {};

// ── App state ─────────────────────────────────────────────────────────────
let visNetwork = null, nodesDS = null, edgesDS = null;
let graphData  = {nodes:[], edges:[]};
let adjList    = {};
let currentStart = null, currentEnd = null;
let pathActive = false, tourActive = false, showAll = false;
let currentMode = "path";

let nodeTooltips    = {};
let edgeTooltipsArr = [];

// ── Pre-loaded data from Python ───────────────────────────────────────────
const PRELOADED = __EMBEDDED_DATA__;
const VIS_OPTS  = __VIS_OPTIONS__;

window.addEventListener("DOMContentLoaded", () => {
  $ = {
    tooltip:         document.getElementById("custom-tooltip"),
    overlay:         document.getElementById("overlay"),
    container:       document.getElementById("network-container"),
    status:          document.getElementById("file-status"),
    fileInput:       document.getElementById("file-input"),
    dropZone:        document.getElementById("drop-zone"),
    startSel:        document.getElementById("start"),
    endSel:          document.getElementById("end"),
    criteriaSel:     document.getElementById("criteria"),
    critBadge:       document.getElementById("criteria-badge"),
    toggleRow:       document.getElementById("show-all-toggle"),
    sameNodeTip:     document.getElementById("same-node-tip"),
    findBtn:         document.getElementById("find-btn"),
    resultEl:        document.getElementById("result"),
    resultSec:       document.getElementById("result-secondary"),
    resetBtn:        document.getElementById("reset-btn"),
    // Tour
    tourSection:     document.getElementById("tour-section"),
    pathSection:     document.getElementById("path-section"),
    tourStartSel:    document.getElementById("tour-start"),
    tourFindBtn:     document.getElementById("tour-find-btn"),
    tourResult:      document.getElementById("tour-result"),
    tourResultSec:   document.getElementById("tour-result-secondary"),
    tourUnreachable: document.getElementById("tour-unreachable"),
    tourResetBtn:    document.getElementById("tour-reset-btn"),
    tourComputing:   document.getElementById("tour-computing"),
    tabPath:         document.getElementById("tab-path"),
    tabTour:         document.getElementById("tab-tour"),
  };

  $.dropZone.addEventListener("dragover",  e => { e.preventDefault(); $.dropZone.classList.add("drag-over"); });
  $.dropZone.addEventListener("dragleave", () => $.dropZone.classList.remove("drag-over"));
  $.dropZone.addEventListener("drop",      e => { e.preventDefault(); $.dropZone.classList.remove("drag-over"); loadFile(e.dataTransfer.files[0]); });
  $.dropZone.addEventListener("click",     () => $.fileInput.click());
  document.getElementById("browse-link")
          .addEventListener("click", e => { e.stopPropagation(); $.fileInput.click(); });
  $.fileInput.addEventListener("change",   e => loadFile(e.target.files[0]));
  $.startSel.addEventListener("change",    e => { highlightNode("start", e.target.value); checkSameNode(); });
  $.endSel.addEventListener("change",      e => { highlightNode("end",   e.target.value); checkSameNode(); });
  $.criteriaSel.addEventListener("change", e => {
    updateEdgeLabels(e.target.value);
    if (pathActive) findPath();
    if (tourActive) findTour();
  });
  $.container.addEventListener("mousemove", positionTooltip);

  if (PRELOADED) initFromData(PRELOADED);
});

// ── Mode switching ────────────────────────────────────────────────────────
function switchMode(mode) {
  if (currentMode === mode) return;
  currentMode = mode;

  document.querySelectorAll(".mode-tab").forEach(t =>
    t.classList.toggle("active", t.dataset.mode === mode));

  $.pathSection.style.display = mode === "path" ? "block" : "none";
  $.tourSection.style.display = mode === "tour" ? "block" : "none";

  // Clear whatever was active in the previous mode
  if (mode === "path") {
    clearTourUI();
    if (nodesDS) resetHighlights();
    highlightNode("start", $.startSel.value);
    highlightNode("end",   $.endSel.value);
  } else {
    clearPathUI();
    if (nodesDS) resetHighlights();
    highlightTourStart($.tourStartSel.value);
  }
  pathActive = false;
  tourActive = false;
}

// ── Tooltip helpers ───────────────────────────────────────────────────────
function positionTooltip(e) {
  const x = e.clientX + 16, y = e.clientY + 16;
  $.tooltip.style.left = Math.min(x, window.innerWidth  - $.tooltip.offsetWidth  - 10) + "px";
  $.tooltip.style.top  = Math.min(y, window.innerHeight - $.tooltip.offsetHeight - 10) + "px";
}
const showTooltip = html => { $.tooltip.innerHTML = html; $.tooltip.style.display = "block"; };
const hideTooltip = ()   => { $.tooltip.style.display = "none"; };

function buildNodeTooltip(name, edges) {
  const rows = edges
    .filter(e => e.from === name)
    .map(e =>
      `<tr>
        <td style='padding:2px 8px;color:#E0E0E0'>${e.to}</td>
        <td style='padding:2px 8px;color:#4FC3F7'>${e.distance} km</td>
        <td style='padding:2px 8px;color:#FFD740'>${e.time} min</td>
        <td style='padding:2px 8px;color:#00E676'>${e.fuel} L</td>
      </tr>`
    ).join("");
  return `<b style='font-size:14px;color:#E0E0E0'>${name}</b>` + (rows
    ? `<table style='margin-top:6px;font-size:11px;border-collapse:collapse'>
        <tr>
          <th style='padding:2px 8px;color:#607080'>To</th>
          <th style='padding:2px 8px;color:#4FC3F7'>km</th>
          <th style='padding:2px 8px;color:#FFD740'>min</th>
          <th style='padding:2px 8px;color:#00E676'>L</th>
        </tr>${rows}</table>` : "");
}
const buildEdgeTooltip = e =>
  `<b style='color:#E0E0E0'>${e.from} &rarr; ${e.to}</b><br>
   <span style='color:#4FC3F7'>📍 ${e.distance} km</span><br>
   <span style='color:#FFD740'>⏱ ${e.time} mins</span><br>
   <span style='color:#00E676'>⛽ ${e.fuel} L</span>`;

// ── Initialise from data object ───────────────────────────────────────────
function initFromData(data) {
  graphData.nodes = data.nodes_list;
  graphData.edges = data.edges_data;

  nodeTooltips    = data.node_tooltips
    || Object.fromEntries(data.nodes_list.map(n => [n, buildNodeTooltip(n, data.edges_data)]));
  edgeTooltipsArr = data.edge_tooltips
    || data.edges_data.map(buildEdgeTooltip);

  adjList = {};
  for (const e of data.edges_data) {
    (adjList[e.from] ??= []).push(e);
  }

  buildNetwork();
  populateSelects(data.nodes_list);
  $.overlay.style.display = "none";
  setStatus(`✓ ${data.nodes_list.length} nodes, ${data.edges_data.length} edges loaded`);
}

// ── Edge label builder ────────────────────────────────────────────────────
const edgeLabelFor = (e, w) => showAll
  ? `📍 ${e.distance}km\n⏱ ${e.time}mins\n⛽ ${e.fuel}L`
  : `${ICON[w]} ${e[w]} ${UNIT[w]}`;

function updateEdgeLabels(weight) {
  if (!edgesDS) return;
  edgesDS.update(graphData.edges.map((e, i) => ({id:i, label:edgeLabelFor(e, weight)})));
  $.critBadge.textContent = BADGE[weight];
}

function toggleShowAll() {
  showAll = !showAll;
  $.toggleRow.classList.toggle("active", showAll);
  updateEdgeLabels($.criteriaSel.value);
  if (pathActive) findPath();
  if (tourActive) findTour();
}

function toggleChart() {
  const content = document.getElementById("chart-content");
  const arrow   = document.getElementById("chart-arrow");
  if (!content) return;
  content.classList.toggle("collapsed");
  arrow.innerHTML = content.classList.contains("collapsed") ? "&#9660;" : "&#9650;";
}

// ── Build vis.js network ──────────────────────────────────────────────────
function buildNetwork() {
  const weight = $.criteriaSel.value || "distance";

  nodesDS = new vis.DataSet(graphData.nodes.map(n => ({
    id:n, label:n,
    color:{background:C.nodeDef, border:C.nodeDef},
    font: {color:C.fontDef, size:28, strokeWidth:4, strokeColor:"#000"},
    size:28
  })));

  edgesDS = new vis.DataSet(graphData.edges.map((e, i) => ({
    id:i, from:e.from, to:e.to,
    label:edgeLabelFor(e, weight),
    arrows:"to",
    color:{color:C.edgeDef},
    font: {color:"#fff", size:16, align:"top", strokeWidth:0},
    smooth:{type:"dynamic"}
  })));

  if (visNetwork) visNetwork.destroy();

  const opts = Object.assign(
    {
      physics:{
        solver:"barnesHut",
        barnesHut:{gravitationalConstant:-20000, centralGravity:.3,
                   springLength:250, springConstant:.05, damping:.09}
      },
      nodes:{shape:"dot"},
      edges:{smooth:{type:"dynamic"}}
    },
    VIS_OPTS || {},
    {interaction:{hover:true, tooltipDelay:9999999}}
  );

  visNetwork = new vis.Network($.container, {nodes:nodesDS, edges:edgesDS}, opts);

  visNetwork.on("hoverNode",  p => { const h = nodeTooltips[p.node];    if (h) showTooltip(h); });
  visNetwork.on("blurNode",   hideTooltip);
  visNetwork.on("hoverEdge",  p => { const h = edgeTooltipsArr[p.edge]; if (h) showTooltip(h); });
  visNetwork.on("blurEdge",   hideTooltip);
  visNetwork.on("dragStart",  hideTooltip);
  visNetwork.on("zoom",       hideTooltip);
}

// ── CSV parsing ───────────────────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) throw new Error("CSV must have a header + at least one data row.");

  const header = lines[0].split(",").map(h => h.trim().toLowerCase());
  const COL    = {
    from:     header.findIndex(h => h.includes("from")),
    to:       header.findIndex(h => h.includes("to")),
    distance: header.findIndex(h => h.includes("distance")),
    time:     header.findIndex(h => h.includes("time")),
    fuel:     header.findIndex(h => h.includes("fuel")),
  };
  const missing = Object.entries(COL).filter(([, i]) => i === -1).map(([k]) => k);
  if (missing.length) throw new Error("Missing columns: " + missing.join(", "));

  const nodesSet = new Set();
  const edges    = [];
  const cell     = (cells, j) => (cells[j] || "").replace(/^"|"$/g, "").trim();

  for (let i = 1; i < lines.length; i++) {
    const raw = lines[i].trim();
    if (!raw) continue;
    const cells = raw.split(",");
    const from  = cell(cells, COL.from);
    const to    = cell(cells, COL.to);
    if (!from || !to) continue;
    nodesSet.add(from); nodesSet.add(to);
    edges.push({
      from, to,
      distance: parseFloat(cell(cells, COL.distance)) || 0,
      time:     parseFloat(cell(cells, COL.time))     || 0,
      fuel:     parseFloat(cell(cells, COL.fuel))     || 0,
    });
  }
  return {nodes_list:[...nodesSet], edges_data:edges};
}

// ── Populate selects ──────────────────────────────────────────────────────
function populateSelects(nodes) {
  const opts = nodes.map(n => `<option value="${n}">${n}</option>`).join("");
  $.startSel.innerHTML     = opts;
  $.endSel.innerHTML       = opts;
  $.tourStartSel.innerHTML = opts;

  [$.startSel, $.endSel, $.criteriaSel, $.tourStartSel].forEach(s => s.disabled = false);
  $.findBtn.disabled     = false;
  $.tourFindBtn.disabled = false;
  $.tabTour.disabled     = false;
  $.toggleRow.classList.remove("disabled");

  if (nodes.length > 1) $.endSel.selectedIndex = 1;

  setTimeout(() => {
    highlightNode("start", $.startSel.value);
    highlightNode("end",   $.endSel.value);
  }, 900);
}

// ── Same-node guard ───────────────────────────────────────────────────────
function checkSameNode() {
  const same = $.startSel.value && $.endSel.value && $.startSel.value === $.endSel.value;
  $.sameNodeTip.style.display = same ? "flex" : "none";
  $.findBtn.disabled = same;
}

// ── File handling ─────────────────────────────────────────────────────────
function loadFile(file) {
  if (!file || !file.name.endsWith(".csv")) {
    setStatus("Please upload a .csv file.", true); return;
  }
  const r = new FileReader();
  r.onload = ev => {
    try {
      const data = parseCSV(ev.target.result);
      initFromData(data);
      setStatus(`✓ ${file.name}  (${data.nodes_list.length} nodes, ${data.edges_data.length} edges)`);
      checkSameNode();
    } catch (err) { setStatus("Error: " + err.message, true); }
  };
  r.readAsText(file);
}

const setStatus = (msg, isError = false) => {
  $.status.textContent = msg;
  $.status.className   = isError ? "error" : "";
};

// ── Highlight helpers (path mode) ─────────────────────────────────────────
function resetHighlights() {
  if (!nodesDS) return;
  const w = $.criteriaSel.value;
  nodesDS.update(graphData.nodes.map(n => ({
    id:n, label:n,
    color:{background:C.nodeDef, border:C.nodeDef},
    font: {color:C.fontDef, size:28, strokeWidth:4, strokeColor:"#000"},
    size:28, opacity:1,
  })));
  edgesDS.update(graphData.edges.map((e, i) => ({
    id:i, label:edgeLabelFor(e, w),
    color:{color:C.edgeDef},
    font: {color:"#fff", size:16, strokeWidth:0},
    width:1,
  })));
}

function highlightNode(role, name) {
  if (role === "start") currentStart = name;
  else                  currentEnd   = name;
  if ((pathActive || tourActive) || !nodesDS) return;
  resetHighlights();
  if (currentStart) nodesDS.update([{id:currentStart, color:{background:C.start, border:"#fff"}, size:36}]);
  if (currentEnd)   nodesDS.update([{id:currentEnd,   color:{background:C.end,   border:"#fff"}, size:36}]);
}

function highlightTourStart(name) {
  if (!nodesDS || tourActive) return;
  resetHighlights();
  if (name) nodesDS.update([{
    id:name,
    color:{background:C.start, border:"#fff"},
    size:38,
    font:{color:"#003300", size:30, strokeWidth:4, strokeColor:"rgba(0,230,118,.5)"},
  }]);
}

// ── Min-heap ──────────────────────────────────────────────────────────────
class MinHeap {
  constructor() { this._h = []; }
  push(item)  { this._h.push(item); this._bubbleUp(this._h.length - 1); }
  pop()       { const top = this._h[0]; const last = this._h.pop();
                if (this._h.length) { this._h[0] = last; this._siftDown(0); } return top; }
  get size()  { return this._h.length; }
  _bubbleUp(i)   { while (i > 0) { const p = (i - 1) >> 1; if (this._h[p][0] <= this._h[i][0]) break; [this._h[p], this._h[i]] = [this._h[i], this._h[p]]; i = p; } }
  _siftDown(i)   { const n = this._h.length; while (true) { let s = i, l = 2*i+1, r = 2*i+2; if (l < n && this._h[l][0] < this._h[s][0]) s = l; if (r < n && this._h[r][0] < this._h[s][0]) s = r; if (s === i) break; [this._h[s], this._h[i]] = [this._h[i], this._h[s]]; i = s; } }
}

// ── Single-pair Dijkstra (path mode) ──────────────────────────────────────
function dijkstra(start, end, weight) {
  const dist = {}, prev = {};
  for (const n of graphData.nodes) { dist[n] = Infinity; prev[n] = null; }
  dist[start] = 0;
  const heap = new MinHeap();
  heap.push([0, start]);
  while (heap.size) {
    const [d, u] = heap.pop();
    if (d > dist[u]) continue;
    if (u === end)   break;
    for (const e of (adjList[u] || [])) {
      const alt = d + e[weight];
      if (alt < dist[e.to]) { dist[e.to] = alt; prev[e.to] = u; heap.push([alt, e.to]); }
    }
  }
  const path = []; let cur = end;
  while (cur !== null) { path.unshift(cur); cur = prev[cur]; }
  return {path, total: isFinite(dist[end]) ? dist[end] : Infinity};
}

function sumAlongPath(path, weights) {
  const totals = Object.fromEntries(weights.map(w => [w, 0]));
  for (let i = 0; i < path.length - 1; i++) {
    const e = (adjList[path[i]] || []).find(e => e.to === path[i + 1]);
    if (e) weights.forEach(w => { totals[w] += e[w]; });
  }
  weights.forEach(w => { totals[w] = Math.round(totals[w] * 100) / 100; });
  return totals;
}

// ── Full Dijkstra (all destinations from one source) ─────────────────────
function dijkstraFull(start, weight) {
  const dist = {}, prev = {};
  for (const n of graphData.nodes) { dist[n] = Infinity; prev[n] = null; }
  dist[start] = 0;
  const heap = new MinHeap();
  heap.push([0, start]);
  while (heap.size) {
    const [d, u] = heap.pop();
    if (d > dist[u]) continue;
    for (const e of (adjList[u] || [])) {
      const alt = d + e[weight];
      if (alt < dist[e.to]) { dist[e.to] = alt; prev[e.to] = u; heap.push([alt, e.to]); }
    }
  }
  return {dist, prev};
}

function reconstructSubPath(prev, start, end) {
  const path = []; let cur = end;
  while (cur !== null && cur !== undefined) {
    path.unshift(cur);
    if (cur === start) break;
    cur = prev[cur];
  }
  return (path.length && path[0] === start) ? path : [];
}

// ── ════════════ TOUR PLANNER (SSSP) ════════════ ─────────────────────────
// Algorithm: single Dijkstra from the chosen start node.
// For each other node, we independently find the cheapest path from start.
// The tour cost = SUM of all those individual cheapest-path costs.
// Displayed edges = union of all edges used across every individual path.
// ──────────────────────────────────────────────────────────────────────────

function findTour() {
  const start  = $.tourStartSel.value;
  const weight = $.criteriaSel.value;
  if (!start || graphData.nodes.length < 2) return;

  $.tourComputing.style.display = "flex";
  $.tourFindBtn.disabled = true;

  // Defer heavy work so the spinner renders first
  setTimeout(() => {
    try {
      _runTour(start, weight);
    } finally {
      $.tourComputing.style.display = "none";
      $.tourFindBtn.disabled = false;
    }
  }, 20);
}

function _runTour(start, weight) {
  // ── Single Dijkstra from start → cheapest path to every node ─────────
  const {dist, prev} = dijkstraFull(start, weight);

  const nodeResults   = [];   // {node, cost, path}  one entry per reachable dest
  const unreachable   = [];
  const usedEdgePairs = new Set();
  const allTotals     = {distance:0, time:0, fuel:0};

  for (const node of graphData.nodes) {
    if (node === start) continue;
    const d = dist[node] ?? Infinity;
    if (!isFinite(d)) { unreachable.push(node); continue; }

    // Reconstruct this node's individual cheapest path from start
    const path = reconstructSubPath(prev, start, node);

    // Accumulate edges and multi-metric sums for this path
    for (let i = 0; i < path.length - 1; i++) {
      const e = (adjList[path[i]] || []).find(e => e.to === path[i+1]);
      if (e) {
        allTotals.distance += e.distance;
        allTotals.time     += e.time;
        allTotals.fuel     += e.fuel;
        usedEdgePairs.add(`${path[i]}|${path[i+1]}`);
      }
    }

    nodeResults.push({node, cost: Math.round(d * 100) / 100, path});
  }

  // Sort destinations cheapest → costliest
  nodeResults.sort((a, b) => a.cost - b.cost);

  ALL_WEIGHTS.forEach(w => { allTotals[w] = Math.round(allTotals[w] * 100) / 100; });
  const totalCost = Math.round(nodeResults.reduce((s, r) => s + r.cost, 0) * 100) / 100;

  tourActive = true;
  pathActive = false;
  visualizeTour(start, nodeResults, usedEdgePairs, totalCost, allTotals, weight, unreachable);
}

function visualizeTour(start, nodeResults, usedEdgePairs, totalCost, allTotals, weight, unreachable) {
  const reachableSet = new Set(nodeResults.map(r => r.node));
  reachableSet.add(start);

  // ── Update nodes: label each reached node with its individual cost ────
  nodesDS.update(graphData.nodes.map(n => {
    const isStart    = n === start;
    const res        = nodeResults.find(r => r.node === n);
    const reachable  = isStart || !!res;
    const costLabel  = res ? `${res.cost} ${UNIT[weight]}` : "";
    const bg = isStart ? C.start : (reachable ? C.tourNode : C.nodeDim);
    return {
      id: n,
      label: reachable ? (isStart ? `${n}\n▶ start` : `${n}\n${costLabel}`) : n,
      color: {background: bg, border: reachable ? "#fff" : "#1e2e3e"},
      size:  isStart ? 44 : (reachable ? 34 : 22),
      font: {
        color:       reachable ? (isStart ? "#001a00" : "#1a001a") : C.fontDim,
        size:        reachable ? (isStart ? 24 : 22) : 22,
        strokeWidth: reachable ? 4 : 2,
        strokeColor: reachable ? "rgba(255,255,255,.5)" : "rgba(0,0,0,.2)",
      },
      opacity: 1,
    };
  }));

  // ── Update edges: highlight only those used in any shortest path ──────
  edgesDS.update(graphData.edges.map((e, i) => {
    const on = usedEdgePairs.has(`${e.from}|${e.to}`);
    return {
      id: i,
      label: edgeLabelFor(e, weight),
      color: {color: on ? C.tourEdge : C.edgeDim},
      font: {
        color:       on ? C.pathLabel       : "rgba(255,255,255,.1)",
        size:        on ? 18                : 14,
        strokeWidth: on ? 3                 : 0,
        strokeColor: on ? C.pathLabelStroke : "transparent",
      },
      width: on ? 4 : 1,
    };
  }));

  // ── Primary result card ───────────────────────────────────────────────
  const unit = UNIT[weight], icon = ICON[weight];

  const destListHtml = nodeResults.map((res, i) => {
    // Show the via-path if it goes through intermediate nodes
    const via = res.path.slice(1, -1);
    const viaHtml = via.length
      ? `<span class="stop-via">via ${via.join(" → ")}</span>`
      : "";
    return `
      <div class="tour-stop">
        <span class="stop-num">${i + 1}</span>
        <span class="stop-node-col">
          <span class="stop-node">${res.node}</span>
          ${viaHtml}
        </span>
        <span class="stop-leg"><span>${icon} ${res.cost} ${unit}</span></span>
      </div>`;
  }).join("");

  const n_dest = nodeResults.length;
  const n_unreachable = unreachable.length;

  $.tourResult.style.display = "block";
  $.tourResult.innerHTML = `
    <div class="tour-result-label">
      Cheapest Path to Each Node
      <span class="heuristic-badge">SSSP</span>
    </div>
    <div class="tour-visit-list">${destListHtml || '<div style="color:#607080;font-size:12px;padding:6px 0">No reachable destinations.</div>'}</div>
    <div class="metric-row">
      <span class="metric-icon">${icon}</span>
      <span class="tour-metric-value">${totalCost}</span>
      <span class="metric-unit">${unit} total</span>
    </div>
    <div class="hop-count">
      ${n_dest} destination${n_dest !== 1 ? "s" : ""} reached
      ${n_unreachable > 0 ? `&nbsp;&middot;&nbsp; ${n_unreachable} unreachable` : ""}
    </div>`;

  // ── Secondary metrics card ────────────────────────────────────────────
  const others = ALL_WEIGHTS.filter(w => w !== weight);
  $.tourResultSec.style.display = "block";
  $.tourResultSec.innerHTML = `
    <div class="sec-label">Also Along These Paths</div>
    <div class="sec-metric-grid">
      ${others.map(w => `
        <div class="sec-metric-item">
          <div class="sm-icon">${ICON[w]}</div>
          <div class="sm-value">${allTotals[w]}</div>
          <div class="sm-unit">${UNIT[w]}</div>
          <div class="sm-name">${LABEL[w]}</div>
        </div>`).join("")}
    </div>`;

  // ── Unreachable warning ───────────────────────────────────────────────
  if (unreachable.length > 0) {
    $.tourUnreachable.style.display = "block";
    $.tourUnreachable.innerHTML = `
      <div class="u-title">&#9888; Unreachable Nodes (${unreachable.length})</div>
      <div class="u-nodes">${unreachable.join(", ")}</div>`;
  } else {
    $.tourUnreachable.style.display = "none";
  }

  $.tourResetBtn.style.display = "block";
}

function clearTourUI() {
  $.tourResult.style.display      = "none";
  $.tourResultSec.style.display   = "none";
  $.tourUnreachable.style.display = "none";
  $.tourResetBtn.style.display    = "none";
  $.tourComputing.style.display   = "none";
}

function resetTour() {
  tourActive = false;
  clearTourUI();
  resetHighlights();
  highlightTourStart($.tourStartSel.value);
}

// ── Find path (path mode) ─────────────────────────────────────────────────
function findPath() {
  const start  = $.startSel.value;
  const end    = $.endSel.value;
  const weight = $.criteriaSel.value;
  if (start === end) { checkSameNode(); return; }

  const {path, total} = dijkstra(start, end, weight);
  const pathSet   = new Set(path);
  const pathPairs = new Set(path.slice(0, -1).map((_, i) => `${path[i]}|${path[i+1]}`));

  pathActive = true;
  tourActive = false;

  nodesDS.update(graphData.nodes.map(n => {
    const on = pathSet.has(n);
    let bg = on ? C.pathNode : C.nodeDim;
    let fc = on ? "#1A1A2E"  : C.fontDim;
    if (n === start) { bg = C.start; fc = "#003300"; }
    if (n === end)   { bg = C.end;   fc = "#3b0000"; }
    return {
      id:n, label:n, opacity:1,
      color:{background:bg, border: on ? "#fff" : "#1e2e3e"},
      size: on ? 38 : 24,
      font:{color:fc, size:on?32:26, strokeWidth:on?4:2,
            strokeColor:on?"rgba(255,255,255,.5)":"rgba(0,0,0,.2)"},
    };
  }));

  edgesDS.update(graphData.edges.map((e, i) => {
    const on = pathPairs.has(`${e.from}|${e.to}`);
    return {
      id:i,
      label: edgeLabelFor(e, weight),
      color: {color: on ? C.pathEdge : C.edgeDim},
      font:  {
        color:       on ? C.pathLabel      : "rgba(255,255,255,.1)",
        size:        on ? 18               : 14,
        strokeWidth: on ? 3                : 0,
        strokeColor: on ? C.pathLabelStroke : "transparent",
      },
      width: on ? 5 : 1,
    };
  }));

  const unit = UNIT[weight], icon = ICON[weight];
  const pathHtml = path.map((n, i) => {
    let cls = "node-chip";
    if (i === 0)              cls += " start";
    if (i === path.length-1)  cls += " end";
    let suffix = "";
    if (i < path.length - 1) {
      const e   = (adjList[n] || []).find(e => e.to === path[i+1]);
      const val = e ? e[weight] : "?";
      suffix = `<span class="arrow">&#8594;</span>
                <span class="edge-badge">${icon} ${val} ${unit}</span>
                <span class="arrow">&#8594;</span>`;
    }
    return `<span class="${cls}">${n}</span>${suffix}`;
  }).join(" ");

  const hops = path.length - 1;
  $.resultEl.style.display = "block";
  $.resultEl.innerHTML = `
    <div class="result-label">Optimal Route Found</div>
    <div class="path-line">${pathHtml}</div>
    <div class="metric-row">
      <span class="metric-icon">${icon}</span>
      <span class="metric-value">${Math.round(total * 100) / 100}</span>
      <span class="metric-unit">${unit}</span>
    </div>
    <div class="hop-count">${LABEL[weight]} &nbsp;&middot;&nbsp; ${hops} hop${hops !== 1 ? "s" : ""}</div>`;

  const others  = ALL_WEIGHTS.filter(w => w !== weight);
  const oTotals = sumAlongPath(path, others);
  $.resultSec.style.display = "block";
  $.resultSec.innerHTML = `
    <div class="sec-label">Also Along This Route</div>
    <div class="sec-metric-grid">
      ${others.map(w => `
        <div class="sec-metric-item">
          <div class="sm-icon">${ICON[w]}</div>
          <div class="sm-value">${oTotals[w]}</div>
          <div class="sm-unit">${UNIT[w]}</div>
          <div class="sm-name">${LABEL[w]}</div>
        </div>`).join("")}
    </div>`;

  $.resetBtn.style.display = "block";
}

function clearPathUI() {
  $.resultEl.style.display  = "none";
  $.resultSec.style.display = "none";
  $.resetBtn.style.display  = "none";
}

function resetAll() {
  pathActive = false;
  tourActive = false;
  clearPathUI();
  clearTourUI();
  resetHighlights();
  if (currentMode === "path") {
    highlightNode("start", $.startSel.value);
    highlightNode("end",   $.endSel.value);
  } else {
    highlightTourStart($.tourStartSel.value);
  }
}
</script>
</body>
</html>"""


# ════════════════════════════════════════════════════════════════════════════
# 7. CLI helpers + main
# ════════════════════════════════════════════════════════════════════════════
def interactive_pick(prompt: str, options: list) -> str:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i:>3}. {opt}")
    while True:
        raw = input("  Enter number or name: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        print("  ⚠  Invalid choice — try again.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Network Path Finder  (pandas + pyvis + matplotlib)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python generate_network.py\n"
            "  python generate_network.py network.csv\n"
            "  python generate_network.py network.csv --start A --end B\n"
            "  python generate_network.py network.csv --criteria fuel --out-dir ./out\n"
            "  python generate_network.py network.csv --mode tour --start A\n"
            "  python generate_network.py network.csv --mode tour --start A --criteria fuel"
        )
    )
    parser.add_argument("csv",        nargs="?",  help="Path to network CSV file")
    parser.add_argument("--start",                help="Start node name")
    parser.add_argument("--end",                  help="End node name (path mode only)")
    parser.add_argument("--criteria",
                        choices=["distance","time","fuel"], default="distance",
                        help="Optimisation criterion (default: distance)")
    parser.add_argument("--mode",
                        choices=["path","tour"], default="path",
                        help="'path' = shortest path between two nodes; "
                             "'tour' = cheapest tour visiting all nodes (default: path)")
    parser.add_argument("--out-dir",  default=".", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    html_path = os.path.join(args.out_dir, "node_map.html")

    # ── No CSV → drag-and-drop HTML ───────────────────────────────────────
    if not args.csv:
        print("No CSV provided — generating drag-and-drop HTML …")
        html = generate_html()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved: {html_path}")
        print("Open in a browser and upload a CSV to get started.")
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        return

    if not os.path.isfile(args.csv):
        sys.exit(f"Error: file not found — {args.csv}")

    # 1. pandas: load & validate
    print(f"\nLoading '{args.csv}' with pandas …")
    df = load_graph(args.csv)
    all_nodes = sorted(pd.concat([df["from"], df["to"]]).unique().tolist())
    print(f"  {len(all_nodes)} nodes, {len(df)} edges")
    print(f"  Columns: {list(df.columns)}")

    # 2. pyvis: prepare vis.js graph data + options
    print("\nPreparing vis.js data with pyvis …")
    graph_data = prepare_graph_data(df)

    weight = args.criteria

    # ════════════════════════════════════════════════════════════════════
    # MODE: TOUR  (Single-Source Shortest Paths — sum cheapest paths to all nodes)
    # ════════════════════════════════════════════════════════════════════
    if args.mode == "tour":
        start = args.start or interactive_pick("Select START node for tour:", all_nodes)
        if start not in all_nodes:
            sys.exit(f"Error: '{start}' not found in graph.")

        print(f"\nRunning SSSP from '{start}' (criterion: {weight}) …")
        node_results, total_cost, unreachable = sssp_tour(df, start, weight)

        print(f"\n  Start node : {start}")
        print(f"  Destinations reached: {len(node_results)}")
        if unreachable:
            print(f"  Unreachable: {', '.join(unreachable)}")
        print(f"\n  {'Node':<20}  {'Cost':>10}  {'Path'}")
        print(f"  {'-'*20}  {'-'*10}  {'-'*30}")
        for res in node_results:
            path_str = " → ".join(res["path"])
            print(f"  {res['node']:<20}  {res['cost']:>10} {UNIT[weight]}  {path_str}")
        print(f"\n  Total (sum of all cheapest paths): {total_cost} {UNIT[weight]}")

        # matplotlib tour chart
        print("\nGenerating matplotlib tour stats chart …")
        chart_b64 = make_tour_chart_b64(df, start, node_results, weight, unreachable)
        png_path  = os.path.join(args.out_dir, "tour_stats.png")
        with open(png_path, "wb") as f:
            f.write(base64.b64decode(chart_b64))
        print(f"  Chart saved → {png_path}")

    # ════════════════════════════════════════════════════════════════════
    # MODE: PATH
    # ════════════════════════════════════════════════════════════════════
    else:
        start = args.start or interactive_pick("Select START node:", all_nodes)
        end   = args.end   or interactive_pick("Select END node:",   all_nodes)

        if start not in all_nodes: sys.exit(f"Error: '{start}' not found in graph.")
        if end   not in all_nodes: sys.exit(f"Error: '{end}' not found in graph.")
        if start == end:            sys.exit("Error: Start and End must be different.")

        print(f"\nRunning Dijkstra  {start} → {end}  (optimise: {weight}) …")
        path, total = dijkstra(df, start, end, weight)
        if not path:
            sys.exit(f"No path found from '{start}' to '{end}'.")
        hops  = len(path) - 1
        extra = sum_path(df, path)
        print(f"\n  Path   : {' → '.join(path)}")
        print(f"  Total  : {total} {UNIT[weight]}  ({hops} hop{'s' if hops != 1 else ''})")
        for m in METRICS:
            if m != weight:
                print(f"           {extra[m]} {UNIT[m]}  ({m})")

        # matplotlib path chart
        print("\nGenerating matplotlib path stats chart …")
        chart_b64 = make_chart_b64(df, path, weight)
        png_path  = os.path.join(args.out_dir, "path_stats.png")
        with open(png_path, "wb") as f:
            f.write(base64.b64decode(chart_b64))
        print(f"  Chart saved → {png_path}")

    # Build and save HTML (same for both modes — interactive in browser)
    html = generate_html(graph_data, chart_b64)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Map saved   → {html_path}")

    print("\nDone! Opening in browser …")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")


if __name__ == "__main__":
    main()