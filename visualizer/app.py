import sys
import json
import os
from PyQt6 import QtWidgets

from visualizer.data_io import load_csv, save_project, load_project
from visualizer.ui import MainWindow


class DatasetFactory:
    def __init__(self):
        self.file_counter = {}

    def make_id(self, filename):
        self.file_counter[filename] = self.file_counter.get(filename, 0) + 1
        return f"{filename}::{self.file_counter[filename]}"

    def create(self, filename):
        # normalize stored filename immediately
        filename = os.path.normpath(filename)
        filename = os.path.relpath(filename)

        return load_csv(filename, self.make_id(filename))


def parse_inputs(args):
    project = None
    csv_files = []

    for arg in args:
        if arg.lower().endswith(".json"):
            with open(arg, "r") as f:
                project = json.load(f)
        else:
            csv_files.append(arg)

    if project:
        csv_files = project.get("files", [])

    return csv_files, project


def main():
    app = QtWidgets.QApplication([])

    factory = DatasetFactory()

    csv_files, project = parse_inputs(sys.argv[1:])

    colors = [
        "#00ffff", "#ffff00", "#ff00ff",
        "#00ff00", "#ff4444", "#ffffff"
    ]

    win = MainWindow(colors, factory)

    if project:
        win.rebuild_from_project(project)

    def on_save():
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            win, "Save Project", "", "Project (*.json)"
        )
        if not path:
            return
        save_project(path, win.datasets)

    def on_load():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            win, "Load Project", "", "Project (*.json)"
        )
        if not path:
            return

        project_data = load_project(path)
        win.rebuild_from_project(project_data)

    win.btn_save = QtWidgets.QPushButton("Save Project")
    win.btn_load = QtWidgets.QPushButton("Load Project")

    win.vbox.insertWidget(0, win.btn_load)
    win.vbox.insertWidget(0, win.btn_save)

    win.btn_save.clicked.connect(on_save)
    win.btn_load.clicked.connect(on_load)

    win.resize(1800, 1000)
    win.show()

    app.exec()


if __name__ == "__main__":
    main()
