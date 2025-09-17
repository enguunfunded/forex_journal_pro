import os
import matplotlib.pyplot as plt
import pandas as pd

def save_candles_image(df: pd.DataFrame, symbol: str, entry_time, base_dir: str) -> str:
    fig, ax = plt.subplots(figsize=(10,4))
    for _, row in df.iterrows():
        o,h,l,c = row["Open"], row["High"], row["Low"], row["Close"]
        t = row["Datetime"]
        ax.vlines(t, l, h)
        ax.vlines(t, min(o,c), max(o,c), linewidth=6)
    ax.set_title(f"{symbol} {entry_time}")
    path = os.path.join(base_dir,f"{symbol}_{entry_time}.png")
    os.makedirs(base_dir,exist_ok=True)
    plt.savefig(path)
    plt.close(fig)
    return path
