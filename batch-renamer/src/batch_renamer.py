import os
import re
import difflib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QTextEdit, QFileDialog, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt

# Function to rename files
def rename_files(
    folder_paths,
    pattern_to_remove,
    occurrence_to_remove='all',
    pattern_to_replace_with='',
    pattern_to_add='',
    add_position='end',
    extension_filter='',
    use_regex=False,
    dry_run=True,
    interactive=False,
    parent=None,
    remembered_choices=None
):
    planned_changes = []
    replaced_occurrences = {}  # filename -> tuple of (set of replaced spans, set of added spans)
    if remembered_choices is None:
        remembered_choices = {}

    no_files_found = True

    for folder_path in folder_paths:
        if not os.path.isdir(folder_path):
            continue

        for filename in os.listdir(folder_path):
            if extension_filter and not filename.endswith(extension_filter):
                continue

            new_name = filename
            original_name = filename
            replaced_spans = set()
            added_spans = set()

            if pattern_to_remove:
                if use_regex:
                    matches = list(re.finditer(pattern_to_remove, new_name))
                else:
                    matches = list(re.finditer(re.escape(pattern_to_remove), new_name))

                if matches:
                    no_files_found = False
                    if interactive and len(matches) > 1:
                        # Only ask once per filename if multiple matches
                        if filename not in remembered_choices:
                            options = ", ".join(str(i+1) for i in range(len(matches))) + ", l (last), a (all)"
                            choice, ok = QInputDialog.getText(
                                parent, "Select Occurrence",
                                f"File: {filename}\nOccurrences found: {len(matches)}\nEnter which occurrence(s) to replace ({options}):"
                            )
                            # Normalize empty input to None
                            remembered_choices[filename] = choice.strip() if ok and choice.strip() else None
                        choice = remembered_choices[filename]

                        if choice:
                            if choice.lower() == 'l':
                                idx = len(matches) - 1
                                match = matches[idx]
                                new_name = new_name[:match.start()] + pattern_to_replace_with + new_name[match.end():]
                                replaced_spans.add((match.start(), match.end()))
                            elif choice.lower() == 'a':
                                if use_regex:
                                    new_name = re.sub(pattern_to_remove, pattern_to_replace_with, new_name)
                                    replaced_spans.update((m.start(), m.end()) for m in matches)
                                else:
                                    new_name = new_name.replace(pattern_to_remove, pattern_to_replace_with)
                                    replaced_spans.update((m.start(), m.end()) for m in matches)
                            else:
                                # support comma separated indices like "1,3"
                                indices = [int(c)-1 for c in choice.split(',') if c.strip().isdigit()]
                                for idx in sorted(indices, reverse=True):
                                    if 0 <= idx < len(matches):
                                        match = matches[idx]
                                        new_name = new_name[:match.start()] + pattern_to_replace_with + new_name[match.end():]
                                        replaced_spans.add((match.start(), match.end()))
                    else:
                        if occurrence_to_remove == 'first':
                            idx = 0
                            match = matches[idx]
                            new_name = new_name[:match.start()] + pattern_to_replace_with + new_name[match.end():]
                            replaced_spans.add((match.start(), match.end()))
                        elif occurrence_to_remove == 'last':
                            idx = len(matches) - 1
                            match = matches[idx]
                            new_name = new_name[:match.start()] + pattern_to_replace_with + new_name[match.end():]
                            replaced_spans.add((match.start(), match.end()))
                        else:
                            if use_regex:
                                new_name = re.sub(pattern_to_remove, pattern_to_replace_with, new_name)
                                replaced_spans.update((m.start(), m.end()) for m in matches)
                            else:
                                new_name = new_name.replace(pattern_to_remove, pattern_to_replace_with)
                                replaced_spans.update((m.start(), m.end()) for m in matches)

            if pattern_to_add:
                if add_position == 'start':
                    new_name = pattern_to_add + new_name
                    added_spans.add((0, len(pattern_to_add)))
                else:
                    name, ext = os.path.splitext(new_name)
                    new_name = name + pattern_to_add + ext
                    added_spans.add((len(name), len(name) + len(pattern_to_add)))

            if new_name != original_name:
                planned_changes.append((original_name, new_name, folder_path))
                replaced_occurrences[filename] = (replaced_spans, added_spans)

    if no_files_found and dry_run:
        # Show message only if pattern_to_remove is not empty
        if pattern_to_remove:
            QMessageBox.information(parent, "No Files Found", "No files matching the specified pattern were found.")

    if not dry_run:
        for original_name, new_name, folder_path in planned_changes:
            try:
                os.rename(
                    os.path.join(folder_path, original_name),
                    os.path.join(folder_path, new_name)
                )
            except Exception as e:
                QMessageBox.critical(parent, "Error", f"Failed to rename {original_name} -> {new_name}: {e}")

    return planned_changes, replaced_occurrences

# GUI Application
class RenameApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch File Renamer")
        self.folder_paths = []
        self.remembered_choices = {}
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Folder selection
        self.folder_label = QLabel("No folders selected")
        layout.addWidget(self.folder_label)
        select_btn = QPushButton("Select Folders")
        select_btn.clicked.connect(self.select_folders)
        layout.addWidget(select_btn)

        # Pattern to remove
        layout.addWidget(QLabel("Pattern to Remove:"))
        self.pattern_to_remove = QLineEdit()
        layout.addWidget(self.pattern_to_remove)

        # Pattern to replace with
        layout.addWidget(QLabel("Replace With (optional):"))
        self.pattern_to_replace_with = QLineEdit()
        layout.addWidget(self.pattern_to_replace_with)

        # Occurrence options
        layout.addWidget(QLabel("Occurrence to Remove:"))
        self.occurrence = QComboBox()
        self.occurrence.addItems(['all', 'first', 'last'])
        layout.addWidget(self.occurrence)

        # Pattern to add
        layout.addWidget(QLabel("Pattern to Add:"))
        self.pattern_to_add = QLineEdit()
        layout.addWidget(self.pattern_to_add)

        # Add position
        layout.addWidget(QLabel("Add Position:"))
        self.add_position = QComboBox()
        self.add_position.addItems(['start', 'end'])
        layout.addWidget(self.add_position)

        # Extension filter
        layout.addWidget(QLabel("Extension Filter (e.g., .txt):"))
        self.extension_filter = QLineEdit()
        layout.addWidget(self.extension_filter)

        # Regex option
        self.use_regex = QCheckBox("Use Regular Expression")
        layout.addWidget(self.use_regex)

        # Interactive option
        self.interactive = QCheckBox("Interactive Mode (ask which occurrence to replace)")
        layout.addWidget(self.interactive)

        # Action buttons
        preview_btn = QPushButton("Preview Changes")
        preview_btn.clicked.connect(self.preview_rename)
        layout.addWidget(preview_btn)

        self.redo_btn = QPushButton("Redo Preview")
        self.redo_btn.clicked.connect(self.redo_preview)
        layout.addWidget(self.redo_btn)

        perform_btn = QPushButton("Perform Rename")
        perform_btn.clicked.connect(self.perform_rename)
        layout.addWidget(perform_btn)

        # Preview area
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)

        # Color legend label
        self.legend_label = QLabel()
        self.legend_label.setText(
            '<b>Color Legend:</b> '
            '<span style="background-color:red; color:white; padding:2px;"> Replaced Occurrence </span> '
            '<span style="background-color:orange; color:white; padding:2px;"> Unchanged Pattern Match </span> '
            '<span style="background-color:green; color:white; padding:2px;"> Added Pattern </span>'
        )
        layout.addWidget(self.legend_label)

        self.setLayout(layout)

    def select_folders(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.folder_paths = [path]
            self.folder_label.setText(path)

    def preview_rename(self):
        pattern = self.pattern_to_remove.text().strip()
        use_regex = self.use_regex.isChecked()
        planned, replaced_occurrences = rename_files(
            self.folder_paths,
            pattern,
            self.occurrence.currentText(),
            self.pattern_to_replace_with.text(),
            self.pattern_to_add.text(),
            self.add_position.currentText(),
            self.extension_filter.text().strip(),
            use_regex,
            dry_run=True,
            interactive=self.interactive.isChecked(),
            parent=self,
            remembered_choices=self.remembered_choices
        )

        html = ""
        for original, new, folder in planned:
            replaced_spans, added_spans = replaced_occurrences.get(original, (set(), set()))
            regex_pattern = pattern if use_regex else re.escape(pattern)
            # Sort replaced spans by start index
            replaced_spans_sorted = sorted(replaced_spans, key=lambda x: x[0])
            orig_html = ""
            last_idx = 0
            # Iterate over replaced spans to build highlighted html
            for start, end in replaced_spans_sorted:
                # Add text before replaced span, highlight pattern matches in orange
                segment = original[last_idx:start]
                last = 0
                for match in re.finditer(regex_pattern, segment):
                    s, e = match.start(), match.end()
                    orig_html += segment[last:s]
                    orig_html += f'<span style="background-color:orange; color:white;">{segment[s:e]}</span>'
                    last = e
                orig_html += segment[last:]
                # Add replaced span in red
                orig_html += f'<span style="background-color:red; color:white;">{original[start:end]}</span>'
                last_idx = end
            # Add remaining text after last replaced span, highlight pattern matches in orange
            segment = original[last_idx:]
            last = 0
            for match in re.finditer(regex_pattern, segment):
                s, e = match.start(), match.end()
                orig_html += segment[last:s]
                orig_html += f'<span style="background-color:orange; color:white;">{segment[s:e]}</span>'
                last = e
            orig_html += segment[last:]
            # Arrow
            html += orig_html + " -> "
            # New with highlights
            # Highlight added spans in green distinctly
            new_html = ""
            last_idx = 0
            added_spans_sorted = sorted(added_spans, key=lambda x: x[0])
            for start, end in added_spans_sorted:
                # Add text before added span
                new_html += new[last_idx:start]
                # Add added span in green
                new_html += f'<span style="background-color:green; color:white;">{new[start:end]}</span>'
                last_idx = end
            # Add remaining text after last added span
            new_html += new[last_idx:]
            html += new_html + "<br>"
        self.preview_text.setHtml(html)

    def redo_preview(self):
        self.remembered_choices = {}
        self.preview_rename()

    def perform_rename(self):
        planned, _ = rename_files(
            self.folder_paths,
            self.pattern_to_remove.text().strip(),
            self.occurrence.currentText(),
            self.pattern_to_replace_with.text(),
            self.pattern_to_add.text(),
            self.add_position.currentText(),
            self.extension_filter.text().strip(),
            self.use_regex.isChecked(),
            dry_run=False,
            interactive=self.interactive.isChecked(),
            parent=self,
            remembered_choices=self.remembered_choices
        )
        QMessageBox.information(self, "Rename Complete", f"Renamed {len(planned)} files.")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ex = RenameApp()
    ex.show()
    sys.exit(app.exec_())
