"""Data preprocessing and profiling utilities for Qianzhi Selection.

This module supports generic table loading and field profiling. It does not
map official field meanings, convert units, or merge official datasets until
the exact source files and data dictionary are available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.core.config import get_path


SUPPORTED_TABLE_SUFFIXES = {".csv", ".xlsx", ".xls"}


def read_table(path: str | Path) -> pd.DataFrame:
    """Read a CSV or Excel table from an exact path."""
    table_path = Path(path)
    if not table_path.exists():
        raise FileNotFoundError(f"数据文件不存在：{table_path}")
    if not table_path.is_file():
        raise ValueError(f"路径不是文件：{table_path}")

    suffix = table_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(table_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(table_path)
    raise ValueError(f"不支持的文件格式：{suffix}")


def list_data_files(directory: str | Path) -> list[Path]:
    """List supported data files in a directory, excluding placeholder files."""
    data_dir = Path(directory)
    if not data_dir.exists():
        raise FileNotFoundError(f"数据目录不存在：{data_dir}")
    if not data_dir.is_dir():
        raise ValueError(f"路径不是目录：{data_dir}")

    return sorted(
        path
        for path in data_dir.iterdir()
        if path.is_file() and path.name != ".gitkeep" and path.suffix.lower() in SUPPORTED_TABLE_SUFFIXES
    )


def ensure_raw_data_available(raw_dir: str | Path | None = None) -> list[Path]:
    """Return raw data files or stop with an explicit message."""
    source_dir = Path(raw_dir) if raw_dir is not None else get_path("official_raw_dir")
    files = list_data_files(source_dir)
    if not files:
        raise FileNotFoundError(f"未发现官方数据文件：请将宏观经济指标文件、就业数据文件和说明文件放入 {source_dir}")
    return files


def load_macro_data(path: str | Path) -> pd.DataFrame:
    """Load an official macro-economic indicator table from an exact path."""
    return read_table(path)


def load_employment_data(path: str | Path) -> pd.DataFrame:
    """Load an official employment table from an exact path."""
    return read_table(path)


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Return field profiling results for a dataframe."""
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def build_field_profile_table(source_file: str, df: pd.DataFrame) -> pd.DataFrame:
    """Build a row-per-field profile table without assigning field meanings."""
    profile_rows: list[dict[str, Any]] = []
    for field in df.columns:
        profile_rows.append(
            {
                "source_file": source_file,
                "raw_field": field,
                "field_meaning": "",
                "data_type": str(df[field].dtype),
                "unit": "",
                "usable_for_site_selection": "",
                "target_indicator": "",
                "notes": f"缺失值数量：{int(df[field].isna().sum())}",
            }
        )
    return pd.DataFrame(profile_rows)


def clean_macro_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply only source-agnostic cleanup that does not alter field meanings."""
    return df.drop_duplicates().copy()


def clean_employment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply only source-agnostic cleanup that does not alter field meanings."""
    return df.drop_duplicates().copy()


def build_region_features_with_shared_key(
    macro_df: pd.DataFrame,
    employment_df: pd.DataFrame,
    region_key: str | None = None,
) -> pd.DataFrame:
    """Build region-level base features only with a confirmed shared region key."""
    if region_key is None:
        raise ValueError("未确认共享区域键，不能合并宏观经济指标和就业数据。")
    if region_key not in macro_df.columns:
        raise KeyError(f"宏观经济指标数据缺少共享区域键：{region_key}")
    if region_key not in employment_df.columns:
        raise KeyError(f"就业数据缺少共享区域键：{region_key}")
    return macro_df.merge(employment_df, on=region_key, how="inner", validate="one_to_one")


def main() -> None:
    """Profile files under data/raw when official data exists."""
    raw_dir = get_path("official_raw_dir")
    files = list_data_files(raw_dir)
    if not files:
        print("未发现官方数据文件")
        print(f"请将宏观经济指标文件、就业数据文件和字段说明文件放入 {raw_dir}")
        return

    for path in files:
        df = read_table(path)
        profile = profile_dataframe(df)
        print(f"{path.name}: {profile['shape'][0]} 行，{profile['shape'][1]} 列，重复行 {profile['duplicate_rows']} 条")
        print("字段：")
        for field in profile["columns"]:
            print(f"- {field}")


if __name__ == "__main__":
    main()
