import json
import pandas as pd

from visualizer.dataset import Dataset


def load_csv(filename, ds_id):
    df = pd.read_csv(filename, header=None).iloc[:, :2]
    df.columns = ["t", "v"]

    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df["v"] = pd.to_numeric(df["v"], errors="coerce")
    df = df.dropna()

    return Dataset(ds_id, filename, df)


def save_project(path, datasets):
    project = {
        "files": [ds.filename for ds in datasets],
        "datasets": {ds.id: ds.to_dict() for ds in datasets}
    }

    with open(path, "w") as f:
        json.dump(project, f, indent=2)


def load_project(path):
    with open(path, "r") as f:
        return json.load(f)
