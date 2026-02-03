import csv
import time
import sys

# =========================
# DATA LOADING
# =========================

def load_csv(filepath, limit=None):
    start = time.perf_counter()
    data = []

    with open(filepath, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            row["ID"] = int(row["ID"])  # ensure integer comparison
            data.append(row)

    end = time.perf_counter()
    return data, end - start


# =========================
# SORTING ALGORITHMS
# =========================

def bubble_sort(data, key):
    arr = data[:]
    n = len(arr)

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j][key] > arr[j + 1][key]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def insertion_sort(data, key):
    arr = data[:]

    for i in range(1, len(arr)):
        current = arr[i]
        j = i - 1

        while j >= 0 and arr[j][key] > current[key]:
            arr[j + 1] = arr[j]
            j -= 1

        arr[j + 1] = current
    return arr


def merge_sort(data, key):
    if len(data) <= 1:
        return data

    mid = len(data) // 2
    left = merge_sort(data[:mid], key)
    right = merge_sort(data[mid:], key)

    return merge(left, right, key)


def merge(left, right, key):
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i][key] <= right[j][key]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


# =========================
# BENCHMARK CONTROLLER
# =========================

def benchmark():
    print("\n=== Sorting Algorithm Benchmark Tool ===\n")

    filepath = "../data/generated_data.csv"

    print("Choose column to sort by:")
    print("1 - ID")
    print("2 - FirstName")
    print("3 - LastName")

    col_choice = input("Enter choice: ").strip()
    key_map = {"1": "ID", "2": "FirstName", "3": "LastName"}

    if col_choice not in key_map:
        print("Invalid column choice.")
        sys.exit(1)

    sort_key = key_map[col_choice]

    print("\nChoose sorting algorithm:")
    print("1 - Bubble Sort (O(n²))")
    print("2 - Insertion Sort (O(n²))")
    print("3 - Merge Sort (O(n log n))")

    algo_choice = input("Enter choice: ").strip()

    algo_map = {
        "1": bubble_sort,
        "2": insertion_sort,
        "3": merge_sort
    }

    if algo_choice not in algo_map:
        print("Invalid algorithm choice.")
        sys.exit(1)

    algorithm = algo_map[algo_choice]

    N = int(input("\nEnter number of rows to sort (e.g., 1000, 10000, 100000): "))

    if algo_choice in {"1", "2"} and N > 10000:
        print("\nWARNING:")
        print("You selected an O(n²) algorithm with a large dataset.")
        confirm = input("This may take a long time. Continue? (y/n): ").lower()
        if confirm != "y":
            sys.exit(0)

    print("\nLoading data...")
    data, load_time = load_csv(filepath, N)

    print("Sorting data...")
    sort_start = time.perf_counter()
    sorted_data = algorithm(data, sort_key)
    sort_end = time.perf_counter()

    sort_time = sort_end - sort_start
    total_time = load_time + sort_time

    print("\n--- RESULTS ---")
    print(f"Rows sorted: {N}")
    print(f"Sort key: {sort_key}")
    print(f"Load time: {load_time:.4f} seconds")
    print(f"Sort time: {sort_time:.4f} seconds")
    print(f"Total execution time: {total_time:.4f} seconds")

    print("\nFirst 10 sorted records:")
    for row in sorted_data[:10]:
        print(row)


if __name__ == "__main__":
    benchmark()