import java.awt.*;
import java.io.*;
import java.util.ArrayList;
import javax.swing.*;
import javax.swing.border.TitledBorder;

public class SortingAlgorithm extends JFrame {

    // ===================== DATA MODEL =====================
    static class Person {
        int id;
        String firstName;
        String lastName;

        Person(int id, String firstName, String lastName) {
            this.id = id;
            this.firstName = firstName;
            this.lastName = lastName;
        }
    }

    // ===================== UI COMPONENTS =====================
    private JComboBox<String> algorithmBox;
    private JComboBox<String> columnBox;
    private JComboBox<String> orderBox;
    private JTextField rowField;
    private JButton loadButton, runButton;
    private JLabel fileLabel;
    private JProgressBar progressBar;

    private JTextArea summaryArea;
    private JTextArea fullListArea;

    private JTabbedPane tabbedPane;

    private File selectedFile;
    private ArrayList<Person> data = new ArrayList<>();

    public SortingAlgorithm() {
        setTitle("Sorting Algorithm Benchmark Tool");
        setSize(1100, 650);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout());

        // ===================== FILE PANEL =====================
        JPanel filePanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        loadButton = new JButton("Select CSV File");
        fileLabel = new JLabel("No file selected");

        filePanel.add(loadButton);
        filePanel.add(fileLabel);

        // ===================== CONTROL PANEL =====================
        algorithmBox = new JComboBox<>(new String[]{
                "Bubble Sort", "Insertion Sort", "Merge Sort"
        });

        columnBox = new JComboBox<>(new String[]{
                "ID", "First Name", "Last Name"
        });

        orderBox = new JComboBox<>(new String[]{
                "Ascending", "Descending"
        });

        rowField = new JTextField("10000");
        rowField.setPreferredSize(new Dimension(100, rowField.getPreferredSize().height));

        runButton = new JButton("Run Benchmark");

        // Single row: [Algorithm] [box] [Sort Column] [box] [Sort Order] [box] [Rows (N)] [field] [Run]
        JPanel controlPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 8));
        controlPanel.setBorder(new TitledBorder("Sorting Controls"));

        controlPanel.add(new JLabel("Algorithm:"));
        controlPanel.add(algorithmBox);

        controlPanel.add(new JLabel("Sort Column:"));
        controlPanel.add(columnBox);

        controlPanel.add(new JLabel("Sort Order:"));
        controlPanel.add(orderBox);

        controlPanel.add(new JLabel("Rows to Sort (N):"));
        controlPanel.add(rowField);

        controlPanel.add(runButton);

        JPanel topPanel = new JPanel(new BorderLayout());
        topPanel.add(filePanel, BorderLayout.NORTH);
        topPanel.add(controlPanel, BorderLayout.SOUTH);
        add(topPanel, BorderLayout.NORTH);

        // ===================== TABBED OUTPUT =====================
        tabbedPane = new JTabbedPane();

        summaryArea = new JTextArea();
        summaryArea.setEditable(false);
        summaryArea.setFont(new Font("Monospaced", Font.PLAIN, 12));

        fullListArea = new JTextArea();
        fullListArea.setEditable(false);
        fullListArea.setFont(new Font("Monospaced", Font.PLAIN, 12));

        tabbedPane.addTab("Benchmark Results", new JScrollPane(summaryArea));
        tabbedPane.addTab("Full Sorted List", new JScrollPane(fullListArea));

        add(tabbedPane, BorderLayout.CENTER);

        // ===================== PROGRESS BAR =====================
        progressBar = new JProgressBar();
        progressBar.setStringPainted(true);
        add(progressBar, BorderLayout.SOUTH);

        // ===================== EVENTS =====================
        loadButton.addActionListener(e -> chooseFile());
        runButton.addActionListener(e -> runBenchmark());
    }

    // ===================== FILE CHOOSER =====================
    private void chooseFile() {
        JFileChooser chooser = new JFileChooser();
        if (chooser.showOpenDialog(this) == JFileChooser.APPROVE_OPTION) {
            selectedFile = chooser.getSelectedFile();
            fileLabel.setText(selectedFile.getName());
        }
    }

    // ===================== BENCHMARK PROCESS =====================
    private void runBenchmark() {
        if (selectedFile == null) {
            JOptionPane.showMessageDialog(this, "Please select a CSV file first.");
            return;
        }

        int N;
        try {
            N = Integer.parseInt(rowField.getText());
        } catch (NumberFormatException e) {
            JOptionPane.showMessageDialog(this, "Invalid row count.");
            return;
        }

        String algorithm = (String) algorithmBox.getSelectedItem();
        String column = (String) columnBox.getSelectedItem();
        boolean ascending = orderBox.getSelectedItem().equals("Ascending");

        if ((algorithm.equals("Bubble Sort") || algorithm.equals("Insertion Sort")) && N > 20000) {
            int choice = JOptionPane.showConfirmDialog(
                    this,
                    "Warning: O(n²) algorithm with large N.\nThis may take a long time.\nContinue?",
                    "Performance Warning",
                    JOptionPane.YES_NO_OPTION
            );
            if (choice != JOptionPane.YES_OPTION) return;
        }

        summaryArea.setText("");
        fullListArea.setText("");
        progressBar.setValue(0);
        tabbedPane.setSelectedIndex(0);

        new Thread(() -> {
            try {
                long loadStart = System.nanoTime();
                loadCSV(selectedFile, N);
                long loadEnd = System.nanoTime();

                progressBar.setValue(30);

                long sortStart = System.nanoTime();

                switch (algorithm) {
                    case "Bubble Sort" -> bubbleSort(column, ascending);
                    case "Insertion Sort" -> insertionSort(column, ascending);
                    case "Merge Sort" -> mergeSort(0, data.size() - 1, column, ascending);
                }

                long sortEnd = System.nanoTime();
                progressBar.setValue(100);

                displaySummary(loadEnd - loadStart, sortEnd - sortStart);
                displayFullList();

            } catch (Exception ex) {
                summaryArea.setText("Error: " + ex.getMessage());
            }
        }).start();
    }

    // ===================== CSV LOADING =====================
    private void loadCSV(File file, int N) throws IOException {
        data.clear();
        BufferedReader br = new BufferedReader(new FileReader(file));
        String line = br.readLine(); // header

        int count = 0;
        while ((line = br.readLine()) != null && count < N) {
            String[] p = line.split(",");
            data.add(new Person(
                    Integer.parseInt(p[0].trim()),
                    p[1].trim(),
                    p[2].trim()
            ));
            count++;
        }
        br.close();
    }

    // ===================== COMPARISON =====================
    private int compare(Person a, Person b, String field, boolean ascending) {
        int result = switch (field) {
            case "First Name" -> a.firstName.compareToIgnoreCase(b.firstName);
            case "Last Name" -> a.lastName.compareToIgnoreCase(b.lastName);
            default -> Integer.compare(a.id, b.id);
        };
        return ascending ? result : -result;
    }

    // ===================== SORTING ALGORITHMS =====================
    private void bubbleSort(String field, boolean ascending) {
        for (int i = 0; i < data.size() - 1; i++) {
            for (int j = 0; j < data.size() - i - 1; j++) {
                if (compare(data.get(j), data.get(j + 1), field, ascending) > 0) {
                    swap(j, j + 1);
                }
            }
            progressBar.setValue((i * 70) / data.size());
        }
    }

    private void insertionSort(String field, boolean ascending) {
        for (int i = 1; i < data.size(); i++) {
            Person key = data.get(i);
            int j = i - 1;

            while (j >= 0 && compare(data.get(j), key, field, ascending) > 0) {
                data.set(j + 1, data.get(j));
                j--;
            }
            data.set(j + 1, key);
            progressBar.setValue((i * 70) / data.size());
        }
    }

    private void mergeSort(int left, int right, String field, boolean ascending) {
        if (left < right) {
            int mid = (left + right) / 2;
            mergeSort(left, mid, field, ascending);
            mergeSort(mid + 1, right, field, ascending);
            merge(left, mid, right, field, ascending);
        }
    }

    private void merge(int left, int mid, int right, String field, boolean ascending) {
        ArrayList<Person> temp = new ArrayList<>();
        int i = left, j = mid + 1;

        while (i <= mid && j <= right) {
            if (compare(data.get(i), data.get(j), field, ascending) <= 0) {
                temp.add(data.get(i++));
            } else {
                temp.add(data.get(j++));
            }
        }

        while (i <= mid) temp.add(data.get(i++));
        while (j <= right) temp.add(data.get(j++));

        for (int k = 0; k < temp.size(); k++) {
            data.set(left + k, temp.get(k));
        }
    }

    private void swap(int i, int j) {
        Person t = data.get(i);
        data.set(i, data.get(j));
        data.set(j, t);
    }

    // ===================== OUTPUT =====================
    private void displaySummary(long loadTime, long sortTime) {
        summaryArea.append("=== Benchmark Results ===\n");
        summaryArea.append("File Load Time: " + loadTime / 1_000_000 + " ms\n");
        summaryArea.append("Sort Time: " + sortTime / 1_000_000 + " ms\n\n");

        summaryArea.append("First 10 Sorted Records:\n");
        summaryArea.append("ID\tFirst Name\tLast Name\n");

        for (int i = 0; i < Math.min(10, data.size()); i++) {
            Person p = data.get(i);
            summaryArea.append(
                    String.format("%-10d %-15s %-15s%n", p.id, p.firstName, p.lastName)
            );
        }
    }

    private void displayFullList() {
        fullListArea.setText("ID\tFirst Name\tLast Name\n");
        for (Person p : data) {
            fullListArea.append(
                    String.format("%-10d %-15s %-15s%n", p.id, p.firstName, p.lastName)
            );
        }
    }

    // ===================== MAIN =====================
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new SortingAlgorithm().setVisible(true));
    }
}
