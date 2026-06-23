class Dataset:
    def __init__(self, ds_id, filename, df):
        self.id = ds_id
        self.filename = filename
        self.raw = df

        # trimming
        self.start_trim = 0
        self.end_trim = 0

        # infinite transforms (FIX)
        self.x_offset = 0.0
        self.y_offset = 0.0

        self.roll = 5

        # UI/runtime
        self.color = None
        self.curve = None

    def to_dict(self):
        return {
            "start": self.start_trim,
            "end": self.end_trim,
            "x_offset": self.x_offset,
            "y_offset": self.y_offset,
            "roll": self.roll
        }

    def apply_dict(self, d):
        self.start_trim = int(d.get("start", self.start_trim))
        self.end_trim = int(d.get("end", self.end_trim))

        self.x_offset = float(d.get("x_offset", self.x_offset))
        self.y_offset = float(d.get("y_offset", self.y_offset))

        self.roll = int(d.get("roll", self.roll))
