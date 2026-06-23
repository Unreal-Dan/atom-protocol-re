import json
import os
import pandas as pd

from visualizer.dataset import Dataset


def load_csv(filename, ds_id):
    filename = os.path.abspath(filename)

    df = pd.read_csv(filename, header=None).iloc[:, :2]
    df.columns = ["t", "v"]

    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df = df.dropna()

    return Dataset(ds_id, filename, df)

def save_project(path, datasets):
    project_dir = os.path.dirname(os.path.abspath(path))

    project = {
        "files": [
            os.path.relpath(ds.filename, project_dir)
            for ds in datasets
        ],
        "datasets": {
            ds.id: ds.to_dict() for ds in datasets
        }
    }

    with open(path, "w") as f:
        json.dump(project, f, indent=2)


def load_project(path):
    with open(path, "r") as f:
        project = json.load(f)

    project_dir = os.path.dirname(os.path.abspath(path))

    # convert relative paths back to absolute
    project["files"] = [
        os.path.normpath(os.path.join(project_dir, f))
        for f in project.get("files", [])
    ]

    return project
