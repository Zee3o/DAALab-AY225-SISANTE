import java.awt.*;
import java.io.*;
import java.util.*;
import javax.swing.*;

public class SortingGUI extends JFrame {

    /* ================= UI COMPONENTS ================= */
    private JTextArea originalArea;
    private JTextArea sortedArea;
    private JTextArea detailsArea;

    private JButton loadButton, clearButton;
    private JComboBox<String> algorithmCombo;
    private JComboBox<String> orderCombo;

    /* ================= THEME COLORS ================= */
    private final Color BG = new Color(25, 25, 25);
    private final Color PANEL = new Color(35, 35, 35);
    private final Color TEXT = new Color(230, 230, 230);
    private final Color ACCENT = new Color(90, 180, 255);

    public SortingGUI() {
        setTitle("Sorting Algorithms Visualizer");
        setSize(850, 600);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        initComponents();
    }

    private void initComponents() {
        setLayout(new BorderLayout(10, 10));
        getContentPane().setBackground(BG);

        /* ================= HEADER ================= */
        JLabel title = new JLabel("Sorting Algorithms (File Dataset)", JLabel.CENTER);
        title.setFont(new Font("Segoe UI", Font.BOLD, 22));
        title.setForeground(ACCENT);
        title.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        add(title, BorderLayout.NORTH);

        /* ================= TABS ================= */
        JTabbedPane tabs = new JTabbedPane();
        tabs.setBackground(PANEL);
        tabs.setForeground(TEXT);
        tabs.setFont(new Font("Segoe UI", Font.PLAIN, 14));

        originalArea = createTextArea();
        sortedArea = createTextArea();
        detailsArea = createTextArea();

        tabs.addTab("Original Array", wrapScroll(originalArea));
        tabs.addTab("Sorted Array", wrapScroll(sortedArea));
        tabs.addTab("Details", wrapScroll(detailsArea));

        add(tabs, BorderLayout.CENTER);

        /* ================= CONTROLS ================= */
        JPanel controls = new JPanel(new FlowLayout(FlowLayout.CENTER, 12, 10));
        controls.setBackground(PANEL);

        algorithmCombo = new JComboBox<>(new String[]{
                "Bubble Sort", "Selection Sort", "Insertion Sort",
                "Merge Sort", "Quick Sort", "Random Quick Sort"
        });

        orderCombo = new JComboBox<>(new String[]{"Ascending", "Descending"});

        loadButton = new JButton("Load & Sort");
        clearButton = new JButton("Clear");

        styleCombo(algorithmCombo);
        styleCombo(orderCombo);
        styleButton(loadButton);
        styleButton(clearButton);

        loadButton.addActionListener(e -> loadAndSortFile());
        clearButton.addActionListener(e -> clearAll());

        controls.add(new JLabel("Algorithm:", JLabel.RIGHT));
        controls.add(algorithmCombo);
        controls.add(new JLabel("Order:", JLabel.RIGHT));
        controls.add(orderCombo);
        controls.add(loadButton);
        controls.add(clearButton);

        add(controls, BorderLayout.SOUTH);
    }

    /* ================= FILE + SORT ================= */

    private void loadAndSortFile() {
        File file = chooseFile();
        if (file == null || !file.exists()) return;

        try {
            ArrayList<Integer> list = new ArrayList<>();
            BufferedReader br = new BufferedReader(new FileReader(file));
            String line;
            while ((line = br.readLine()) != null) {
                list.add(Integer.parseInt(line.trim()));
            }
            br.close();

            int[] arr = list.stream().mapToInt(i -> i).toArray();
            int[] original = arr.clone();

            boolean ascending = orderCombo.getSelectedItem().equals("Ascending");
            String algorithm = (String) algorithmCombo.getSelectedItem();

            long start = System.nanoTime();

            switch (algorithm) {
                case "Bubble Sort" -> bubbleSort(arr, ascending);
                case "Selection Sort" -> selectionSort(arr, ascending);
                case "Insertion Sort" -> insertionSort(arr, ascending);
                case "Merge Sort" -> mergeSort(arr, 0, arr.length - 1, ascending);
                case "Quick Sort" -> quickSort(arr, 0, arr.length - 1, ascending);
                case "Random Quick Sort" -> randomQuickSort(arr, 0, arr.length - 1, ascending);
            }

            long end = System.nanoTime();
            double timeMs = (end - start) / 1_000_000.0;

            originalArea.setText(arrayToMultiline(original));
            sortedArea.setText(arrayToMultiline(arr));

            detailsArea.setText(
                    "Dataset File : " + file.getName() + "\n" +
                    "Array Size   : " + arr.length + "\n" +
                    "Algorithm    : " + algorithm + "\n" +
                    "Order        : " + (ascending ? "Ascending" : "Descending") + "\n" +
                    "Time Taken   : " + String.format("%.6f ms", timeMs)
            );

        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Error reading file", "Error", JOptionPane.ERROR_MESSAGE);
        }
    }

    private File chooseFile() {
        JFileChooser chooser = new JFileChooser();
        return chooser.showOpenDialog(this) == JFileChooser.APPROVE_OPTION
                ? chooser.getSelectedFile()
                : null;
    }

    private void clearAll() {
        originalArea.setText("");
        sortedArea.setText("");
        detailsArea.setText("");
    }

    /* ================= UI HELPERS ================= */

    private JTextArea createTextArea() {
        JTextArea area = new JTextArea();
        area.setEditable(false);
        area.setLineWrap(true);           // 🔑 vertical scroll only
        area.setWrapStyleWord(true);
        area.setFont(new Font("Consolas", Font.PLAIN, 14));
        area.setBackground(BG);
        area.setForeground(TEXT);
        area.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        return area;
    }

    private JScrollPane wrapScroll(JTextArea area) {
        JScrollPane pane = new JScrollPane(area);
        pane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);
        pane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED);
        return pane;
    }

    private void styleButton(JButton btn) {
        btn.setBackground(ACCENT);
        btn.setForeground(Color.BLACK);
        btn.setFocusPainted(false);
        btn.setFont(new Font("Segoe UI", Font.BOLD, 13));
    }

    private void styleCombo(JComboBox<String> combo) {
        combo.setFont(new Font("Segoe UI", Font.PLAIN, 13));
    }

    private String arrayToMultiline(int[] arr) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < arr.length; i++) {
            sb.append(arr[i]).append(i < arr.length - 1 ? ", " : "");
            if (i % 20 == 0 && i != 0) sb.append("\n");
        }
        return sb.toString();
    }

    // ===================== SORTING ALGORITHMS =====================

    private void bubbleSort(int[] arr, boolean ascending) {
        int n = arr.length;
        for (int i = 0; i < n; i++) {
            boolean swapped = false;
            for (int j = 0; j < n - i - 1; j++) {
                if ((ascending && arr[j] > arr[j + 1]) || (!ascending && arr[j] < arr[j + 1])) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                    swapped = true;
                }
            }
            if (!swapped) break;
        }
    }

    private void selectionSort(int[] arr, boolean ascending) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            int idx = i;
            for (int j = i + 1; j < n; j++) {
                if ((ascending && arr[j] < arr[idx]) || (!ascending && arr[j] > arr[idx])) {
                    idx = j;
                }
            }
            int temp = arr[i];
            arr[i] = arr[idx];
            arr[idx] = temp;
        }
    }

    private void insertionSort(int[] arr, boolean ascending) {
        for (int i = 1; i < arr.length; i++) {
            int key = arr[i];
            int j = i - 1;
            while (j >= 0 && ((ascending && arr[j] > key) || (!ascending && arr[j] < key))) {
                arr[j + 1] = arr[j];
                j--;
            }
            arr[j + 1] = key;
        }
    }

    private void mergeSort(int[] arr, int left, int right, boolean ascending) {
        if (left < right) {
            int mid = (left + right) / 2;
            mergeSort(arr, left, mid, ascending);
            mergeSort(arr, mid + 1, right, ascending);
            merge(arr, left, mid, right, ascending);
        }
    }

    private void merge(int[] arr, int left, int mid, int right, boolean ascending) {
        int n1 = mid - left + 1;
        int n2 = right - mid;
        int[] L = new int[n1];
        int[] R = new int[n2];

        System.arraycopy(arr, left, L, 0, n1);
        System.arraycopy(arr, mid + 1, R, 0, n2);

        int i = 0, j = 0, k = left;
        while (i < n1 && j < n2) {
            if ((ascending && L[i] <= R[j]) || (!ascending && L[i] >= R[j])) {
                arr[k++] = L[i++];
            } else {
                arr[k++] = R[j++];
            }
        }

        while (i < n1) arr[k++] = L[i++];
        while (j < n2) arr[k++] = R[j++];
    }

    private void quickSort(int[] arr, int low, int high, boolean ascending) {
        if (low < high) {
            int pi = partition(arr, low, high, ascending);
            quickSort(arr, low, pi - 1, ascending);
            quickSort(arr, pi + 1, high, ascending);
        }
    }

    private int partition(int[] arr, int low, int high, boolean ascending) {
        int pivot = arr[high];
        int i = low - 1;
        for (int j = low; j < high; j++) {
            if ((ascending && arr[j] <= pivot) || (!ascending && arr[j] >= pivot)) {
                i++;
                int temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
        int temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        return i + 1;
    }

    private void randomQuickSort(int[] arr, int low, int high, boolean ascending) {
        if (low < high) {
            int pi = randomPartition(arr, low, high, ascending);
            randomQuickSort(arr, low, pi - 1, ascending);
            randomQuickSort(arr, pi + 1, high, ascending);
        }
    }

    private int randomPartition(int[] arr, int low, int high, boolean ascending) {
        int randomIndex = new Random().nextInt(high - low + 1) + low;
        int temp = arr[randomIndex];
        arr[randomIndex] = arr[high];
        arr[high] = temp;
        return partition(arr, low, high, ascending);
    }

    private String arrayToString(int[] arr) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < arr.length; i++) {
            sb.append(arr[i]);
            if (i < arr.length - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new SortingGUI().setVisible(true));
    }
}
