#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RANGES = ["1mo", "3mo", "6mo", "1y"]
TICKER = "TSM"
OUT_DIR = Path(__file__).resolve().parents[1] / "data"

BASE_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    "{ticker}?range={range}&interval=1d&includePrePost=false&events=history"
)


def fetch_range(range_name: str) -> dict:
    url = BASE_URL.format(ticker=TICKER, range=range_name)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {range_name}")
        return json.loads(resp.read().decode("utf-8"))


def to_rows(payload: dict) -> list[dict]:
    result = (payload.get("chart", {}).get("result") or [None])[0]

    if not result:
        raise RuntimeError("Missing chart.result")

    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]

    rows = []

    for i, ts in enumerate(timestamps):
        try:
            open_price = quote["open"][i]
            high_price = quote["high"][i]
            low_price = quote["low"][i]
            close_price = quote["close"][i]
            volume = quote["volume"][i]

            if None in [open_price, high_price, low_price, close_price]:
                continue

            rows.append(
                {
                    "time": int(ts),
                    "date": datetime.fromtimestamp(
                        int(ts), timezone.utc
                    ).strftime("%Y/%m/%d"),
                    "open": round(float(open_price), 4),
                    "high": round(float(high_price), 4),
                    "low": round(float(low_price), 4),
                    "close": round(float(close_price), 4),
                    "volume": int(volume or 0),
                }
            )
        except (TypeError, ValueError, KeyError, IndexError):
            continue

    if len(rows) < 10:
        raise RuntimeError(f"Too few rows: {len(rows)}")

    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = []

    for range_name in RANGES:
        payload = fetch_range(range_name)
        rows = to_rows(payload)

        out = {
            "ticker": TICKER,
            "source": "Yahoo Finance chart API via GitHub Actions",
            "range": range_name,
            "interval": "1d",
            "updatedAt": updated_at,
            "latest": rows[-1],
            "rows": rows,
        }

        out_path = OUT_DIR / f"tsm-{range_name}.json"
        out_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary.append(
            f"{range_name}: {len(rows)} rows, "
            f"latest close {rows[-1]['close']} on {rows[-1]['date']}"
        )

        time.sleep(1)

    readme = OUT_DIR / "README.txt"
    readme.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print("Generated TSM ADR data files:")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
