import pandas as pd


# =========================
# MAIN CLEANING PIPELINE
# =========================

def build_backtest_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts raw intraday data into clean backtesting-ready dataset:
    - timezone-safe datetime handling
    - de-duplication
    - numeric enforcement
    - RTH filtering (09:30–16:00 ET)
    - 1-minute continuity grid
    """
AS  
    df = df.copy()

    # --------------------------------------------------
    # 1. Ensure datetime is parsed correctly
    # --------------------------------------------------
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["datetime"] = df["datetime"].dt.tz_convert("America/New_York")
    df = df.sort_values("datetime")

    # --------------------------------------------------
    # 2. Remove duplicate timestamps (critical fix)
    # --------------------------------------------------
    df = df.drop_duplicates(subset=["datetime"], keep="last")

    # --------------------------------------------------
    # 3. Set datetime index for time-series operations
    # --------------------------------------------------
    df = df.set_index("datetime")

    # --------------------------------------------------
    # 4. Ensure numeric types (prevents silent bugs)
    # --------------------------------------------------
    cols = ["volume", "vw", "open", "high", "low", "close", "n"]
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # --------------------------------------------------
    # 5. Filter Regular Trading Hours (RTH only)
    # --------------------------------------------------
    df = df.between_time("09:30", "16:00")

    # --------------------------------------------------
    # 6. Enforce 1-minute continuity grid per day
    # --------------------------------------------------
    df = _enforce_daily_grid(df)

    return df


# =========================
# INTERNAL HELPER
# =========================

def _enforce_daily_grid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rebuilds a strict 1-minute RTH index per trading day.
    Missing bars become NaN (important for realistic backtests).
    """

    output = []

    for date, day in df.groupby(df.index.date):

        day = day.sort_index()

        # Construct full RTH index
        start = pd.Timestamp(f"{date} 09:30", tz=day.index.tz)
        end = pd.Timestamp(f"{date} 16:00", tz=day.index.tz)

        full_index = pd.date_range(
            start=start,
            end=end,
            freq="1min"
        )

        # Reindex to enforce continuity
        day = day.reindex(full_index)

        output.append(day)

    return pd.concat(output)


# =========================
# OPTIONAL VALIDATION TOOL
# =========================

def dataset_report(df: pd.DataFrame):
    """
    Quick sanity checks for backtesting readiness.
    """

    print("\n===== DATASET REPORT =====")

    # bars per day
    daily_counts = df.groupby(df.index.date).size()
    print("Avg bars/day:", daily_counts.mean())
    print("Min bars/day:", daily_counts.min())
    print("Max bars/day:", daily_counts.max())

    # missing data ratio
    missing = df["close"].isna().mean()
    print("Missing bar ratio:", round(missing, 4))

    # time range
    print("Start:", df.index.min())
    print("End:", df.index.max())


# =========================
# USAGE EXAMPLE
# =========================
if __name__ == "__main__":

    # Example: load raw data
    df = pd.read_csv("QQQ_1min_2025_01_01_to_2026_06_23.csv")

    # Clean dataset
    clean_df = build_backtest_dataset(df)

    # Report
    dataset_report(clean_df)

    # Save
    clean_df.to_parquet("QQQ_clean_backtest.parquet")

    print("\nSaved clean dataset.")