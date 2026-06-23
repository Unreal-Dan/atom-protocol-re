import numpy as np


def decode_trim(raw_value, n):
    pct = raw_value / 10000.0
    pct = max(0.0, min(1.0, pct))
    return int(n * pct)


def apply_roll(df, w):
    if w <= 1:
        return df.copy()
    out = df.copy()
    out["v"] = out["v"].rolling(w, center=True, min_periods=1).mean()
    return out.dropna()


def recompute(ds):
    d = ds.raw
    n = len(d)
    if n < 2:
        return None

    s = decode_trim(ds.start_trim, n)
    e = n - decode_trim(ds.end_trim, n)

    s = max(0, min(n - 2, s))
    e = max(s + 1, min(n, e))

    d = d.iloc[s:e]
    d = apply_roll(d, ds.roll)

    d = d.copy()
    return d
