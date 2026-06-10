# 黔址优选：贵阳市典型区县社区商业智能选址原型

## 1. 项目定位

本项目面向贵州人工智能创业大赛公共数据赛道，聚焦社区便利店与轻餐饮两类业态。v2 主线定位为：

> 以贵阳市典型区县为试点，将官方宏观经济指标和就业数据作为区域市场背景，将高德 POI 与地理空间数据作为网格级特征来源，构建“区县背景约束下的网格级多因子商业选址推荐模型”。

系统输出适合实地调研和经营研判的 1km 评价网格，提供地图洞察、指标解释和 Markdown 选址报告。当前版本不做门牌号级推荐，不承诺具体盈利，不生成真实租金、真实客流或真实营收预测。

## 2. 当前状态

当前仓库已存在 v1 可运行基础：

- 官方数据清洗与合理性报告。
- OSM/GIS 空间特征处理。
- 旧版区域与网格评分结果。
- Streamlit 页面入口。
- 地图 HTML 与 Markdown 报告生成能力。

v2 迁移目标是把主数据源和方法口径调整为：

- 官方宏观经济指标和就业数据：用于贵州、贵阳和目标区县市场背景说明。
- 高德行政区划 API：用于目标区县基础信息和边界信息。
- 高德 POI API：用于网格级商业、交通、生活配套、竞品和共生业态统计。
- 离线演示数据：用于无 `AMAP_KEY` 时保持演示链路可运行。
- 1km 评价网格：作为核心评分对象。

高德 API 客户端、区县边界构建、网格 POI 查询、v2 指标工程、v2 评分结果和新版工作台页面均属于 v2 待实施内容。

## 3. 目标区县与业务对象

第一版目标区县：

- 云岩区
- 南明区
- 观山湖区

增强版可扩展：

- 花溪区
- 白云区

业务对象：

- 社区便利店
- 轻餐饮

推荐对象：

- 1km 评价网格

## 4. 文档结构

当前主线文档：

```text
黔址优选_Codex多步执行指令.md
docs/文档索引.md
docs/方法调整说明.md
docs/初赛方案_新版.md
docs/技术路线草图.md
docs/项目执行计划.md
docs/推荐项目方案.md
```

旧版文档已归档到：

```text
docs/legacy/
```

旧版文档仅用于追溯 OSM/GIS 实现和历史演示方案，不作为 v2 主线口径。

## 5. 当前代码结构

```text
qianzhi_selection/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   └── legacy/
├── outputs/
│   ├── figures/
│   ├── reports/
│   └── results/
├── src/
│   ├── data/
│   ├── osm/
│   ├── reporting/
│   ├── selection/
│   ├── visualization/
│   ├── app.py
│   └── config.py
├── tests/
├── config.yaml
├── README.md
└── 黔址优选_Codex多步执行指令.md
```

当前代码仍保留 v1 模块。v2 实施时应保留旧模块作为 legacy 参考，不直接删除。

## 6. 当前已有输出

官方背景处理：

```text
data/processed/official/macro_clean.csv
data/processed/official/employment_clean.csv
outputs/results/metadata/字段说明表.csv
outputs/reports/数据识别与合理性报告.md
```

旧版空间处理与评分结果：

```text
data/processed/osm_region/poi_features.csv
data/processed/osm_region/road_features.csv
data/processed/osm_region/landuse_features.csv
data/processed/site_selection/region_stage_scoring_input.csv
data/processed/site_selection/grid_stage_scoring_input.csv
outputs/results/region_stage/region_stage_score_result.csv
outputs/results/grid_stage/grid_stage_score_result.csv
outputs/figures/convenience_grid_map.html
outputs/figures/light_food_grid_map.html
```

这些输出代表 v1 已有能力，不等同于 v2 高德 POI 链路结果。

## 7. 当前运行方式

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

运行旧版数据与演示入口：

```bash
python -m src.data.official_pipeline
python -m src.osm.inventory
python -m src.osm.pipeline --no-download
python -m src.selection.two_stage --top-n 5 --grid-size-m 1000
python -m src.visualization.map_viz
python -m src.reporting.report_generator --template
streamlit run src/app.py
```

v2 一键流程将在后续实施 `docs/项目执行计划.md` 后补齐。

## 8. 验证方法

```bash
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; print('syntax ok')"
```

文档检查：

```bash
rg -n "^#{1,6} " README.md "黔址优选_Codex多步执行指令.md" docs -g "*.md"
rg -n "OSM|Geofabrik|两阶段|区域粗筛|网格细筛" README.md docs -g "*.md"
rg -n "全量高德|精准盈利|真实租金|真实客流|门牌号级" README.md docs -g "*.md"
```

## 9. 当前限制

- v2 高德 API 客户端尚未实施。
- v2 区县边界、网格 POI 统计、指标工程和评分结果尚未实施。
- 当前页面仍基于 v1 输出展示，尚未改造成完整商业选址工作台。
- 当前未接入工商主体、信用、租赁、实时客流、停车条件和门店经营流水数据。
- 官方宏观经济与就业数据只用于背景说明，不硬拆到 1km 评价网格。
