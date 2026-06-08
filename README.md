# 黔址优选：两阶段社区商业智能选址推荐系统

## 1. 项目定位

本项目面向贵州人工智能创业大赛公共数据赛道，聚焦社区便利店与轻餐饮两类业态，构建“官方数据背景处理 + OSM/GIS 空间处理 + 两阶段选址推荐 + Streamlit 展示 + 报告生成”的可运行原型。

推荐结果定位为：

- 第一阶段：优先考察区域。
- 第二阶段：入选区域内 1km 评价网格。

项目不做门牌号级推荐，不承诺具体盈利。

## 2. 目录结构

```text
qianzhi_selection/
├── data/
│   ├── raw/
│   │   ├── official/          # 六个官方 Excel
│   │   └── osm_guizhou/       # guizhou.gpkg 与来源 README
│   └── processed/
│       ├── official/          # 官方清洗与背景数据
│       ├── osm_region/        # OSM 边界区域级空间特征
│       └── site_selection/    # 两阶段选址模型输入
├── outputs/
│   ├── results/
│   │   ├── region_stage/      # 区域粗筛结果
│   │   ├── grid_stage/        # 1km 网格细筛结果
│   │   └── metadata/          # 字段说明、指标体系、权重、图层盘点
│   ├── reports/               # Markdown/Word 报告
│   └── figures/               # 地图 HTML、截图、图表
├── src/
├── tests/
└── docs/
```

## 3. 数据基础

官方 Excel 位于：

```text
data/raw/official/
```

OSM 原始空间数据位于：

```text
data/raw/osm_guizhou/guizhou.gpkg
```

官方数据用于贵州整体市场背景说明；OSM 数据用于区域和 1km 评价网格之间的空间差异计算。

## 4. 项目配置说明

项目路径、默认参数和业态权重统一写在 `config.yaml` 中，代码通过 `src/config.py` 读取。

当前规范路径：

```text
paths.raw_official_data        data/raw/official
paths.raw_osm_data             data/raw/osm_guizhou
paths.processed_official       data/processed/official
paths.processed_osm_region     data/processed/osm_region
paths.processed_site_selection data/processed/site_selection
paths.results_region_stage     outputs/results/region_stage
paths.results_grid_stage       outputs/results/grid_stage
paths.results_metadata         outputs/results/metadata
paths.figures                  outputs/figures
paths.reports                  outputs/reports
```

默认模型参数：

```text
model_defaults.top_n       5
model_defaults.grid_size_m 1000
```

便利店和轻餐饮两套权重位于 `weights.convenience_store` 和 `weights.light_catering`。后续调整权重时优先修改 `config.yaml`，不要在业务脚本中写死新权重。

## 5. 主要输出

官方背景处理：

```text
data/processed/official/macro_clean.csv
data/processed/official/employment_clean.csv
outputs/results/metadata/字段说明表.csv
outputs/reports/数据识别与合理性报告.md
```

OSM 区域空间特征：

```text
data/processed/osm_region/poi_features.csv
data/processed/osm_region/road_features.csv
data/processed/osm_region/landuse_features.csv
data/processed/osm_region/osm_boundaries.csv
data/processed/osm_region/osm_places.csv
outputs/results/metadata/osm_guizhou_layer_inventory.csv
outputs/results/metadata/osm_guizhou_layer_inventory.md
outputs/reports/osm_guizhou_processing_report.md
```

两阶段选址结果：

```text
data/processed/site_selection/region_stage_scoring_input.csv
data/processed/site_selection/grid_stage_scoring_input.csv
outputs/results/region_stage/region_stage_score_result.csv
outputs/results/region_stage/selected_regions_for_grid_stage.csv
outputs/results/grid_stage/grid_stage_score_result.csv
outputs/reports/two_stage_site_selection_report.md
```

## 6. 环境配置

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如 PowerShell 禁止激活虚拟环境：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 7. 程序执行方法

官方数据背景处理：

```bash
python src/official_pipeline.py
```

OSM 图层盘点与空间数据检查：

```bash
python src/osm_inventory.py
```

OSM 空间数据处理：

```bash
python src/osm_guizhou_pipeline.py --no-download
```

两阶段选址推荐：

```bash
python src/two_stage_site_selection.py --top-n 5 --grid-size-m 1000
```

生成一份网格报告：

```bash
python src/report_generator.py
```

启动页面：

```bash
streamlit run src/app.py
```

## 8. 验证方法

```bash
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"
```

检查关键输出：

```powershell
Test-Path data\raw\official\就业表1.xlsx
Test-Path data\raw\osm_guizhou\guizhou.gpkg
Test-Path outputs\results\region_stage\region_stage_score_result.csv
Test-Path outputs\results\grid_stage\grid_stage_score_result.csv
```

## 9. 当前限制

- 官方数据不提供可确认的细粒度空间区域字段。
- 就业地址文本不用于空间推断。
- OSM 标识不等同于官方行政区划代码。
- 当前未接入真实租金、实时客流、停车条件和工商信用数据。
