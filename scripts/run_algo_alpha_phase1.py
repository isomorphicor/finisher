#!/usr/bin/env python3
"""
Phase-1 exploration (scheme v3): load a date window, train HGBR, validation/test Sharpe vs equal-weight.

Usage (from repo root):
  PYTHONPATH=src python scripts/run_algo_alpha_phase1.py --date-start 2023-01-01 --date-end 2023-02-01

Paths and columns default to local A-share feathers; override with env INVERST_ALGO_ALPHA_*.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd

from algo_alpha.config import DataPaths, DateWindow, default_columns, default_paths
from algo_alpha.explore import run_phase1_gbdt
from algo_alpha.load import load_panel_filtered


def main() -> None:
    p = argparse.ArgumentParser(description="algo_alpha phase-1 GBDT smoke (scheme v3)")
    p.add_argument("--date-start", required=True, help="YYYY-MM-DD (inclusive)")
    p.add_argument("--date-end", required=True, help="YYYY-MM-DD (exclusive)")
    p.add_argument("--max-features", type=int, default=40, help="Use first N numeric feature columns after load (memory)")
    args = p.parse_args()

    d0 = date.fromisoformat(args.date_start)
    d1 = date.fromisoformat(args.date_end)
    paths = default_paths()
    cols = default_columns()
    window = DateWindow(start=d0, end=d1)

    df = load_panel_filtered(paths=paths, cols=cols, window=window, feature_cols=None)
    df[cols.date_col] = pd.to_datetime(df[cols.date_col])

    num_cols = []
    for c in df.columns:
        if c in (cols.date_col, cols.code_col, cols.label_col, cols.return_col):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            num_cols.append(c)
    num_cols = num_cols[: max(0, args.max_features)]
    if not num_cols:
        raise SystemExit("No numeric feature columns after panel merge.")

    for c in num_cols + [cols.label_col, cols.return_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[num_cols] = df[num_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    rep = run_phase1_gbdt(
        df,
        date_col=cols.date_col,
        code_col=cols.code_col,
        return_col=cols.return_col,
        label_col=cols.label_col,
        feature_cols=num_cols,
    )

    out = {
        "window": {"start": args.date_start, "end": args.date_end},
        "paths": {"feature": paths.feature_path, "label": paths.label_path},
        "columns": {
            "date": cols.date_col,
            "code": cols.code_col,
            "return": cols.return_col,
            "label": cols.label_col,
        },
        "n_rows": len(df),
        "n_features_used": len(num_cols),
        "result": rep,
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
