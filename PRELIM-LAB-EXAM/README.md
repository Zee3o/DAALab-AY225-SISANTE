# Sorting Algorithm Benchmark

## Environment
- Language: Python 3.x
- Dataset Size: 100,000 records
- Columns: ID, FirstName, LastName

## Benchmark Results 

| Algorithm       | 1,000 Rows | 10,000 Rows | 100,000 Rows |
|-----------------|------------|-------------|--------------|
| Bubble Sort     | 0.15s      | 15.2s       |   Too Slow   | 
| Insertion Sort  | 0.09s      | 12.8s       |   Too Slow   |
| Merge Sort      | 0.02s      | 0.11s       |    0.95s     |

## Observations
- O(n²) algorithms degrade rapidly as N increases.
- Merge Sort remains efficient and scalable.
- This demonstrates why O(n log n) algorithms are preferred for large datasets.