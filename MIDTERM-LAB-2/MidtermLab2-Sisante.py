import csv
import heapq
import math
import os
import tkinter as tk
from tkinter import ttk, messagebox

# ─────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────

def load_graph(filepath):
    graph = {}   # adjacency list: node -> list of (neighbor, attrs)
    nodes = set()

    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            frm  = row['From Node'].strip()
            to   = row['To Node'].strip()
            dist = float(row['Distance (km)'])
            time = float(row['Time (mins)'])
            fuel = float(row['Fuel (Liters)'])

            nodes.add(frm)
            nodes.add(to)

            graph.setdefault(frm, []).append((to,   {'distance': dist, 'time': time, 'fuel': fuel}))
            graph.setdefault(to,  []).append((frm,  {'distance': dist, 'time': time, 'fuel': fuel}))

    return graph, sorted(nodes)


# ─────────────────────────────────────────
#  DIJKSTRA
# ─────────────────────────────────────────

def dijkstra(graph, start, end, weight_key):
    """
    Computes the shortest path using Dijkstra's Algorithm.

    Parameters:
        graph (dict): Adjacency list representation of the graph
        start (str): Starting node
        end (str): Destination node
        weight_key (str): Which metric to optimize ('distance', 'time', 'fuel')

    Returns:
        (cost, path, totals):
            cost   -> optimized cost (based on weight_key)
            path   -> list of nodes representing the shortest path
            totals -> dictionary with accumulated distance, time, and fuel
    """

    # Priority queue stores:
    # (optimized_cost, current_node, path_so_far, totals_dict)
    pq = [(0, start, [start], {'distance': 0, 'time': 0, 'fuel': 0})]

    # Stores the best known cost to each node (prevents reprocessing)
    visited = {}

    while pq:
        cost, node, path, totals = heapq.heappop(pq)

        # If we've already found a better path to this node, skip it
        if node in visited:
            continue

        visited[node] = cost

        # Destination reached → return immediately (greedy guarantee)
        if node == end:
            return cost, path, totals

        # Explore neighbors (Dijkstra relaxation step)
        for neighbor, attrs in graph.get(node, []):
            if neighbor not in visited:
                new_cost = cost + attrs[weight_key]

                # Update totals incrementally instead of recomputing later
                new_totals = {
                    'distance': totals['distance'] + attrs['distance'],
                    'time': totals['time'] + attrs['time'],
                    'fuel': totals['fuel'] + attrs['fuel']
                }

                heapq.heappush(
                    pq,
                    (new_cost, neighbor, path + [neighbor], new_totals)
                )

    # No path exists
    return None, [], {}


# ─────────────────────────────────────────
#  NODE MAP (Canvas-based)
# ─────────────────────────────────────────

NODE_POSITIONS = {
    'NOVELETA': (0.25, 0.35),
    'IMUS':     (0.42, 0.12),
    'BACOOR':   (0.75, 0.20),
    'KAWIT':    (0.25, 0.55),
    'DASMA':    (0.85, 0.55),
    'INDANG':   (0.18, 0.85),
    'SILANG':   (0.52, 0.85),
    'GENTRI':   (0.85, 0.85),
}

BG_COLOR        = '#111827'
PANEL_COLOR     = '#1f2937'
ACCENT          = '#22d3ee'
EDGE_COLOR      = '#6b7280'
NODE_FILL       = '#374151'
NODE_OUTLINE    = '#22d3ee'
NODE_TEXT       = '#e5e7eb'

HIGHLIGHT_EDGE  = '#22d3ee'
HIGHLIGHT_NODE  = '#06b6d4'

CANVAS_W        = 720
CANVAS_H        = 320
RADIUS          = 22


def draw_map(canvas, graph, nodes, highlight_path=None, animate=False):
    """
    Renders the node map with:
    - curved edges
    - glowing nodes
    - optional animated path highlight
    """

    canvas.delete('all')
    W, H = CANVAS_W, CANVAS_H

    # ── Background: dotted map style ──
    for x in range(0, W, 30):
        for y in range(0, H, 30):
            canvas.create_oval(x, y, x+1, y+1, fill='#1f2937', outline='')

    def pos(name):
        px, py = NODE_POSITIONS.get(name, (0.5, 0.5))
        return int(px * W), int(py * H)

    # Precompute positions (performance + cleaner code)
    positions = {name: pos(name) for name in nodes}

    drawn_edges = set()

    # Convert highlight path → edge set
    hl_edges = set()
    if highlight_path:
        for i in range(len(highlight_path) - 1):
            a, b = highlight_path[i], highlight_path[i + 1]
            hl_edges.add((min(a, b), max(a, b)))

    # ── Draw edges (curved) ──
    for node in graph:
        for neighbor, attrs in graph[node]:
            key = (min(node, neighbor), max(node, neighbor))
            if key in drawn_edges:
                continue
            drawn_edges.add(key)

            x1, y1 = positions[node]
            x2, y2 = positions[neighbor]

            is_hl = key in hl_edges and not animate

            color = HIGHLIGHT_EDGE if is_hl else EDGE_COLOR
            width = 4 if is_hl else 1.5

            # Create curved line using midpoint control
            cx, cy = (x1 + x2)//2, (y1 + y2)//2 - 20

            canvas.create_line(
                x1, y1, cx, cy, x2, y2,
                smooth=True,
                splinesteps=36,
                fill=color,
                width=width
            )

            # Distance label
            mx, my = (x1 + x2)//2, (y1 + y2)//2
            canvas.create_text(mx, my - 8,
                               text=f"{attrs['distance']} km",
                               fill='#9ca3af',
                               font=('Courier', 7))

    # ── Draw nodes with glow ──
    for name in nodes:
        x, y = positions[name]
        is_hl = highlight_path and name in highlight_path

        # Glow effect
        canvas.create_oval(
            x - RADIUS - 4, y - RADIUS - 4,
            x + RADIUS + 4, y + RADIUS + 4,
            fill='',
            outline=ACCENT if is_hl else '#1f2937',
            width=2
        )

        # Main node
        canvas.create_oval(
            x - RADIUS, y - RADIUS,
            x + RADIUS, y + RADIUS,
            fill=HIGHLIGHT_NODE if is_hl else NODE_FILL,
            outline=NODE_OUTLINE,
            width=2
        )

        canvas.create_text(x, y,
                           text=name[:3],
                           fill=NODE_TEXT,
                           font=('Courier', 9, 'bold'))

        canvas.create_text(x, y + RADIUS + 10,
                           text=name,
                           fill='#9ca3af',
                           font=('Courier', 7))

    # ── Animate path if requested ──
    if animate and highlight_path:
        animate_path(canvas, highlight_path, positions)

# ─────────────────────────────────────────
#  PATH ANIMATION
# ─────────────────────────────────────────

def animate_path(canvas, path, positions, i=0):
    """Draws the path progressively to simulate movement."""
    if i >= len(path) - 1:
        return

    a, b = path[i], path[i+1]
    x1, y1 = positions[a]
    x2, y2 = positions[b]

    cx, cy = (x1 + x2)//2, (y1 + y2)//2 - 20

    canvas.create_line(
        x1, y1, cx, cy, x2, y2,
        smooth=True,
        splinesteps=36,
        fill=HIGHLIGHT_EDGE,
        width=4
    )

    canvas.after(180, lambda: animate_path(canvas, path, positions, i+1))

# ─────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────

def build_gui(graph, nodes):
    root = tk.Tk()
    root.title("Network Path Finder")
    root.configure(bg=BG_COLOR)
    root.resizable(False, False)

    # ── Header ──
    header = tk.Frame(root, bg=PANEL_COLOR, pady=10)
    header.pack(fill='x')

    tk.Label(header,
             text="NETWORK PATH FINDER",
             font=('Courier', 15, 'bold'),
             fg=ACCENT, bg=PANEL_COLOR).pack()

    tk.Label(header,
             text="Interactive Path Optimization Map",
             font=('Courier', 9),
             fg='#9ca3af', bg=PANEL_COLOR).pack()

    # ── Canvas ──
    canvas = tk.Canvas(root,
                       width=CANVAS_W,
                       height=CANVAS_H,
                       bg=BG_COLOR,
                       highlightthickness=0)
    canvas.pack(padx=10, pady=8)

    draw_map(canvas, graph, nodes)

    # ── Controls ──
    ctrl = tk.Frame(root, bg=BG_COLOR)
    ctrl.pack(pady=6)

    def label(text):
        return tk.Label(ctrl, text=text,
                        bg=BG_COLOR, fg='#9ca3af',
                        font=('Courier', 9))

    # Row 1
    label("START").grid(row=0, column=0, padx=5)
    frm_var = tk.StringVar(value=nodes[0])
    ttk.Combobox(ctrl, textvariable=frm_var,
                 values=nodes, width=12,
                 state='readonly').grid(row=1, column=0, padx=5)

    label("DESTINATION").grid(row=0, column=1, padx=5)
    to_var = tk.StringVar(value=nodes[-1])
    ttk.Combobox(ctrl, textvariable=to_var,
                 values=nodes, width=12,
                 state='readonly').grid(row=1, column=1, padx=5)

    label("OPTIMIZE").grid(row=0, column=2, padx=5)
    opt_var = tk.StringVar(value='distance')
    ttk.Combobox(ctrl, textvariable=opt_var,
                 values=['distance', 'time', 'fuel'],
                 width=10, state='readonly').grid(row=1, column=2, padx=5)

    # ── Result Card ──
    result_frame = tk.Frame(root, bg=PANEL_COLOR, pady=10)
    result_frame.pack(fill='x', padx=12, pady=6)

    result_var = tk.StringVar(value="Select route parameters and calculate the best path.")

    tk.Label(result_frame,
             textvariable=result_var,
             bg=PANEL_COLOR,
             fg='#e5e7eb',
             font=('Courier', 9),
             justify='left',
             wraplength=680).pack(padx=10)

    # ── Actions ──
    def find_path():
        start = frm_var.get()
        end = to_var.get()
        key = opt_var.get()

        if start == end:
            messagebox.showwarning("Invalid Selection", "Start and destination must be different.")
            return

        cost, path, totals = dijkstra(graph, start, end, key)

        if not path:
            result_var.set(f"No route found from {start} to {end}.")
            draw_map(canvas, graph, nodes)
            return

        path_str = " → ".join(path)

        result_var.set(
            f"ROUTE FOUND\n\n"
            f"{path_str}\n\n"
            f"Distance : {totals['distance']:.1f} km\n"
            f"Time     : {totals['time']:.0f} mins\n"
            f"Fuel     : {totals['fuel']:.2f} L"
        )

        draw_map(canvas, graph, nodes, highlight_path=path, animate=True)

    def reset():
        result_var.set("Select route parameters and calculate the best path.")
        draw_map(canvas, graph, nodes)

    btn_frame = tk.Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=5)

    tk.Button(btn_frame, text="Find Route",
              command=find_path,
              bg=ACCENT, fg='black',
              font=('Courier', 10, 'bold'),
              padx=12, pady=5).grid(row=0, column=0, padx=6)

    tk.Button(btn_frame, text="Reset",
              command=reset,
              bg='#374151', fg='white',
              font=('Courier', 10),
              padx=10, pady=5).grid(row=0, column=1, padx=6)

    # ── Legend ──
    tk.Label(root,
             text="● Node   ─ Route   🔷 Highlighted Path",
             fg='#6b7280',
             bg=BG_COLOR,
             font=('Courier', 8)).pack(pady=4)

    root.mainloop()


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────

if __name__ == '__main__':
    CSV_FILE = os.path.join(os.path.dirname(__file__), 'Database.csv')
    try:
        graph, nodes = load_graph(CSV_FILE)
    except FileNotFoundError:
        print(f"ERROR: '{CSV_FILE}' not found. Place it in the same folder as this script.")
        raise

    print("Nodes loaded:", nodes)
    print(f"Edges: {sum(len(v) for v in graph.values()) // 2}")
    build_gui(graph, nodes)