import json
import os
from datetime import datetime

import matplotlib.pyplot as plt

import fetch_prices as fp


GRAPHS_DIR = "graphs"
DASHBOARD_FILE = "GRAPHS.md"


def ensure_graphs_dir():
    os.makedirs(GRAPHS_DIR, exist_ok=True)


def load_coin_history(coin: str):
    path = os.path.join(fp.HISTORY_DIR, f"{coin}.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def format_change_pct(value: float | int | None) -> str:
    if value is None:
        return "0.00%"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "0.00%"


def format_price(value: float | int | None) -> str:
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def write_coin_markdown(coin: str, history: list[dict]) -> dict:
    """Generate graphs/<coin>.png and graphs/<coin>.md markdown, return summary info."""
    ensure_graphs_dir()

    coin_name = coin.replace("-", " ").title()
    symbol_currency = fp.VS_CURRENCY.upper()

    lines: list[str] = []
    lines.append(f"# {coin_name} ({symbol_currency})")
    lines.append("")

    # If we have at least 2 points, generate a PNG chart
    if len(history) >= 2:
        timestamps = []
        prices = []
        for entry in history:
            ts_raw = entry.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                timestamps.append(ts)
                prices.append(float(entry.get("price")))
            except Exception:
                continue

        if len(timestamps) >= 2 and len(prices) >= 2:
            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(6, 3))

            ax.plot(timestamps, prices, marker="o", linewidth=1.5, color="#60a5fa")
            ax.set_title(f"{coin_name} price in {symbol_currency}")
            ax.set_xlabel("Time")
            ax.set_ylabel(f"Price ({symbol_currency})")
            fig.autofmt_xdate(rotation=30)
            ax.grid(alpha=0.3)

            ensure_graphs_dir()
            png_path = os.path.join(GRAPHS_DIR, f"{coin}.png")
            fig.tight_layout()
            fig.savefig(png_path, dpi=120)
            plt.close(fig)

            # Embed image in markdown (relative path from repo root)
            rel_png_path = f"{GRAPHS_DIR}/{coin}.png"
            lines.append(f"![{coin_name} chart]({rel_png_path})")
            lines.append("")

    latest = history[-1] if history else None
    if latest:
        latest_price = latest.get("price")
        latest_change = latest.get("change_24h")
        lines.append(
            f"**Latest price:** `{format_price(latest_price)}` {symbol_currency}  "
        )
        lines.append(f"**24h change:** {format_change_pct(latest_change)}")
        lines.append("")

    if not history:
        lines.append("No history data available yet for this coin.")
    else:
        lines.append(
            f"| Time (UTC) | Price ({symbol_currency}) | 24h Change |"
        )
        lines.append("| ---------- | ----------------: | ----------: |")

        for entry in history:
            ts_raw = entry.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_str = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts_str = str(ts_raw)

            price_str = format_price(entry.get("price"))
            change_str = format_change_pct(entry.get("change_24h"))
            lines.append(
                f"| {ts_str} | {price_str:>16} | {change_str:>10} |"
            )

    content = "\n".join(lines) + "\n"
    out_path = os.path.join(GRAPHS_DIR, f"{coin}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated markdown for {coin} -> {out_path}")

    return {"coin": coin, "coin_name": coin_name, "latest": latest}


def write_dashboard(summaries: list[dict]):
    """Write the root GRAPHS.md dashboard linking to per-coin markdown files."""
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    symbol_currency = fp.VS_CURRENCY.upper()

    lines: list[str] = []
    lines.append("# Cryptocurrency Price History (Markdown)")
    lines.append("")
    lines.append(
        f"Auto-generated from history files. Prices in **{symbol_currency}** (primary vs_currency)."
    )
    lines.append("")
    lines.append(f"Last updated (UTC): `{now_utc}`")
    lines.append("")
    lines.append("## Coins")
    lines.append("")

    for summary in summaries:
        coin = summary["coin"]
        coin_name = summary["coin_name"]
        latest = summary.get("latest")
        latest_price = latest.get("price") if latest else None
        latest_change = latest.get("change_24h") if latest else None

        latest_str = (
            f"`{format_price(latest_price)}` {symbol_currency}"
            if latest is not None
            else "no data yet"
        )
        change_str = (
            format_change_pct(latest_change) if latest is not None else "N/A"
        )

        lines.append(
            f"- [{coin_name}](graphs/{coin}.md) – latest: {latest_str} (24h: {change_str})"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Data source: [CoinGecko API](https://www.coingecko.com/en/api). History generated from scheduled price snapshots._"
    )

    content = "\n".join(lines) + "\n"
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated dashboard -> {DASHBOARD_FILE}")


def main():
    # Load configuration (coins, currencies)
    if not fp.load_config():
        return

    ensure_graphs_dir()

    summaries: list[dict] = []
    for coin in fp.COINS:
        history = load_coin_history(coin)
        summary = write_coin_markdown(coin, history)
        summaries.append(summary)

    write_dashboard(summaries)


if __name__ == "__main__":
    main()
