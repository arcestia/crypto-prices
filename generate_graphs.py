import json
import os
from datetime import datetime

import matplotlib.pyplot as plt

from fetch_prices import CONFIG_FILE, COINS, VS_CURRENCY, HISTORY_DIR, load_config


GRAPHS_DIR = "graphs"


def ensure_graphs_dir():
    os.makedirs(GRAPHS_DIR, exist_ok=True)


def load_coin_history(coin: str):
    path = os.path.join(HISTORY_DIR, f"{coin}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def generate_graph_for_coin(coin: str):
    history = load_coin_history(coin)
    if len(history) < 2:
        # Not enough data points for a meaningful graph
        print(f"Skipping {coin}: not enough history points ({len(history)})")
        return

    timestamps = [datetime.fromisoformat(entry["timestamp"]) for entry in history]
    prices = [entry["price"] for entry in history]

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(6, 3))

    ax.plot(timestamps, prices, marker="o", linewidth=1.5, color="#60a5fa")
    ax.set_title(f"{coin.replace('-', ' ').title()} price in {VS_CURRENCY.upper()}")
    ax.set_xlabel("Time")
    ax.set_ylabel(f"Price ({VS_CURRENCY.upper()})")
    fig.autofmt_xdate(rotation=30)

    ax.grid(alpha=0.3)

    ensure_graphs_dir()
    out_path = os.path.join(GRAPHS_DIR, f"{coin}.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)

    print(f"Saved graph for {coin} -> {out_path}")


def main():
    # Load configuration (coins, currencies)
    if not load_config():
        return

    ensure_graphs_dir()

    for coin in COINS:
        generate_graph_for_coin(coin)


if __name__ == "__main__":
    main()
