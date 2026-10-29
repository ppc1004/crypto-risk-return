# Step 1: Download daily price data
#
# Pulls daily prices for 5 cryptocurrencies from Yahoo Finance, plus the
# 3-month U.S. Treasury bill rate (used as the "risk-free" rate for the
# Sharpe ratio). Raw files go to data/raw/ (not uploaded to GitHub).
#
# Run from the project folder:  python src/download_data.py

import os
from datetime import datetime, timezone

import pandas as pd
import requests

# The 5 coins in this project (Yahoo Finance ticker -> short name)
COINS = {
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "USDT-USD": "USDT",
    "BNB-USD": "BNB",
    "XRP-USD": "XRP",
}
RISK_FREE_TICKER = "^IRX"   # 13-week U.S. Treasury bill yield, in %

# A fixed 5-year window, so anyone who re-runs this gets the same numbers
START = "2021-10-01"
END = "2026-09-30"          # last day included

RAW_DIR = os.path.join("data", "raw")


def to_unix(date_text):
    d = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(d.timestamp())


def download(ticker):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
    params = {
        "period1": to_unix(START),
        "period2": to_unix(END) + 2 * 86400,   # a little extra, trimmed below
        "interval": "1d",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]

    df = pd.DataFrame({
        "Date": pd.to_datetime(result["timestamp"], unit="s").normalize(),
        "Open": quote["open"],
        "High": quote["high"],
        "Low": quote["low"],
        "Close": quote["close"],
        "Volume": quote["volume"],
    })
    df = df.dropna(subset=["Close"]).drop_duplicates("Date", keep="last")
    df = df[(df["Date"] >= START) & (df["Date"] <= END)]
    return df


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    for ticker, name in COINS.items():
        df = download(ticker)
        df.to_csv(os.path.join(RAW_DIR, name + ".csv"), index=False)
        print(name, len(df), "days", df["Date"].min().date(), "to", df["Date"].max().date())

    rf = download(RISK_FREE_TICKER)
    rf.to_csv(os.path.join(RAW_DIR, "TBILL_3M.csv"), index=False)
    print("T-bill", len(rf), "days")


if __name__ == "__main__":
    main()
