import java.io.*;
import java.util.*;

public class SortingCLI {

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.println("====================================");
        System.out.println("   SORTING ALGORITHMS (TERMINAL)     ");
        System.out.println("====================================");

        // 1️⃣ Get file path
        System.out.print("Enter path to dataset file: ");
        String filePath = scanner.nextLine();

        File file = new File(filePath);
        if (!file.exists()) {
            System.out.println("❌ File not found.");
            return;
        }

        // 2️⃣ Read file
        ArrayList<Integer> list = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(file))) {
            String line;
            while ((line = br.readLine()) != null) {
                list.add(Integer.parseInt(line.trim()));
            }
        } catch (IOException | NumberFormatException e) {
            System.out.println("❌ Invalid file format. One integer per line required.");
            return;
        }

        int[] arr = list.stream().mapToInt(Integer::intValue).toArray();
        int[] original = arr.clone();

        // 3️⃣ Algorithm selection
        System.out.println("\nChoose Sorting Algorithm:");
        System.out.println("1 - Bubble Sort");
        System.out.println("2 - Selection Sort");
        System.out.println("3 - Insertion Sort");
        System.out.println("4 - Merge Sort");
        System.out.println("5 - Quick Sort");
        System.out.println("6 - Random Quick Sort");
        System.out.print("Enter choice (1-6): ");
        int algoChoice = scanner.nextInt();

        // 4️⃣ Order selection
        System.out.print("\nOrder (1 = Ascending, 2 = Descending): ");
        int orderChoice = scanner.nextInt();
        boolean ascending = orderChoice == 1;

        String algorithmName = "";

        // 5️⃣ Start timing
        long start = System.nanoTime();

        switch (algoChoice) {
            case 1:
                bubbleSort(arr, ascending);
                algorithmName = "Bubble Sort";
                break;
            case 2:
                selectionSort(arr, ascending);
                algorithmName = "Selection Sort";
                break;
            case 3:
                insertionSort(arr, ascending);
                algorithmName = "Insertion Sort";
                break;
            case 4:
                mergeSort(arr, 0, arr.length - 1, ascending);
                algorithmName = "Merge Sort";
                break;
            case 5:
                quickSort(arr, 0, arr.length - 1, ascending);
                algorithmName = "Quick Sort";
                break;
            case 6:
                randomQuickSort(arr, 0, arr.length - 1, ascending);
                algorithmName = "Random Quick Sort";
                break;
            default:
                System.out.println("❌ Invalid algorithm choice.");
                return;
        }

        // 6️⃣ End timing
        long end = System.nanoTime();
        double timeMs = (end - start) / 1_000_000.0;

        // 7️⃣ Output results
        System.out.println("\n====================================");
        System.out.println("📄 DATASET INFORMATION");
        System.out.println("------------------------------------");
        System.out.println("File Name   : " + file.getName());
        System.out.println("Array Size  : " + arr.length);

        System.out.println("\n⚙ SORT CONFIGURATION");
        System.out.println("------------------------------------");
        System.out.println("Algorithm   : " + algorithmName);
        System.out.println("Order       : " + (ascending ? "Ascending" : "Descending"));

        System.out.println("\n⏱ PERFORMANCE");
        System.out.println("------------------------------------");
        System.out.printf("Time Taken  : %.6f ms%n", timeMs);

        System.out.println("\n📌 ORIGINAL ARRAY");
        System.out.println("------------------------------------");
        printArray(original);

        System.out.println("\n📌 SORTED ARRAY");
        System.out.println("------------------------------------");
        printArray(arr);

        scanner.close();
    }

    /* ================= UTILITY ================= */

    private static void printArray(int[] arr) {
        for (int i = 0; i < arr.length; i++) {
            System.out.print(arr[i]);
            if (i < arr.length - 1) System.out.print(", ");
            if (i % 20 == 0 && i != 0) System.out.println();
        }
        System.out.println();
    }

    /* ================= SORTING ALGORITHMS ================= */

    private static void bubbleSort(int[] arr, boolean asc) {
        for (int i = 0; i < arr.length; i++) {
            boolean swapped = false;
            for (int j = 0; j < arr.length - i - 1; j++) {
                if ((asc && arr[j] > arr[j + 1]) || (!asc && arr[j] < arr[j + 1])) {
                    int t = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = t;
                    swapped = true;
                }
            }
            if (!swapped) break;
        }
    }

    private static void selectionSort(int[] arr, boolean asc) {
        for (int i = 0; i < arr.length - 1; i++) {
            int idx = i;
            for (int j = i + 1; j < arr.length; j++) {
                if ((asc && arr[j] < arr[idx]) || (!asc && arr[j] > arr[idx])) {
                    idx = j;
                }
            }
            int t = arr[i];
            arr[i] = arr[idx];
            arr[idx] = t;
        }
    }

    private static void insertionSort(int[] arr, boolean asc) {
        for (int i = 1; i < arr.length; i++) {
            int key = arr[i];
            int j = i - 1;
            while (j >= 0 && ((asc && arr[j] > key) || (!asc && arr[j] < key))) {
                arr[j + 1] = arr[j];
                j--;
            }
            arr[j + 1] = key;
        }
    }

    private static void mergeSort(int[] arr, int l, int r, boolean asc) {
        if (l < r) {
            int m = (l + r) / 2;
            mergeSort(arr, l, m, asc);
            mergeSort(arr, m + 1, r, asc);
            merge(arr, l, m, r, asc);
        }
    }

    private static void merge(int[] arr, int l, int m, int r, boolean asc) {
        int[] L = Arrays.copyOfRange(arr, l, m + 1);
        int[] R = Arrays.copyOfRange(arr, m + 1, r + 1);

        int i = 0, j = 0, k = l;
        while (i < L.length && j < R.length) {
            if ((asc && L[i] <= R[j]) || (!asc && L[i] >= R[j])) {
                arr[k++] = L[i++];
            } else {
                arr[k++] = R[j++];
            }
        }
        while (i < L.length) arr[k++] = L[i++];
        while (j < R.length) arr[k++] = R[j++];
    }

    private static void quickSort(int[] arr, int low, int high, boolean asc) {
        if (low < high) {
            int pi = partition(arr, low, high, asc);
            quickSort(arr, low, pi - 1, asc);
            quickSort(arr, pi + 1, high, asc);
        }
    }

    private static int partition(int[] arr, int low, int high, boolean asc) {
        int pivot = arr[high];
        int i = low - 1;
        for (int j = low; j < high; j++) {
            if ((asc && arr[j] <= pivot) || (!asc && arr[j] >= pivot)) {
                i++;
                int t = arr[i];
                arr[i] = arr[j];
                arr[j] = t;
            }
        }
        int t = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = t;
        return i + 1;
    }

    private static void randomQuickSort(int[] arr, int low, int high, boolean asc) {
        if (low < high) {
            int pi = randomPartition(arr, low, high, asc);
            randomQuickSort(arr, low, pi - 1, asc);
            randomQuickSort(arr, pi + 1, high, asc);
        }
    }

    private static int randomPartition(int[] arr, int low, int high, boolean asc) {
        int rand = new Random().nextInt(high - low + 1) + low;
        int t = arr[rand];
        arr[rand] = arr[high];
        arr[high] = t;
        return partition(arr, low, high, asc);
    }
}
