import java.awt.*;
import java.io.*;
import java.util.ArrayList;
import javax.swing.*;

public class BubbleSortGUI extends JFrame {

    private JTextArea outputArea;
    private JButton loadButton;
    private JButton clearButton;

    public BubbleSortGUI() {
        setTitle("Bubble Sort (Descending) - File Dataset");
        setSize(600, 500);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        initComponents();
    }

    private void initComponents() {
        setLayout(new BorderLayout(10, 10));

        JLabel titleLabel = new JLabel("Bubble Sort (Descending Order)", JLabel.CENTER);
        titleLabel.setFont(new Font("Arial", Font.BOLD, 20));
        add(titleLabel, BorderLayout.NORTH);

        outputArea = new JTextArea();
        outputArea.setEditable(false);
        outputArea.setFont(new Font("Monospaced", Font.PLAIN, 13));
        outputArea.setBackground(new Color(240, 240, 240));
        add(new JScrollPane(outputArea), BorderLayout.CENTER);

        JPanel buttonPanel = new JPanel();
        loadButton = new JButton("Load Dataset & Sort");
        clearButton = new JButton("Clear");

        loadButton.addActionListener(e -> loadAndSortFile());
        clearButton.addActionListener(e -> outputArea.setText(""));

        buttonPanel.add(loadButton);
        buttonPanel.add(clearButton);
        add(buttonPanel, BorderLayout.SOUTH);
    }

    private void loadAndSortFile() {
        File file = chooseFile();
        if (file == null) {
            file = new File("dataset.txt");
        }

        if (!file.exists()) {
            outputArea.setText("Error: dataset.txt not found!");
            return;
        }

        try {
            ArrayList<Integer> list = new ArrayList<>();
            BufferedReader reader = new BufferedReader(new FileReader(file));
            String line;

            while ((line = reader.readLine()) != null) {
                list.add(Integer.parseInt(line.trim()));
            }
            reader.close();

            int[] arr = list.stream().mapToInt(i -> i).toArray();
            int[] original = arr.clone();

            long startTime = System.nanoTime();
            bubbleSortDescending(arr);
            long endTime = System.nanoTime();
            double timeTaken = (endTime - startTime) / 1_000_000.0;

            StringBuilder result = new StringBuilder();
            result.append("Dataset File: ").append(file.getName()).append("\n\n");
            result.append("Original Array:\n").append(arrayToString(original)).append("\n\n");
            result.append("Sorted Array (Descending):\n").append(arrayToString(arr)).append("\n\n");
            result.append("Array Size: ").append(arr.length).append("\n");
            result.append("Time Taken: ").append(String.format("%.6f", timeTaken)).append(" ms\n");
            result.append("Algorithm: Bubble Sort (Descending)");

            outputArea.setText(result.toString());

        } catch (Exception e) {
            outputArea.setText("Error reading dataset file.\n" + e.getMessage());
        }
    }

    private File chooseFile() {
        JFileChooser chooser = new JFileChooser();
        chooser.setDialogTitle("Select Dataset File (TXT)");
        int result = chooser.showOpenDialog(this);
        if (result == JFileChooser.APPROVE_OPTION) {
            return chooser.getSelectedFile();
        }
        return null;
    }

    private void bubbleSortDescending(int[] arr) {
        int n = arr.length;

        for (int i = 0; i < n; i++) {
            boolean swapped = false;

            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] < arr[j + 1]) { // DESCENDING
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                    swapped = true;
                }
            }

            if (!swapped) break;
        }
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
        SwingUtilities.invokeLater(() -> new BubbleSortGUI().setVisible(true));
    }
