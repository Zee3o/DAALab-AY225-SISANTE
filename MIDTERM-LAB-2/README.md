# 🌐 Network Path Finder
**CSV-Based Graph Visualizer with Shortest Path Algorithm**

An interactive tool that converts a CSV file of network connections into a dynamic graph and calculates the optimal path between nodes.

The program generates a standalone HTML visualization where users can upload a CSV, visualize the network, and compute the shortest route based on distance, time, or fuel.

---

## ✨ Features

- ✔ Interactive network graph visualization
- ✔ Drag & drop CSV upload
- ✔ Shortest path calculation (Dijkstra's Algorithm)
- ✔ Optimize routes by:
  - 📍 Distance (km)
  - ⏱ Time (minutes)
  - ⛽ Fuel (liters)
- ✔ Displays route metrics and node hops
- ✔ Secondary metric display (see all costs along the chosen path)
- ✔ Option to show all edge values simultaneously
- ✔ Embedded matplotlib statistics chart (when launched via CLI with a CSV)
- ✔ Modern dark UI with highlighted paths and interactive tooltips

---

## 🖥 System Requirements

| Requirement | Version          |
|-------------|------------------|
| Python      | 3.7 or newer     |
| Browser     | Chrome / Edge / Firefox / Opera |
| Internet    | Required for visualization library |

Check your Python version:

```bash
python --version
```

---

## 📦 Required Python Libraries

| Library    | Purpose                        |
|------------|--------------------------------|
| pyvis      | Network graph visualization    |
| matplotlib | Statistics chart generation    |
| pandas     | CSV data processing            |

---

## ⚙ Installation

Install all dependencies with one command:

```bash
pip install pyvis matplotlib pandas
```

If using Python 3 explicitly:

```bash
pip3 install pyvis matplotlib pandas
```

---

## 🧑‍💻 Recommended Development Environment

**Editor:** Visual Studio Code — [Download](https://code.visualstudio.com/)

| Extension           | Purpose                    |
|---------------------|----------------------------|
| Python (Microsoft)  | Python development support |
| Live Server         | Easily preview HTML files  |

Install both from the VS Code marketplace.

---

## 🚀 Running the Program

### 1️⃣ Save the Script

Save the file as:

```
generate_network.py
```

### 2️⃣ Run the Script

Open a terminal in the project folder and choose a mode:

**Drag & drop mode** (no CSV required — upload via browser):

```bash
python generate_network.py
```

**Interactive mode** (loads a CSV, prompts you to pick nodes):

```bash
python generate_network.py network.csv
```

**Full CLI mode** (specify all options upfront):

```bash
python generate_network.py network.csv --start A --end B --criteria fuel --out-dir ./out
```

**CLI Arguments:**

| Argument      | Description                                          | Default    |
|---------------|------------------------------------------------------|------------|
| `csv`         | Path to the network CSV file (optional)              | —          |
| `--start`     | Start node name                                      | (prompted) |
| `--end`       | End node name                                        | (prompted) |
| `--criteria`  | Optimization metric: `distance`, `time`, or `fuel`   | `distance` |
| `--out-dir`   | Output directory for generated files                 | `.`        |

Output example:

```
Generated: /project/node_map.html
```

### 3️⃣ Open the Visualization

Open the generated file:

```
node_map.html
```

You can double-click it, open it directly in your browser, or use Live Server in VS Code.

**Supported browsers:** Google Chrome · Microsoft Edge · Firefox · Opera

---

## 📊 Using the Application

1. **Upload a CSV file** — drag & drop onto the panel or click **Browse Files**
2. **Select** a Start Node and End Node from the dropdowns
3. **Choose** an optimization criteria (Distance, Time, or Fuel)
4. Click **Find Shortest Path**

The network will:
- Highlight the optimal route
- Display the primary metric total (e.g. shortest distance)
- Show the other two metrics along the same path
- Dim all non-path nodes and edges for clarity

To reset highlights, click **✕ Clear Highlights**.

---

## 📄 CSV File Format

Your CSV must include a header row with the following columns. Column order does not matter, but names must contain the keywords listed below.

| Column          | Keyword Match | Description                    |
|-----------------|---------------|--------------------------------|
| From Node       | `from`        | Starting node of the edge      |
| To Node         | `to`          | Destination node of the edge   |
| Distance (km)   | `distance`    | Distance between nodes         |
| Time (mins)     | `time`        | Travel time                    |
| Fuel (Liters)   | `fuel`        | Fuel consumption               |

### Example CSV

```csv
From Node,To Node,Distance (km),Time (mins),Fuel (Liters)
A,B,5,10,0.5
B,C,4,8,0.4
A,C,10,15,0.9
C,D,7,12,0.7
```

---

## 🧠 Algorithms Used

| Algorithm                              | Purpose                                        |
|----------------------------------------|------------------------------------------------|
| 🌐 Force-Directed Layout (Barnes–Hut)  | Automatically positions nodes in the network   |
| 📍 Dijkstra's Algorithm (Min-Heap)     | Finds the shortest path between two nodes      |

### 🌐 Network Layout

The visualization uses the Barnes–Hut force-directed layout from the vis-network library. In this simulation:

- 🔋 Nodes repel each other
- 🪢 Edges act like springs pulling connected nodes together
- 🌍 Gravity keeps the graph centered

This physics-based layout automatically spreads nodes so the network remains clear and readable.

### 📍 Shortest Path Algorithm

Dijkstra's Algorithm is used to find the optimal route on a weighted directed graph. The implementation uses a **binary min-heap** for O((V + E) log V) performance.

Each edge carries three possible weights:

- 📏 Distance (km)
- ⏱ Time (mins)
- ⛽ Fuel (liters)

The user selects which metric to optimize, and the algorithm finds the minimum-cost path between the selected start and end nodes. The chosen path is highlighted in the visualization while all other nodes and edges are dimmed.

---

## 📊 Statistics Chart

When the program is run with a CSV via the CLI, a **matplotlib statistics chart** is embedded in the HTML and also saved separately as `path_stats.png`. The chart includes:

- **Stacked bar chart** — per-hop breakdown of all three metrics
- **Route totals card** — summary of distance, time, and fuel for the full path
- **Distribution histograms** — all-edge distribution for each metric, with the path's edges marked

---

## 📂 Project Structure

```
network-path-finder/
│
├── generate_network.py     # Main script
├── node_map.html           # Generated after running the script
├── path_stats.png          # Generated when a CSV is provided via CLI
└── README.md
```

---

## 📤 Output

Running the script produces:

- **`node_map.html`** — self-contained file with the network visualization, interactive controls, shortest path algorithm, and (optionally) the embedded statistics chart
- **`path_stats.png`** — standalone chart image (only when a CSV is provided via CLI)

No backend server is required. All logic runs in the browser.

---

## Brief Report: Network Path Finder

This project reads a CSV file containing network connections and converts it into a visual network graph.

Each row represents a connection between two nodes.

The program:

Loads the dataset

Builds a graph structure

Calculates the shortest path

Generates an interactive HTML visualization

Three libraries are used:

Library	Purpose
pandas	Data loading and preprocessing
pyvis	Graph visualization
matplotlib	Statistics chart generation

After selecting a start node, end node, and optimization criteria, the program computes the optimal route and highlights it in the network map.

Finally, a single HTML file is generated containing the visualization and chart.

## Challenges Faced

Handling Different CSV Formats

CSV files may have columns in different orders.

This was solved by detecting columns using keywords such as:

```
from
to
distance
time
fuel
Graph Readability
```

Node labels sometimes overlapped.

This was improved by adjusting:

physics settings

node spacing

PyVis layout parameters

Tooltip Rendering

The default vis.js tooltips escaped HTML, causing formatting issues.

This was solved by implementing a custom tooltip system using an HTML floating div.

Self-Contained HTML Output

To keep the HTML fully portable, the Matplotlib chart is converted to a Base64 image and embedded directly into the page.

## Summary

The Network Path Finder loads network data, visualizes it as an interactive graph, and calculates optimal routes using Dijkstra’s Algorithm.