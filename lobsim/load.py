"""Load the committed trade extract and book summary."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from lobsim.measure import TradePrint

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SYMBOLS = ("btcusdt", "ethusdt")


def summary_path(symbol: str) -> Path:
    return DATA / f"{symbol}_book.json"


def trade_path(symbol: str) -> Path:
    return DATA / f"{symbol}_aggtrades.csv"


def load_summary(symbol: str) -> dict:
    return json.loads(summary_path(symbol).read_text())


def load_trades(symbol: str) -> list[TradePrint]:
    trades: list[TradePrint] = []
    with trade_path(symbol).open() as handle:
        for row in csv.DictReader(handle):
            trades.append(
                TradePrint(
                    time=int(row["time_us"]) / 1_000_000,
                    price=float(row["price"]),
                    qty=float(row["qty"]),
                    buyer_is_maker=row["buyer_is_maker"] == "1",
                )
            )
    return trades


def load_legacy(symbol: str) -> dict:
    return json.loads((DATA / "legacy" / f"{symbol}.json").read_text())
