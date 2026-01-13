# bubblesort.py
import time

def bubble_sort(arr):
    """
    Sorts an array using the bubble sort algorithm.
    
    Args:
        arr: List of comparable elements to sort
        
    Returns:
        Tuple of (sorted list, time taken in seconds)
    """
    start_time = time.time()
    n = len(arr)
    
    # Traverse through all array elements
    for i in range(n):
        # Flag to optimize by detecting if array is already sorted
        swapped = False
        
        # Last i elements are already in place
        for j in range(0, n - i - 1):
            # Swap if the element found is greater than the next element
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        
        # If no swaps occurred, array is sorted
        if not swapped:
            break
    
    end_time = time.time()
    time_taken = end_time - start_time
    
    return arr, time_taken


# Example usage
if __name__ == "__main__":
    # Test with different arrays
    test_arrays = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 1, 4, 2, 8],
        [1, 2, 3, 4, 5],  # Already sorted
        [5, 4, 3, 2, 1],  # Reverse sorted
    ]
    
    for arr in test_arrays:
        print(f"Original: {arr}")
        sorted_arr, time_taken = bubble_sort(arr.copy())
        print(f"Sorted:   {sorted_arr}")
        print(f"Time:     {time_taken:.6f} seconds\n")