# Step 2: Calculate return and risk numbers, and draw the charts
#
# Question: Do the coins that earned more also carry more risk?
#
# Reads data/raw/ (made by download_data.py) and writes:
#   outputs/metrics_5y.csv, outputs/metrics_1y.csv   summary tables
#   docs/data/metrics.json                            numbers for the website
#   docs/images/*.png                                 charts for the website
#
# Run from the project folder:  python src/analysis.py

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

RAW_DIR = os.path.join("data", "raw")
OUT_DIR = "outputs"
IMG_DIR = os.path.join("docs", "images")
SITE_DATA = os.path.join("docs", "data", "metrics.json")

COINS = ["BTC", "ETH", "USDT", "BNB", "XRP"]
NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "USDT": "Tether (USDT)",
         "BNB": "BNB", "XRP": "XRP"}
COLORS = {"BTC": "#eb6834", "ETH": "#2a78d6", "USDT": "#1baf7a",
          "BNB": "#eda100", "XRP": "#e87ba4"}

DAYS_PER_YEAR = 365     # crypto trades every day, including weekends
ONE_YEAR_START = "2025-10-01"

TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"


# ---------- Load data ----------

def load_prices():
    closes, volumes = {}, {}
    for coin in COINS:
        df = pd.read_csv(os.path.join(RAW_DIR, coin + ".csv"), parse_dates=["Date"])
        df = df.set_index("Date")
        closes[coin] = df["Close"]
        volumes[coin] = df["Volume"]
    return pd.DataFrame(closes), pd.DataFrame(volumes)


def load_risk_free(start, end):
    # ^IRX is quoted in percent (e.g. 4.3 means 4.3% a year)
    df = pd.read_csv(os.path.join(RAW_DIR, "TBILL_3M.csv"), parse_dates=["Date"])
    df = df[(df["Date"] >= start) & (df["Date"] <= end)]
    return df["Close"].mean() / 100


def month_end_prices(series):
    # pandas 2.2+ uses "ME" for month-end; older pandas uses "M"
    try:
        return series.resample("ME").last()
    except ValueError:
        return series.resample("M").last()


# ---------- Metrics ----------

def calc_metrics(prices, start, end):
    window = prices.loc[start:end]
    daily = window.pct_change().dropna()
    rf = load_risk_free(start, end)
    years = (window.index[-1] - window.index[0]).days / DAYS_PER_YEAR

    rows = {}
    for coin in COINS:
        p = window[coin]
        r = daily[coin]

        total_return = p.iloc[-1] / p.iloc[0] - 1
        annual_return = (1 + total_return) ** (1 / years) - 1
        annual_vol = r.std() * np.sqrt(DAYS_PER_YEAR)
        # Sharpe ratio: extra yearly return over T-bills, per unit of risk
        sharpe = (r.mean() * DAYS_PER_YEAR - rf) / annual_vol

        # Drawdown: how far the price is below its highest point so far
        drawdown = p / p.cummax() - 1
        trough_date = drawdown.idxmin()
        peak_date = p.loc[:trough_date].idxmax()

        rows[coin] = {
            "name": NAMES[coin],
            "start_price": p.iloc[0],
            "end_price": p.iloc[-1],
            "total_return": total_return,
            "annual_return": annual_return,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": drawdown.min(),
            "drawdown_peak_date": peak_date.strftime("%Y-%m-%d"),
            "drawdown_bottom_date": trough_date.strftime("%Y-%m-%d"),
            "best_day": r.max(),
            "worst_day": r.min(),
            "share_of_up_days": (r > 0).mean(),
        }
    table = pd.DataFrame(rows).T
    return table, rf


def correlation(prices):
    return prices.pct_change().dropna().corr()


# ---------- Chart helpers ----------

def style(ax, title, subtitle=None):
    ax.set_title(title, loc="left", fontsize=13, color=TEXT, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=MUTED)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, filename):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, filename), dpi=150, facecolor="white")
    plt.close(fig)


def money(x, _pos=None):
    for limit, unit in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if abs(x) >= limit:
            return "$" + format(x / limit, "g") + unit
    if abs(x) >= 1:
        return "$" + format(x, ",.0f")
    return "$" + format(x, "g")


PCT = mtick.PercentFormatter(1.0, decimals=0)


# ---------- Charts for one coin ----------

def coin_charts(coin, price, volume):
    color = COLORS[coin]
    name = NAMES[coin]
    daily = price.pct_change().dropna()

    # 1. Price
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(price.index, price, color=color, linewidth=1.6)
    if coin != "USDT":
        ax.set_yscale("log")
    ax.yaxis.set_major_locator(mtick.LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(money))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    style(ax, name + " price (USD)",
          "Daily closing price" + ("" if coin == "USDT" else ", log scale: equal steps = equal % change"))
    save(fig, coin + "_01_price.png")

    # 2. Trading volume (30-day average)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(volume.index, volume.rolling(30).mean(), color=color, linewidth=1.6)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(money))
    style(ax, name + " trading volume (USD)", "30-day average of daily volume")
    save(fig, coin + "_02_volume.png")

    # 3. Monthly returns
    monthly = month_end_prices(price)
    monthly_ret = monthly.pct_change()
    monthly_ret.iloc[0] = monthly.iloc[0] / price.iloc[0] - 1
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bar_colors = [color if v >= 0 else "#8f8d86" for v in monthly_ret]
    ax.bar(monthly_ret.index, monthly_ret, width=24, color=bar_colors)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=2 if coin == "USDT" else 0))
    style(ax, name + " monthly returns", "Colored = up month, gray = down month")
    save(fig, coin + "_03_monthly_returns.png")

    # 4. Daily return distribution
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.hist(daily, bins=80, color=color, edgecolor="white", linewidth=0.4)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1 if coin == "USDT" else 0))
    style(ax, name + ": how big are daily moves?",
          "Number of days with each size of daily price change")
    ax.set_ylabel("Number of days", color=MUTED, fontsize=9)
    save(fig, coin + "_04_daily_return_hist.png")

    # 5. Rolling volatility
    rolling_vol = daily.rolling(30).std() * np.sqrt(DAYS_PER_YEAR)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(rolling_vol.index, rolling_vol, color=color, linewidth=1.6)
    ax.yaxis.set_major_formatter(PCT)
    style(ax, name + " volatility over time",
          "Based on the last 30 days of price moves, scaled to a yearly number")
    save(fig, coin + "_05_rolling_volatility.png")

    # 6. Drawdown
    drawdown = price / price.cummax() - 1
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.fill_between(drawdown.index, drawdown, 0, color=color, alpha=0.35, linewidth=0)
    ax.plot(drawdown.index, drawdown, color=color, linewidth=1.2)
    ax.yaxis.set_major_formatter(PCT)
    style(ax, name + ": how far below its peak?",
          "0% = at its highest price so far")
    save(fig, coin + "_06_drawdown.png")

    return {
        "months": [d.strftime("%Y-%m") for d in monthly_ret.index],
        "monthly_returns": [round(float(v), 6) for v in monthly_ret],
    }


# ---------- Charts comparing all coins ----------

def comparison_charts(prices, m5):
    # A. Risk vs return (the main chart)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for coin in COINS:
        x = m5.loc[coin, "annual_volatility"]
        y = m5.loc[coin, "annual_return"]
        ax.scatter(x, y, s=110, color=COLORS[coin], edgecolor="white", linewidth=2, zorder=3)
        ax.annotate(NAMES[coin], (x, y), xytext=(9, 4), textcoords="offset points",
                    fontsize=10, color=TEXT)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.xaxis.set_major_formatter(PCT)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("Risk: yearly volatility (higher = bumpier ride)", color=MUTED, fontsize=9)
    ax.set_ylabel("Yearly return", color=MUTED, fontsize=9)
    ax.set_xlim(left=0)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(0.04))
    style(ax, "More risk did not always mean more return", "Oct 2021 to Sep 2026")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    save(fig, "compare_risk_vs_return.png")

    # B. Growth of $100
    growth = prices / prices.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for coin in COINS:
        ax.plot(growth.index, growth[coin], color=COLORS[coin], linewidth=1.6, label=NAMES[coin])
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(mtick.LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(money))
    ax.yaxis.set_minor_formatter(mtick.NullFormatter())
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    style(ax, "What $100 invested on Oct 1, 2021 became", "Log scale; dashed line = $100 (break-even)")
    save(fig, "compare_growth_of_100.png")

    # C. Drawdown comparison
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for coin in COINS:
        dd = prices[coin] / prices[coin].cummax() - 1
        ax.plot(dd.index, dd, color=COLORS[coin], linewidth=1.3, label=NAMES[coin])
    ax.yaxis.set_major_formatter(PCT)
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    style(ax, "How far each coin fell below its peak", "0% = at its highest price so far")
    save(fig, "compare_drawdown.png")

    # D. Correlation of daily moves
    corr = correlation(prices)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(corr.values, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(COINS)))
    ax.set_yticks(range(len(COINS)))
    ax.set_xticklabels(COINS)
    ax.set_yticklabels(COINS)
    for i in range(len(COINS)):
        for j in range(len(COINS)):
            v = corr.values[i, j]
            ax.text(j, i, format(v, ".2f"), ha="center", va="center", fontsize=10,
                    color="white" if v > 0.6 else TEXT)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_title("Do they move together?", loc="left", fontsize=13, color=TEXT, pad=22)
    ax.text(0, 1.02, "Correlation of daily moves (1 = always together, 0 = unrelated)",
            transform=ax.transAxes, fontsize=9, color=MUTED)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save(fig, "compare_correlation.png")
    return corr


# ---------- Main ----------

def to_plain(table):
    out = {}
    for coin, row in table.iterrows():
        out[coin] = {k: (v if isinstance(v, str) else round(float(v), 6)) for k, v in row.items()}
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)

    prices, volumes = load_prices()
    start = prices.index[0].strftime("%Y-%m-%d")
    end = prices.index[-1].strftime("%Y-%m-%d")

    m5, rf5 = calc_metrics(prices, start, end)
    m1, rf1 = calc_metrics(prices, ONE_YEAR_START, end)
    m5.to_csv(os.path.join(OUT_DIR, "metrics_5y.csv"))
    m1.to_csv(os.path.join(OUT_DIR, "metrics_1y.csv"))

    monthly = {}
    for coin in COINS:
        monthly[coin] = coin_charts(coin, prices[coin], volumes[coin])
    corr = comparison_charts(prices, m5)

    site = {
        "period": {"start": start, "end": end, "one_year_start": ONE_YEAR_START,
                   "days": int(len(prices))},
        "risk_free": {"five_year": round(rf5, 6), "one_year": round(rf1, 6)},
        "five_year": to_plain(m5),
        "one_year": to_plain(m1),
        "correlation": {c: {d: round(float(corr.loc[c, d]), 3) for d in COINS} for c in COINS},
        "monthly": monthly,
        "colors": COLORS,
    }
    with open(SITE_DATA, "w") as f:
        json.dump(site, f, indent=1)

    show = ["total_return", "annual_return", "annual_volatility", "sharpe_ratio", "max_drawdown"]
    print("5 years:", start, "to", end, "| T-bill rate", round(rf5 * 100, 2), "%")
    print(m5[show].astype(float).round(3).to_string())
    print("\nLast 1 year:", ONE_YEAR_START, "to", end, "| T-bill rate", round(rf1 * 100, 2), "%")
    print(m1[show].astype(float).round(3).to_string())


if __name__ == "__main__":
    main()
