import pandas as pd


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)

    # ensure datetime index
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        df["datetime"] = df["datetime"].dt.tz_convert("America/New_York")
        df = df.set_index("datetime")

    return df


def basic_info(df: pd.DataFrame):
    print("\n===== BASIC INFO =====")
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print("Index type:", type(df.index))
    print("Index dtype:", df.index.dtype)
    print("Start:", df.index.min())
    print("End:", df.index.max())


def check_duplicates(df: pd.DataFrame):
    print("\n===== DUPLICATES CHECK =====")
    dupes = df.index.duplicated().sum()
    print("Duplicate timestamps:", dupes)


def check_time_gaps(df: pd.DataFrame):
    print("\n===== TIME GAP CHECK =====")

    gaps = df.index.to_series().diff().dt.total_seconds() / 60
    print(gaps.value_counts().head(10))


def bars_per_day(df: pd.DataFrame):
    print("\n===== BARS PER DAY =====")

    daily = df.groupby(df.index.date).size()
    print(daily.describe())

    print("\nDays with unusually low bars:")
    print(daily[daily < 300].head(10))


def missing_data_check(df: pd.DataFrame):
    print("\n===== MISSING DATA CHECK =====")

    missing_ratio = df.isna().mean().sort_values(ascending=False)
    print(missing_ratio)


def session_check(df: pd.DataFrame):
    print("\n===== SESSION CHECK (RTH) =====")

    sample = df.between_time("09:30", "16:00")
    print("RTH rows:", len(sample))


def volume_sanity(df: pd.DataFrame):
    print("\n===== VOLUME SANITY =====")

    print(df["volume"].describe())

    zero_vol = (df["volume"] == 0).mean()
    print("Zero-volume ratio:", zero_vol)


def run_all(path: str):
    df = load_data(path)

    basic_info(df)
    check_duplicates(df)
    check_time_gaps(df)
    bars_per_day(df)
    missing_data_check(df)
    session_check(df)
    volume_sanity(df)


if __name__ == "__main__":
    run_all("QQQ_clean_backtest.parquet")