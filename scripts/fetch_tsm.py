#!/usr/bin/env python3
"""
Generate daily OHLC JSON files for TSM ADR static GitHub Pages site.
No third-party Python packages required.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RANGES = ["1mo", "3mo", "6mo", "1y"]
TICKER = "TSM"
BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range}&interval=1d&includePrePost=false&events=history"
OUT_DIR = Path(__file__).resolve().parents[1] / "data"


def fetch_range(range_name: str) -> dict:
    url = BASE_URL.format(ticker=TICKER, range=range_name)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (GitHub Actions; TSM ADR 3D FCN demo)",
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
            row = {
                "time": int(ts),
                "date": datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y/%m/%d"),
                "open": round(float(quote["open"][i]), 4),
                "high": round(float(quote["high"][i]), 4),
                "low": round(float(quote["low"][i]), 4),
                "close": round(float(quote["close"][i]), 4),
                "volume": int(quote["volume"][i] or 0),
            }
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        rows.append(row)

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
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append(f"{range_name}: {len(rows)} rows, latest close {rows[-1]['close']} on {rows[-1]['date']}")
        time.sleep(1)

    (OUT_DIR / "README.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("Generated TSM ADR data files:")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
