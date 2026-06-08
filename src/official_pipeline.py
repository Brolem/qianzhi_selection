"""Official data processing pipeline for the province-level model run."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .config import ensure_output_dirs, get_path
except ImportError:
    from config import ensure_output_dirs, get_path

try:
    from .data_process import build_field_profile_table, profile_dataframe, read_table
except ImportError:
    from data_process import build_field_profile_table, profile_dataframe, read_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = get_path("raw_official_data")
PROCESSED_DIR = get_path("processed_official")
METADATA_DIR = get_path("results_metadata")
REPORTS_DIR = get_path("reports")

MACRO_MAIN_FILE = RAW_DIR / "宏观经济经济运行-指标数据.xlsx"
MACRO_REFERENCE_FILE = RAW_DIR / "宏观经济_数据资源数据表.xlsx"
MACRO_CATALOG_FILE = RAW_DIR / "宏观经济库目录信息.xlsx"
EMPLOYMENT_TABLE_1_FILE = RAW_DIR / "就业表1.xlsx"
EMPLOYMENT_TABLE_2_FILE = RAW_DIR / "就业人员信息2.xlsx"
EMPLOYMENT_STRUCTURE_FILE = RAW_DIR / "就业数据结构.xlsx"

REGION_ID = 520000
REGION_NAME = "贵州省"

def ratio(numerator: float, denominator: float) -> float:
    """Calculate a bounded ratio with zero protection."""
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def build_field_dictionary(
    macro_main: pd.DataFrame,
    macro_reference: pd.DataFrame,
    macro_catalog: pd.DataFrame,
    employment_structure: pd.DataFrame,
) -> pd.DataFrame:
    """Build field dictionary from exact structure files and observed macro fields."""
    field_tables = [
        build_field_profile_table(MACRO_MAIN_FILE.name, macro_main),
        build_field_profile_table(MACRO_REFERENCE_FILE.name, macro_reference),
        build_field_profile_table(MACRO_CATALOG_FILE.name, macro_catalog),
    ]
    employment_fields = employment_structure.rename(
        columns={
            "表中文注释": "source_file",
            "字段名称": "raw_field",
            "字段中文注释": "field_meaning",
            "字段类型": "data_type",
        }
    )[["source_file", "raw_field", "field_meaning", "data_type"]].copy()
    employment_fields["unit"] = ""
    employment_fields["usable_for_site_selection"] = ""
    employment_fields["target_indicator"] = ""
    employment_fields["notes"] = ""
    field_tables.append(employment_fields)
    return pd.concat(field_tables, ignore_index=True)


def build_employment_features(table1: pd.DataFrame, table2: pd.DataFrame) -> dict[str, float]:
    """Aggregate employment tables without joining them by personal identifiers."""
    labour_force_count = int((table1["labour_force_flag"] == 1).sum())
    employed_count = int((table1["employed_flag"] == 1).sum())
    unemployed_count = int((table1["employed_flag"] == 2).sum())
    unit_employment_count = int((table1["employment_way"] == 1).sum())
    flexible_employment_count = int((table1["employment_way"] == 2).sum())
    startup_employment_count = int((table1["employment_way"] == 3).sum())
    farming_employment_count = int((table1["employment_way"] == 5).sum())

    table2_labour_count = int((table2["labour_is"] == 1).sum())
    urban_hard_count = int((table2["urban_hard_obt_empt_is"] == 1).sum())
    registered_unemployment_count = int((table2["djsy_is"] == 1).sum())
    high_salary_desire_count = int((table2["desire_salary"] == 4).sum())
    service_desire_count = int((table2["desire_category"] == 300).sum())

    table1_total = len(table1)
    table2_total = len(table2)
    employment_stability = ratio(unit_employment_count, employed_count)
    high_salary_desire_rate = ratio(high_salary_desire_count, table2_total)
    service_desire_rate = ratio(service_desire_count, table2_total)
    labour_is_rate = ratio(table2_labour_count, table2_total)
    employed_rate = ratio(employed_count, labour_force_count)
    unemployed_rate = ratio(unemployed_count, labour_force_count)
    urban_hard_rate = ratio(urban_hard_count, table2_total)
    registered_unemployment_rate = ratio(registered_unemployment_count, table2_total)

    return {
        "employment_table1_records": float(table1_total),
        "employment_table2_records": float(table2_total),
        "labour_force_count": float(labour_force_count),
        "employed_population": float(employed_count),
        "unemployed_count": float(unemployed_count),
        "employment_stability": employment_stability,
        "employed_rate": employed_rate,
        "unit_employment_count": float(unit_employment_count),
        "flexible_employment_count": float(flexible_employment_count),
        "startup_employment_count": float(startup_employment_count),
        "farming_employment_count": float(farming_employment_count),
        "labour_is_rate": labour_is_rate,
        "high_salary_desire_rate": high_salary_desire_rate,
        "service_desire_rate": service_desire_rate,
        "unemployed_rate": unemployed_rate,
        "urban_hard_obt_empt_rate": urban_hard_rate,
        "registered_unemployment_rate": registered_unemployment_rate,
    }


def write_identification_report(
    profiles: dict[str, dict[str, Any]],
    id_overlap: int,
    macro_area_codes: list[int],
    reference_area_codes: list[int],
) -> Path:
    """Write data identification and reasonableness report."""
    report_path = REPORTS_DIR / "数据识别与合理性报告.md"
    lines = [
        "# 数据识别与合理性报告",
        "",
        "## 1. 文件识别",
        "",
    ]
    for file_name, profile in profiles.items():
        lines.append(f"- `{file_name}`：{profile['shape'][0]} 行，{profile['shape'][1]} 列，重复行 {profile['duplicate_rows']} 条。")
    lines.extend(
        [
            "",
            "## 2. 合理性结论",
            "",
            f"- 宏观经济主表区域编码唯一值：{macro_area_codes}。",
            f"- 宏观经济对照表区域编码唯一值：{reference_area_codes}。",
            f"- `就业表1.idcard_number` 与 `就业人员信息2.id_card` 交集数量：{id_overlap}。",
            "- 官方宏观经济指标可用于消费潜力和区域发展背景说明。",
            "- 就业数据可用于就业客群、收入水平和稳定消费需求背景说明。",
            "- 就业数据未提供已确认区域编码，因此不做地址拆分或区域推断。",
            "- 官方宏观和就业数据只作为贵州整体市场背景，不能制造区域或网格差异。",
            "- 当前不把省级宏观数据强行拆分到 1km 网格。",
            "- 当前推荐主线采用两阶段空间选址：区域粗筛和 1km 评价网格细筛。",
            "",
            "## 3. 处理限制",
            "",
            "- 不合并两张就业人员明细表。",
            "- 不解析就业地点文本。",
            "- 不从官方就业数据生成空间区域字段。",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_official_pipeline() -> dict[str, Path]:
    """Run official province-level processing and scoring."""
    ensure_output_dirs()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    macro_main = read_table(MACRO_MAIN_FILE)
    macro_reference = read_table(MACRO_REFERENCE_FILE)
    macro_catalog = read_table(MACRO_CATALOG_FILE)
    employment_table1 = read_table(EMPLOYMENT_TABLE_1_FILE)
    employment_table2 = read_table(EMPLOYMENT_TABLE_2_FILE)
    employment_structure = read_table(EMPLOYMENT_STRUCTURE_FILE)

    profiles = {
        MACRO_MAIN_FILE.name: profile_dataframe(macro_main),
        MACRO_REFERENCE_FILE.name: profile_dataframe(macro_reference),
        MACRO_CATALOG_FILE.name: profile_dataframe(macro_catalog),
        EMPLOYMENT_TABLE_1_FILE.name: profile_dataframe(employment_table1),
        EMPLOYMENT_TABLE_2_FILE.name: profile_dataframe(employment_table2),
        EMPLOYMENT_STRUCTURE_FILE.name: profile_dataframe(employment_structure),
    }

    macro_clean = macro_main.drop_duplicates().copy()
    macro_clean["value"] = pd.to_numeric(macro_clean["value"], errors="coerce")
    macro_clean_path = PROCESSED_DIR / "macro_clean.csv"
    macro_clean.to_csv(macro_clean_path, index=False, encoding="utf-8-sig")

    employment_features = build_employment_features(employment_table1, employment_table2)
    employment_clean = pd.DataFrame([{**{"region_id": REGION_ID, "region_name": REGION_NAME}, **employment_features}])
    employment_clean_path = PROCESSED_DIR / "employment_clean.csv"
    employment_clean.to_csv(employment_clean_path, index=False, encoding="utf-8-sig")

    field_dictionary = build_field_dictionary(macro_main, macro_reference, macro_catalog, employment_structure)
    field_dictionary_path = METADATA_DIR / "字段说明表.csv"
    field_dictionary.to_csv(field_dictionary_path, index=False, encoding="utf-8-sig")

    id_overlap = len(
        set(employment_table1["idcard_number"].dropna().astype(str)).intersection(
            set(employment_table2["id_card"].dropna().astype(str))
        )
    )
    report_path = write_identification_report(
        profiles=profiles,
        id_overlap=id_overlap,
        macro_area_codes=sorted(macro_main["area_code"].dropna().astype(int).unique().tolist()),
        reference_area_codes=sorted(macro_reference["area_id"].dropna().astype(int).unique().tolist()),
    )

    print("官方数据背景处理流程完成")
    for path in [
        report_path,
        field_dictionary_path,
        macro_clean_path,
        employment_clean_path,
    ]:
        print(path)

    return {
        "report": report_path,
        "field_dictionary": field_dictionary_path,
        "macro_clean": macro_clean_path,
        "employment_clean": employment_clean_path,
    }


if __name__ == "__main__":
    run_official_pipeline()
