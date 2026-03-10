import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv
import heapq

# -------------------------------------------------------
# LOAD DATABASE
# -------------------------------------------------------
def load_database(path):

    graph = {}
    locations = set()

    with open(path, 'r') as file:
        reader = csv.DictReader(file)

        for row in reader:

            a = row["Location A"]
            b = row["Location B"]

            distance = float(row["Distance"])
            time = float(row["Time"])
            fuel = float(row["Fuel"])

            locations.add(a)
            locations.add(b)

            if a not in graph:
                graph[a] = {}

            graph[a][b] = {
                "Distance": distance,
                "Time": time,
                "Fuel": fuel
            }

    return graph, sorted(list(locations))


# -------------------------------------------------------
# DIJKSTRA SHORTEST PATH
# -------------------------------------------------------
def dijkstra(graph, start, metric):

    pq = []
    heapq.heappush(pq, (0, start, [start]))

    visited = {}
    results = {}

    while pq:

        cost, node, path = heapq.heappop(pq)

        if node in visited:
            continue

        visited[node] = cost
        results[node] = (cost, path)

        if node not in graph:
            continue

        for neighbor in graph[node]:

            edge_cost = graph[node][neighbor][metric]

            heapq.heappush(
                pq,
                (cost + edge_cost, neighbor, path + [neighbor])
            )

    return results


# -------------------------------------------------------
# FIND BEST WAREHOUSE
# -------------------------------------------------------
def find_best_warehouse(graph, locations, metric):

    best_node = None
    best_total = float("inf")
    best_routes = None

    for node in locations:

        routes = dijkstra(graph, node, metric)

        total = 0

        for loc in routes:
            if loc != node:
                total += routes[loc][0]

        if total < best_total:

            best_total = total
            best_node = node
            best_routes = routes

    return best_node, best_total, best_routes


# -------------------------------------------------------
# GUI APPLICATION
# -------------------------------------------------------
class App:

    def __init__(self, root):

        self.root = root
        self.root.title("Route Optimizer")

        self.root.geometry("750x500")
        self.root.configure(bg="#1e1e2f")

        self.graph = None
        self.locations = None

        title = tk.Label(
            root,
            text="Route Optimizer",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg="#1e1e2f"
        )
        title.pack(pady=15)

        # CONTROL FRAME
        control = tk.Frame(root, bg="#1e1e2f")
        control.pack()

        tk.Button(
            control,
            text="Load Database.csv",
            command=self.load_csv,
            bg="#4CAF50",
            fg="white",
            width=18
        ).grid(row=0, column=0, padx=10)

        tk.Label(
            control,
            text="Optimize For:",
            fg="white",
            bg="#1e1e2f"
        ).grid(row=0, column=1)

        self.metric = tk.StringVar()
        self.metric.set("Distance")

        metric_menu = ttk.Combobox(
            control,
            textvariable=self.metric,
            values=["Distance", "Time", "Fuel"],
            width=10,
            state="readonly"
        )
        metric_menu.grid(row=0, column=2, padx=10)

        tk.Button(
            control,
            text="Analyze Route",
            command=self.solve,
            bg="#2196F3",
            fg="white",
            width=18
        ).grid(row=0, column=3, padx=10)

        # RESULT SECTION
        result_frame = tk.Frame(root, bg="#2b2b3c")
        result_frame.pack(pady=20, fill="both", expand=True)

        self.result_label = tk.Label(
            result_frame,
            text="Load a database to begin.",
            font=("Segoe UI", 12),
            fg="white",
            bg="#2b2b3c"
        )

        self.result_label.pack(pady=10)

        # ROUTE TABLE
        columns = ("Destination", "Best Route", "Cost")

        self.table = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            height=12
        )

        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, anchor="center")

        self.table.pack(fill="both", expand=True)


    # ---------------------------------------------------
    # LOAD CSV
    # ---------------------------------------------------
    def load_csv(self):

        path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv")]
        )

        if not path:
            return

        try:
            self.graph, self.locations = load_database(path)

            messagebox.showinfo(
                "Database Loaded",
                "Data successfully processed."
            )

        except Exception as e:

            messagebox.showerror("Error", str(e))


    # ---------------------------------------------------
    # SOLVE
    # ---------------------------------------------------
    def solve(self):

        if not self.graph:
            messagebox.showerror("Error", "Please load the database first.")
            return

        metric = self.metric.get()

        warehouse, total, routes = find_best_warehouse(
            self.graph,
            self.locations,
            metric
        )

        self.result_label.config(
            text=f"Best Starting Location: {warehouse}    |    Total {metric}: {round(total,2)}"
        )

        for row in self.table.get_children():
            self.table.delete(row)

        for loc in routes:

            if loc == warehouse:
                continue

            cost, path = routes[loc]

            route = " → ".join(path)

            self.table.insert(
                "",
                "end",
                values=(loc, route, round(cost,2))
            )


# -------------------------------------------------------
# MAIN PROGRAM
# -------------------------------------------------------
root = tk.Tk()
app = App(root)
root.mainloop()