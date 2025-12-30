import numpy as np

def slope(series):
    t = np.arange(len(series))
    return np.polyfit(t, series, 1)[0]

def stats(series):
    return {
        "mean": np.mean(series),
        "std": np.std(series),
        "slope": slope(series),
        "min": np.min(series),
        "max": np.max(series)
    }