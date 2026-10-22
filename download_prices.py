"""Download the Lab 15 monthly adjusted-price data from Yahoo Finance.

Run from this folder with:
    python download_prices.py

The output is prices.csv: Date first, oldest month first, then one column per
ticker.  It deliberately ends with September 2026, the last completed month
before the October 22, 2026 download date.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


TICKERS = ("BIL", "IEF", "LQD", "JOBY")
START = 1633046400  # 2021-10-01 UTC
END = 1790812800    # 2026-10-01 UTC; excludes the incomplete October bar


def monthly_adjusted_closes(ticker):
    """Return Yahoo Finance's monthly adjusted closes, keyed by bar date."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={START}&period2={END}&interval=1mo&events=history"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["adjclose"][0]["adjclose"]
    values = {}
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            raise ValueError(f"Yahoo Finance returned a missing adjusted close for {ticker}.")
        date = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        values[date] = close
    return values


def main():
    data = {ticker: monthly_adjusted_closes(ticker) for ticker in TICKERS}
    dates = sorted(set.intersection(*(set(values) for values in data.values())))
    if len(dates) < 37:
        raise ValueError("Fewer than 37 common monthly observations were downloaded.")
    output = Path("prices.csv")
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", *TICKERS])
        for date in dates:
            writer.writerow([date, *(f"{data[ticker][date]:.6f}" for ticker in TICKERS)])
    print(f"Wrote {output} with {len(dates)} monthly adjusted-price observations.")


if __name__ == "__main__":
    main()
