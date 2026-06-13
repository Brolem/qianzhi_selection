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

v2 已完成的基础数据链路包括：

- 官方宏观经济指标和就业数据：用于贵州、贵阳和目标区县市场背景说明。
- 高德 Web 服务客户端与本地请求缓存。
- 云岩区、南明区、观山湖区的区县基础信息和真实 API 边界。
- 790 个 1km 空间评价网格。
- 三区各 20 个、共 60 个样本网格的关键词 POI 统计。
- 基于统一口径 POI 计数的网格级指标工程输入。
- 社区便利店与轻餐饮的默认差异化评分、全局/区县排名和推荐等级。
- 基于六维权重与两类指标模板的自定义评分方案命令行入口。
- 基于 790 个空间网格的便利店与轻餐饮评分地图，以及自定义评分方案动态地图。
- 基于 Step 8 正式结果的 DeepSeek 智能选址报告，支持默认与自定义评分方案。
- 基于 `st.Page` 和 `st.navigation` 的七页 Streamlit 工作台，并保留旧版本 sidebar radio 回退。
- 基于共享 UI 模块和 `.streamlit/config.toml` 的紧凑运营台视觉系统。
- 首页五类 POI 主题摘要、活跃网格区县平均得分对比图和区域 POI 原始数量对比图。
- 网格推荐页的六项权重预算、即时评分、正式方案保存和单网格六维分解。

当前工作台包含项目总览、数据底座、区域对比、网格推荐、地图洞察、智能报告和项目说明。原“选址分析”与“网格推荐”职责重复，Step 13 已调整为决策流程整合并入 Step 15，不再保留独立页面。Step 14 已补充区县背景图表，Step 15 已统一承载默认方案、已保存自定义方案、新建方案、即时评分和推荐结果。Step 17 智能报告页已完成正式验收；Step 16 地图页已具备核心能力，尚待补充区县筛选。

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
│   ├── pages/
│   ├── app.py
│   ├── app_legacy.py
│   ├── config.py
│   ├── profile_catalog.py
│   └── scoring_model.py
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

运行 legacy 数据链路：

```bash
python -m src.data.official_pipeline
python -m src.osm.inventory
python -m src.osm.pipeline --no-download
python -m src.selection.two_stage --top-n 5 --grid-size-m 1000
python -m src.visualization.map_viz
```

v2 一键流程将在后续实施 `docs/项目执行计划.md` 后补齐。

运行 v2 默认评分：

```powershell
python src/scoring_model.py
```

运行一个自定义六维权重方案：

```powershell
python src/scoring_model.py `
  --profile-id custom_retail_01 `
  --profile-name "自定义社区业态" `
  --template community_retail `
  --traffic-weight 0.20 `
  --consumption-weight 0.25 `
  --employment-weight 0.10 `
  --synergy-weight 0.20 `
  --competition-weight 0.15 `
  --atmosphere-weight 0.10
```

生成两张默认评分地图：

```powershell
python -m src.visualization.map_viz
```

配置 DeepSeek 当前用户环境变量后生成便利店 Top 1 智能报告：

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
python -m src.reporting.report_generator `
  --profile convenience `
  --grid-id grid_520103_000078
```

使用规则模板、不调用 API：

```powershell
python -m src.reporting.report_generator `
  --profile convenience `
  --grid-id grid_520103_000078 `
  --template
```

`--profile` 支持 `convenience`、`light_food` 和 `outputs/results/custom_profiles/` 下具有有效 `profile_metadata.json` 的方案标识。报告默认写入 `outputs/reports/<profile_id>/`。

启动七页 Streamlit 工作台：

```powershell
streamlit run src/app.py
```

“网格推荐”“地图洞察”和“智能报告”分别使用页面内评分方案选择器，支持默认便利店、默认轻餐饮和有效自定义方案。网格推荐页可直接设置六项百分比权重，非零且合计不为 100.00% 的输入可归一后即时预览；正式保存要求合计精确为 100.00%。旧入口实现保留在 `src/app_legacy.py`，不作为 v2 默认启动入口。

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

- v2 当前已完成区县边界、空间网格、60 网格 POI 样本、指标工程、Step 8 网格评分、Step 9 地图生成、Step 10 DeepSeek 智能报告、Step 11 多页工作台架构、Step 12 统一视觉系统、Step 13–15 页面去重与交互增强及 Step 17 智能报告页面验收。
- 60 网格 POI 统计采用统一关键词口径，适合相对比较，不代表完整 POI 总量。
- 19 个全零样本网格保留用于审计，评分结果将其得分固定为 0 且不进入排名。
- 自定义权重只改变现有六维指标贡献；新增正式业态仍需补充对应 POI 和指标模板。
- 七个工作台页面均已切换到 v2 口径并采用统一视觉样式；Step 17 已支持方案选择、活跃网格筛选、按钮触发、会话缓存、模型状态、模板兜底、Markdown 预览与下载。Step 16 后续只需补充区县筛选。
- 高德 JS API 2.0 是地图主链，直接使用 GCJ-02 边界、网格和中心点；Folium 仅作为无 JS 凭据或用户主动选择时的兼容回退，并在回退路径临时转换为 WGS84。
- 高德 Web 服务继续读取 `AMAP_KEY`；地图页面另行读取用户级 `AMAP_JS_KEY` 与 `AMAP_JS_SECURITY_CODE`。三项凭据均不得写入仓库文件。
- 当前未接入工商主体、信用、租赁、实时客流、停车条件和门店经营流水数据。
- 官方宏观经济与就业数据只用于背景说明，不硬拆到 1km 评价网格。
- 官方数据当前真实地域范围为贵州省级，只用于报告中的市场背景和适用边界，不参与网格评分，也不用于制造区县差异。
