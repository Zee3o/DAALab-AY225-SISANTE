import java.awt.*;
import java.awt.event.*;
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
    private JLabel statusLabel;

    /* ================= THEME COLORS ================= */
    private final Color BG = new Color(22, 22, 22);
    private final Color PANEL = new Color(32, 32, 32);
    private final Color CARD = new Color(38, 38, 38);
    private final Color TEXT = new Color(230, 230, 230);
    private final Color MUTED = new Color(170, 170, 170);
    private final Color ACCENT = new Color(80, 160, 230);

    public SortingGUI() {
        setTitle("Sorting Algorithms Visualizer");
        setSize(900, 620);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        initComponents();
    }

    private void initComponents() {
        setLayout(new BorderLayout(10, 10));
        getContentPane().setBackground(BG);

        /* ================= HEADER ================= */
        JLabel title = new JLabel("Sorting Algorithms (File Dataset)", JLabel.CENTER);
        title.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 22));
        title.setForeground(ACCENT);
        title.setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));
        add(title, BorderLayout.NORTH);

        /* ================= CENTER ================= */
        add(createTabbedSection(), BorderLayout.CENTER);

        /* ================= BOTTOM ================= */
        add(createBottomSection(), BorderLayout.SOUTH);
    }

    /* ================= TABS ================= */

    private JTabbedPane createTabbedSection() {
        JTabbedPane tabs = new JTabbedPane();
        tabs.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 14));
        tabs.setBackground(PANEL);
        tabs.setForeground(TEXT);

        originalArea = createTextArea();
        sortedArea = createTextArea();
        detailsArea = createTextArea();

        tabs.addTab("Original", createCard(originalArea));
        tabs.addTab("Sorted", createCard(sortedArea));
        tabs.addTab("Statistics", createCard(detailsArea));

        return tabs;
    }

    private JPanel createCard(JTextArea area) {
        JPanel card = new JPanel(new BorderLayout());
        card.setBackground(CARD);
        card.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        card.add(wrapScroll(area), BorderLayout.CENTER);
        return card;
    }

    /* ================= BOTTOM SECTION ================= */

    private JPanel createBottomSection() {
        JPanel bottom = new JPanel(new BorderLayout());
        bottom.setBackground(PANEL);
        bottom.setBorder(BorderFactory.createEmptyBorder(8, 12, 8, 12));

        bottom.add(createControls(), BorderLayout.CENTER);
        bottom.add(createStatusBar(), BorderLayout.SOUTH);

        return bottom;
    }

    private JPanel createControls() {
        JPanel controls = new JPanel(new FlowLayout(FlowLayout.CENTER, 18, 12));
        controls.setBackground(PANEL);

        algorithmCombo = new JComboBox<>(new String[]{
                "Bubble Sort",
                "Selection Sort",
                "Insertion Sort",
                "Merge Sort",
                "Quick Sort",
                "Random Quick Sort"
        });

        orderCombo = new JComboBox<>(new String[]{"Ascending", "Descending"});

        loadButton = new JButton("Load & Sort");
        clearButton = new JButton("Clear");

        styleCombo(algorithmCombo);
        styleCombo(orderCombo);
        styleButton(loadButton, true);
        styleButton(clearButton, false);

        loadButton.addActionListener(e -> loadAndSortFile());
        clearButton.addActionListener(e -> clearAll());

        controls.add(new JLabel("Algorithm:", JLabel.RIGHT));
        controls.add(algorithmCombo);
        controls.add(new JLabel("Order:", JLabel.RIGHT));
        controls.add(orderCombo);
        controls.add(loadButton);
        controls.add(clearButton);

        return controls;
    }

    private JPanel createStatusBar() {
        JPanel statusPanel = new JPanel(new BorderLayout());
        statusPanel.setBackground(PANEL);

        statusLabel = new JLabel("Ready");
        statusLabel.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 12));
        statusLabel.setForeground(MUTED);

        statusPanel.add(statusLabel, BorderLayout.WEST);
        return statusPanel;
    }

    /* ================= FILE + SORT ================= */

    private void loadAndSortFile() {
        File file = chooseFile();
        if (file == null || !file.exists()) return;

        statusLabel.setText("Loading file...");
        ArrayList<Integer> list = new ArrayList<>();

        try (BufferedReader br = new BufferedReader(new FileReader(file))) {
            String line;
            while ((line = br.readLine()) != null) {
                list.add(Integer.parseInt(line.trim()));
            }
        } catch (IOException | NumberFormatException ex) {
            JOptionPane.showMessageDialog(
                    this,
                    "Invalid file format.\nFile must contain one integer per line.",
                    "File Error",
                    JOptionPane.ERROR_MESSAGE
            );
            statusLabel.setText("Error loading file");
            return;
        }

        int[] arr = list.stream().mapToInt(Integer::intValue).toArray();
        int[] original = arr.clone();

        boolean ascending = "Ascending".equals(orderCombo.getSelectedItem());
        String algorithm = (String) algorithmCombo.getSelectedItem();

        statusLabel.setText("Sorting...");
        long start = System.nanoTime();

        switch (algorithm) {
            case "Bubble Sort":
                bubbleSort(arr, ascending);
                break;
            case "Selection Sort":
                selectionSort(arr, ascending);
                break;
            case "Insertion Sort":
                insertionSort(arr, ascending);
                break;
            case "Merge Sort":
                mergeSort(arr, 0, arr.length - 1, ascending);
                break;
            case "Quick Sort":
                quickSort(arr, 0, arr.length - 1, ascending);
                break;
            case "Random Quick Sort":
                randomQuickSort(arr, 0, arr.length - 1, ascending);
                break;
        }

        long end = System.nanoTime();
        double timeMs = (end - start) / 1_000_000.0;

        originalArea.setText(arrayToMultiline(original));
        sortedArea.setText(arrayToMultiline(arr));

        detailsArea.setText(
                "📄 DATASET INFORMATION\n" +
                "────────────────────────\n" +
                "File Name   : " + file.getName() + "\n" +
                "Array Size  : " + arr.length + "\n\n" +
                "⚙ SORT CONFIGURATION\n" +
                "────────────────────────\n" +
                "Algorithm   : " + algorithm + "\n" +
                "Order       : " + (ascending ? "Ascending" : "Descending") + "\n\n" +
                "⏱ PERFORMANCE\n" +
                "────────────────────────\n" +
                String.format("Time Taken  : %.6f ms", timeMs)
        );

        statusLabel.setText("Sorting completed");
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
        statusLabel.setText("Cleared");
    }

    /* ================= UI HELPERS ================= */

    private JTextArea createTextArea() {
        JTextArea area = new JTextArea();
        area.setEditable(false);
        area.setLineWrap(true);
        area.setWrapStyleWord(true);
        area.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 14));
        area.setBackground(CARD);
        area.setForeground(TEXT);
        area.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
        return area;
    }

    private JScrollPane wrapScroll(JTextArea area) {
        JScrollPane pane = new JScrollPane(area);
        pane.setBorder(BorderFactory.createEmptyBorder());
        pane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);
        pane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED);
        return pane;
    }

    private void styleButton(JButton btn, boolean primary) {
        btn.setBackground(primary ? ACCENT : new Color(90, 90, 90));
        btn.setForeground(Color.BLACK);
        btn.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 13));
        btn.setFocusPainted(false);
        btn.setCursor(new Cursor(Cursor.HAND_CURSOR));

        btn.addMouseListener(new MouseAdapter() {
            public void mouseEntered(MouseEvent e) {
                btn.setBackground(btn.getBackground().darker());
            }

            public void mouseExited(MouseEvent e) {
                btn.setBackground(primary ? ACCENT : new Color(90, 90, 90));
            }
        });
    }

    private void styleCombo(JComboBox<String> combo) {
        combo.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 13));
    }

    private String arrayToMultiline(int[] arr) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < arr.length; i++) {
            sb.append(arr[i]);
            if (i < arr.length - 1) sb.append(", ");
            if (i % 20 == 0 && i != 0) sb.append("\n");
        }
        return sb.toString();
    }

    /* ================= SORTING ALGORITHMS ================= */

    private void bubbleSort(int[] arr, boolean asc) {
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

    private void selectionSort(int[] arr, boolean asc) {
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

    private void insertionSort(int[] arr, boolean asc) {
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

    private void mergeSort(int[] arr, int l, int r, boolean asc) {
        if (l < r) {
            int m = (l + r) / 2;
            mergeSort(arr, l, m, asc);
            mergeSort(arr, m + 1, r, asc);
            merge(arr, l, m, r, asc);
        }
    }

    private void merge(int[] arr, int l, int m, int r, boolean asc) {
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

    private void quickSort(int[] arr, int low, int high, boolean asc) {
        if (low < high) {
            int pi = partition(arr, low, high, asc);
            quickSort(arr, low, pi - 1, asc);
            quickSort(arr, pi + 1, high, asc);
        }
    }

    private int partition(int[] arr, int low, int high, boolean asc) {
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

    private void randomQuickSort(int[] arr, int low, int high, boolean asc) {
        if (low < high) {
            int pi = randomPartition(arr, low, high, asc);
            randomQuickSort(arr, low, pi - 1, asc);
            randomQuickSort(arr, pi + 1, high, asc);
        }
    }

    private int randomPartition(int[] arr, int low, int high, boolean asc) {
        int rand = new Random().nextInt(high - low + 1) + low;
        int t = arr[rand];
        arr[rand] = arr[high];
        arr[high] = t;
        return partition(arr, low, high, asc);
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new SortingGUI().setVisible(true));
    }
}
