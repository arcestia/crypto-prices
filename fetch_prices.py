import json
import os
from datetime import datetime, timezone

import requests


API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Optional external configuration file
CONFIG_FILE = "config.json"

# Configuration values (must be provided via config.json)
COINS: list[str] = []

# Primary vs-currency used for display/history
VS_CURRENCY: str | None = None

# Optional extra currencies to fetch alongside the primary one
EXTRA_VS_CURRENCIES: list[str] = []

# README configuration (the README must contain these markers)
README_FILE = "README.md"
START_MARKER = "<!-- PRICE_TABLE_START -->"
END_MARKER = "<!-- PRICE_TABLE_END -->"

# Local history file for basic trend tracking
PRICE_HISTORY_FILE = "price_history.json"


def load_config():
    """Load configuration from config.json.

    Returns True if configuration is valid, otherwise False.
    """
    global COINS, VS_CURRENCY, EXTRA_VS_CURRENCIES

    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Please create it to configure coins and vs_currency.")
        return False

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"Error reading {CONFIG_FILE}: {e}.")
        return False

    coins = cfg.get("coins")
    if not (isinstance(coins, list) and coins):
        print("Error: 'coins' must be a non-empty list in config.json.")
        return False
    COINS = [str(c) for c in coins]

    vs = cfg.get("vs_currency")
    if not (isinstance(vs, str) and vs.strip()):
        print("Error: 'vs_currency' must be a non-empty string in config.json.")
        return False
    VS_CURRENCY = vs.strip().lower()

    extras = cfg.get("extra_vs_currencies") or []
    if isinstance(extras, list):
        EXTRA_VS_CURRENCIES = [str(c).strip().lower() for c in extras if str(c).strip()]

    return True


def all_vs_currencies():
    """Return list of all vs-currencies to request from the API."""
    currencies = [VS_CURRENCY]
    for cur in EXTRA_VS_CURRENCIES:
        if cur not in currencies:
            currencies.append(cur)
    return currencies


def fetch_prices():
    """Fetch prices (and 24h change) for all configured coins from CoinGecko."""
    params = {
        "ids": ",".join(COINS),
        "vs_currencies": ",".join(all_vs_currencies()),
        "include_24hr_change": "true",
    }
    try:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching prices from API: {e}")
        return None


def save_json(data, path="prices.json"):
    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "vs_currency": VS_CURRENCY,
        "prices": data,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_price_history():
    """Load previous price data for trend calculation."""
    if os.path.exists(PRICE_HISTORY_FILE):
        try:
            with open(PRICE_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_price_history(prices):
    """Save current prices to history file, keeping only the last 10 entries per coin."""
    if not prices:
        return

    history = load_price_history()
    timestamp = datetime.utcnow().isoformat()

    for coin, data in prices.items():
        if coin not in history:
            history[coin] = []

        # Keep only last 10 entries to avoid file bloat
        if len(history[coin]) >= 10:
            history[coin] = history[coin][-9:]

        history[coin].append(
            {
                "timestamp": timestamp,
                "price": data.get(VS_CURRENCY, 0),
                "change_24h": data.get(f"{VS_CURRENCY}_24h_change", 0),
            }
        )

    with open(PRICE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_trend_indicator(change_24h):
    """Get trend indicator emoji and color based on 24h change."""
    if change_24h is None:
        change_24h = 0

    if change_24h > 5:
        return "🚀", "#00ff00"  # Strong up
    if change_24h > 0:
        return "📈", "#90EE90"  # Up
    if change_24h > -5:
        return "📉", "#FFB6C1"  # Down
    return "💥", "#ff0000"  # Strong down


def coin_label(coin_id: str) -> str:
    mapping = {
        "bitcoin": "Bitcoin (BTC)",
        "ethereum": "Ethereum (ETH)",
        "solana": "Solana (SOL)",
        "binancecoin": "BNB (BNB)",
        "ripple": "XRP (XRP)",
    }
    return mapping.get(coin_id, coin_id.capitalize())


def format_price(value):
    if value is None:
        return "-"
    if value >= 1000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:,.4f}"
    return f"${value:.8f}"


def generate_enhanced_table(prices, coin_ids):
    """Generate an enhanced HTML table with trends and styling for the README."""
    if not prices:
        return "<p>❌ No price data available</p>"

    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    table_html = f"""
<div align="center">

### 💰 Live Cryptocurrency Prices

<table>
<thead>
<tr>
<th align="left">🪙 Cryptocurrency</th>
<th align="right">💵 Price ({VS_CURRENCY.upper()})</th>
<th align="right">📊 24h Change</th>
<th align="center">📈 Trend</th>
<th align="center">🎯 Status</th>
</tr>
</thead>
<tbody>
"""

    change_key = f"{VS_CURRENCY}_24h_change"

    for coin in coin_ids:
        coin_data = prices.get(coin, {})
        price = coin_data.get(VS_CURRENCY)
        change_24h = coin_data.get(change_key, 0)

        coin_name = coin.replace("-", " ").title()

        if price:
            if price >= 1000:
                price_str = f"${price:,.0f}"
            elif price >= 1:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.4f}"

            change_str = f"{change_24h:+.2f}%" if change_24h else "0.00%"
            change_color = "#00ff00" if change_24h and change_24h > 0 else "#ff0000" if change_24h and change_24h < 0 else "#888888"

            trend_emoji, _trend_color = get_trend_indicator(change_24h)

            if change_24h and change_24h > 2:
                status = "🔥 HOT"
            elif change_24h and change_24h > 0:
                status = "✅ UP"
            elif change_24h and change_24h > -2:
                status = "⚡ STABLE"
            else:
                status = "❄️ COLD"

            table_html += f"""
<tr>
<td><strong>{coin_name}</strong></td>
<td align="right"><code>{price_str}</code></td>
<td align="right" style="color: {change_color}"><strong>{change_str}</strong></td>
<td align="center">{trend_emoji}</td>
<td align="center">{status}</td>
</tr>
"""
        else:
            table_html += f"""
<tr>
<td><strong>{coin_name}</strong></td>
<td align="right"><code>N/A</code></td>
<td align="right">--</td>
<td align="center">❓</td>
<td align="center">⚠️ ERROR</td>
</tr>
"""

    total_coins = len([c for c in coin_ids if prices.get(c, {}).get(VS_CURRENCY)])
    avg_change = sum(
        [
            prices.get(c, {}).get(change_key, 0)
            for c in coin_ids
            if prices.get(c, {}).get(change_key) is not None
        ]
    ) / max(1, total_coins)

    table_html += f"""
</tbody>
</table>

---

**📊 Market Summary:** {total_coins}/{len(coin_ids)} coins tracked | **📈 Avg 24h Change:** {avg_change:+.2f}%  
**🕐 Last Updated:** {current_time} | **🔄 Auto-updates every ~5 minutes**

*Data provided by [CoinGecko API](https://www.coingecko.com/en/api) 🦎*

</div>
"""

    return table_html


def update_readme(table_content):
    """Update README.md between the configured markers with the new table."""
    try:
        with open(README_FILE, "r", encoding="utf-8") as file:
            content = file.read()

        start_index = content.find(START_MARKER)
        end_index = content.find(END_MARKER)

        if start_index == -1 or end_index == -1:
            print(
                f"Error: Could not find markers {START_MARKER} and {END_MARKER} in {README_FILE}"
            )
            return False

        new_content = (
            content[: start_index + len(START_MARKER)]
            + "\n"
            + table_content
            + "\n"
            + content[end_index:]
        )

        with open(README_FILE, "w", encoding="utf-8") as file:
            file.write(new_content)

        print(f"✅ Successfully updated {README_FILE} with enhanced price table")
        return True

    except FileNotFoundError:
        print(f"Error: {README_FILE} not found")
        return False
    except Exception as e:
        print(f"Error updating {README_FILE}: {e}")
        return False


def generate_html(prices_payload, path="index.html"):
    updated_at = prices_payload["updated_at_utc"]
    vs_currency = prices_payload["vs_currency"].upper()
    prices = prices_payload["prices"]

    rows = []
    for coin_id in COINS:
        coin_data = prices.get(coin_id, {})
        value = coin_data.get(VS_CURRENCY)
        rows.append(
            f"<tr><td>{coin_label(coin_id)}</td><td style='text-align:right'>{format_price(value)}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Live Cryptocurrency Prices</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#0f172a; color:#e5e7eb; margin:0; padding:0; }}
    .container {{ max-width: 720px; margin: 40px auto; padding: 24px; background:#020617; border-radius:16px; box-shadow:0 20px 40px rgba(15,23,42,0.8); border:1px solid #1e293b; }}
    h1 {{ margin-top:0; font-size: 1.8rem; color:#f9fafb; }}
    p {{ color:#9ca3af; }}
    table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
    th, td {{ padding:12px 8px; border-bottom:1px solid #1f2937; }}
    th {{ text-align:left; color:#9ca3af; font-weight:500; font-size:0.9rem; }}
    tr:last-child td {{ border-bottom:none; }}
    .footer {{ margin-top:16px; font-size:0.8rem; color:#6b7280; }}
    code {{ background:#020617; padding:2px 4px; border-radius:4px; }}
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Live Cryptocurrency Prices</h1>
    <p>Auto-updated every 5 minutes via GitHub Actions. Prices in <strong>{vs_currency}</strong>.</p>
    <p class=\"footer\">Last update (UTC): <code>{updated_at}</code></p>
    <table>
      <thead>
        <tr>
          <th>Coin</th>
          <th style=\"text-align:right\">Price</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    <p class=\"footer\">Data source: <a href=\"https://www.coingecko.com/en/api\" style=\"color:#60a5fa; text-decoration:none\">CoinGecko API</a></p>
  </div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    # Load configuration (required). Abort if invalid.
    if not load_config():
        return

    prices = fetch_prices()

    if not prices:
        print("❌ Failed to fetch price data")
        return

    # Save history and JSON snapshot
    save_price_history(prices)
    save_json(prices)

    # Build enhanced table for README and update between markers
    table_content = generate_enhanced_table(prices, COINS)
    update_readme(table_content)

    # Load payload and generate HTML page as before
    with open("prices.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    generate_html(payload)


if __name__ == "__main__":
    main()
