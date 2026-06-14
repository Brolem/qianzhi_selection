# Legacy 说明

本文档为 v1 旧版项目执行计划归档，保留原始内容用于追溯。当前主线已切换到 `docs/项目执行计划.md` 与根目录 `黔址优选_Codex多步执行指令.md`，方法口径为“区县背景约束下的网格级多因子商业选址推荐模型”。本文档中的 OSM/两阶段路线仅作为历史实现说明，不作为 v2 主线。

---

下面按 **“一次只让 Codex 完成一个闭环小任务”** 来安排。你不要把全部需求一次丢给 Codex，否则它很容易大改项目结构、引入不可控 bug。最佳方式是：**每一步都有明确输入、输出、验收命令和禁止事项**。

当前项目最终展示应围绕“两阶段选址推荐系统”推进：官方宏观经济和就业数据用于贵州整体市场背景，OSM/GIS 数据用于形成区域和 1km 网格差异，最后在 Streamlit 中展示区域粗筛、网格细筛、推荐解释和报告生成。这个路线与你现有技术路线一致。 赛题也明确要求结合公共数据、机器学习/大模型/GIS，构建商业选址智能决策辅助工具。

---

# 总体执行顺序

建议分成 9 个 Codex 任务包：

```text
0. 基线检查
1. 数据路径与配置统一
2. 官方数据读取与合理性报告
3. OSM 图层盘点与空间数据检查
4. 第一阶段：区域粗筛稳定化
5. 第二阶段：1km 网格细筛稳定化
6. 地图可视化
7. Streamlit 页面整合
8. 智能报告生成
9. 测试、README、演示材料收尾
```

每一步完成后都让 Codex 停下来，不要让它自动进入下一步。

---

# Step 0：项目基线检查

## 目标

确认当前项目能否运行，先不新增功能。

## 给 Codex 的指令

```text
你现在只做项目基线检查，不新增功能、不重构、不删除文件。

请完成以下任务：
1. 检查项目目录结构是否包含 data、src、outputs、docs、tests。
2. 检查 src/ 下所有 Python 文件是否能通过语法解析。
3. 检查关键数据文件是否存在：
   - data/raw/osm_guizhou/guizhou.gpkg
   - data/processed/osm_region/poi_features.csv
   - outputs/results/region_stage/region_stage_score_result.csv
   - outputs/results/grid_stage/grid_stage_score_result.csv
4. 运行已有测试，如果没有 tests，则创建最小测试目录，但不要写复杂测试。
5. 输出一份 docs/当前项目状态检查.md，说明：
   - 已存在文件
   - 缺失文件
   - 可运行命令
   - 当前最大风险

禁止事项：
- 不要重构业务逻辑。
- 不要修改评分权重。
- 不要改动 Streamlit 页面。
```

## 验收命令

```bash
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"
```

## 你要检查的产出

```text
docs/当前项目状态检查.md
```

---

# Step 1：统一配置文件和路径管理

## 目标

避免后面代码里到处写死路径。

## 给 Codex 的指令

```text
请只做“配置文件和路径管理”任务。

当前项目已有 config.yaml，请检查并完善它，使项目中主要路径都从 config.yaml 读取，包括：
1. 官方原始数据路径
2. OSM GPKG 路径
3. processed 数据输出路径
4. results 输出路径
5. figures 输出路径
6. reports 输出路径
7. 默认 top_n
8. 默认 grid_size_m
9. 便利店和轻餐饮两套权重

请新增或完善 src/config.py，实现：
- load_config()
- get_path(key)
- ensure_output_dirs()

要求：
- 不要改变现有业务结果。
- 如果原代码已有硬编码路径，优先改成从 config 读取。
- 所有路径用 pathlib.Path。
- 增加必要的异常提示，例如文件不存在时提示用户检查 data/raw。

完成后更新 README 中的“项目配置说明”。
```

## 预期产出

```text
config.yaml
src/config.py
README.md 中的配置说明
```

## 验收命令

```bash
python -c "from src.config import load_config, ensure_output_dirs; cfg=load_config(); ensure_output_dirs(cfg); print(cfg.keys())"
```

---

# Step 2：官方数据读取与合理性报告

## 目标

把官方宏观经济指标和就业数据整理成“背景说明”，不要强行用它制造网格差异。

你的现有方案已经明确：官方宏观和就业数据只作为贵州整体市场背景说明，不制造区域或网格之间的差异，也不解析就业地址文本。 这个边界要继续保持。

## 给 Codex 的指令

```text
请只做“官方数据读取与合理性报告”任务。

目标：
把 data/raw/ 中的官方宏观经济指标和就业数据读取、清洗、汇总，并生成报告。
注意：官方数据当前只作为贵州整体市场背景说明，不用于制造区县、街道或网格差异。

请完成：
1. 完善 src/data/preprocess.py 和 src/data/official_pipeline.py。
2. 自动识别 data/raw/ 下的 Excel/CSV 文件。
3. 读取宏观经济指标表，输出：
   - data/processed/macro_clean.csv
4. 读取就业数据表，输出：
   - data/processed/employment_clean.csv
5. 生成字段说明表：
   - outputs/results/字段说明表.csv
6. 生成数据识别与合理性报告：
   - outputs/results/数据识别与合理性报告.md

报告必须说明：
- 官方宏观经济指标可用于消费潜力、区域发展背景。
- 就业数据可用于就业客群、收入水平、稳定消费需求背景。
- 当前不从就业地址文本推断具体空间区域。
- 当前不把省级宏观数据强行拆分到 1km 网格。

禁止事项：
- 不要伪造区县数据。
- 不要随机生成官方数据。
- 不要把就业地址文本强行地理编码。
```

## 预期产出

```text
data/processed/macro_clean.csv
data/processed/employment_clean.csv
outputs/results/字段说明表.csv
outputs/results/数据识别与合理性报告.md
```

## 验收命令

```bash
python -m src.data.official_pipeline
```

---

# Step 3：OSM 图层盘点与空间数据检查

## 目标

确认 Geofabrik 贵州 OSM GPKG 中有哪些图层、哪些字段、哪些能用于选址。

OSMnx 可以下载和分析 OpenStreetMap 的路网、POI、建筑、公交站等空间要素；GeoPandas 的空间连接可用于把点、线、面要素聚合到区域或网格中。([OSMnx][1]) ([GeoPandas][2])

## 给 Codex 的指令

```text
请只做“OSM 图层盘点与空间数据检查”任务。

目标：
读取 data/raw/osm_guizhou/guizhou.gpkg，盘点所有图层，判断哪些图层可用于 POI、道路、土地利用、边界、地点。

请完成：
1. 新建或完善 src/osm/inventory.py。
2. 读取 guizhou.gpkg 的全部图层名称。
3. 对每个图层输出：
   - layer_name
   - geometry_type
   - row_count
   - crs
   - columns
   - sample_tags_or_fields
4. 输出文件：
   - outputs/results/osm_guizhou_layer_inventory.csv
   - outputs/results/osm_guizhou_layer_inventory.md
5. 报告中明确标记推荐使用图层：
   - POI 图层
   - road/transport 图层
   - landuse 图层
   - boundary/place 图层

禁止事项：
- 不要做评分。
- 不要生成网格。
- 不要修改 app.py。
```

## 预期产出

```text
src/osm/inventory.py
outputs/results/osm_guizhou_layer_inventory.csv
outputs/results/osm_guizhou_layer_inventory.md
```

## 验收命令

```bash
python -m src.osm.inventory
```

---

# Step 4：第一阶段区域粗筛

## 目标

稳定输出“优先考察区域”。这是最终 Demo 的第一层结果。

当前项目主线已经确定为：第一阶段用 OSM 边界评价区域做区域级粗筛，第二阶段在入选区域内生成 1km 网格。

## 给 Codex 的指令

```text
请只做“第一阶段：区域粗筛”任务。

目标：
基于 OSM 边界评价区域，聚合 POI、道路、土地利用特征，计算区域级评分结果。

请完成：
1. 完善 src/selection/two_stage.py 中的区域粗筛部分。
2. 输入：
   - data/raw/osm_guizhou/guizhou.gpkg
   - config.yaml 中的权重
3. 对每个 OSM 边界评价区域计算：
   - area_km2
   - poi_density
   - road_density
   - intersection_density
   - bus_stop_density
   - residential_landuse_ratio
   - commercial_landuse_ratio
   - retail_landuse_ratio
   - restaurant_density
   - convenience_density
   - supermarket_density
   - school_density
   - hospital_density
4. 构造五类指标：
   - traffic_accessibility
   - consumption_potential
   - synergy_score
   - competition_pressure
   - development_basis
5. 分别计算：
   - convenience_score
   - light_food_score
6. 输出：
   - data/processed/region_stage_scoring_input.csv
   - outputs/results/region_stage_score_result.csv
   - outputs/results/selected_regions_for_grid_stage.csv

要求：
- 所有密度类指标必须除以面积，避免大区域天然占优。
- competition_pressure 是负向指标。
- 输出中必须包含 main_advantage 和 main_risk。
- 不做门牌号推荐，只输出“优先考察区域”。

禁止事项：
- 不要把官方省级数据硬拆到各区域。
- 不要把 OSM 区域当作官方行政区划。
```

## 预期产出

```text
data/processed/region_stage_scoring_input.csv
outputs/results/region_stage_score_result.csv
outputs/results/selected_regions_for_grid_stage.csv
```

## 验收命令

```bash
python -m src.selection.two_stage --top-n 5
```

---

# Step 5：第二阶段 1km 网格细筛

## 目标

输出最终最重要的推荐结果：**1km 评价网格 Top N**。

这是最终项目展示的核心，不是区域粗筛。

## 给 Codex 的指令

```text
请只做“第二阶段：1km 网格细筛”任务。

目标：
在第一阶段选出的区域内生成 1km x 1km 评价网格，并从 OSM 原始几何重新聚合 POI、道路、土地利用特征，输出网格级推荐结果。

请完成：
1. 在 src/selection/two_stage.py 中完善网格细筛逻辑。
2. 支持参数：
   - --top-n
   - --region-id
   - --grid-size-m
3. 若用户传入 --region-id，则只对该区域生成网格。
4. 若未传入 --region-id，则对 selected_regions_for_grid_stage.csv 中的区域生成网格。
5. 每个网格输出：
   - grid_id
   - parent_region_id
   - centroid_lon
   - centroid_lat
   - area_km2
   - traffic_accessibility
   - consumption_potential
   - synergy_score
   - competition_pressure
   - development_basis
   - convenience_score
   - light_food_score
   - main_advantage
   - main_risk
6. 输出：
   - data/processed/grid_stage_poi_features.csv
   - data/processed/grid_stage_road_features.csv
   - data/processed/grid_stage_landuse_features.csv
   - data/processed/grid_stage_scoring_input.csv
   - outputs/results/grid_stage_score_result.csv
   - outputs/results/two_stage_site_selection_report.md

技术要求：
- 使用投影坐标系生成 1000m 网格，不能直接在经纬度上按度数生成 1km 网格。
- 使用 GeoPandas 的 spatial join 或 overlay 完成点、线、面与网格的聚合。
- 注意 CRS 一致性。

禁止事项：
- 不要复用区域级聚合表简单拆分网格。
- 不要生成门牌号推荐。
```

GeoPandas 文档说明，空间连接会根据几何之间的空间关系合并两个 GeoDataFrame，点落入面、多边形相交等场景都适用。([GeoPandas][2])

## 预期产出

```text
outputs/results/grid_stage_score_result.csv
outputs/results/two_stage_site_selection_report.md
```

## 验收命令

```bash
python -m src.selection.two_stage --top-n 5 --grid-size-m 1000
python -m src.selection.two_stage --region-id 8316193 --grid-size-m 1000
```

---

# Step 6：地图可视化

## 目标

把推荐结果从表格变成“看得见的选址地图”。

Folium 可以把 Python 处理后的数据可视化为 Leaflet 交互地图，适合在 Streamlit 中嵌入。([Python Visualization][3])

## 给 Codex 的指令

```text
请只做“地图可视化”任务。

目标：
基于区域粗筛和 1km 网格细筛结果，生成可在 Streamlit 展示的交互地图。

请完成：
1. 新建 src/visualization/map_viz.py。
2. 实现函数：
   - load_grid_result()
   - load_region_result()
   - build_grid_map(business_type)
   - build_region_map(business_type)
3. 地图至少包含：
   - 推荐网格中心点
   - 推荐网格边界或简化多边形
   - 不同颜色表示评分高低
   - tooltip 显示 grid_id、score、main_advantage、main_risk
4. 支持 business_type：
   - convenience
   - light_food
5. 输出静态 HTML：
   - outputs/figures/convenience_grid_map.html
   - outputs/figures/light_food_grid_map.html

如果当前没有网格几何，请从 grid_stage_score_result.csv 中的中心经纬度生成点地图，后续再增强为网格面地图。

禁止事项：
- 不要修改评分逻辑。
- 不要重新生成数据。
- 不要强行接入在线地图 API key。
```

## 预期产出

```text
src/visualization/map_viz.py
outputs/figures/convenience_grid_map.html
outputs/figures/light_food_grid_map.html
```

## 验收命令

```bash
python -m src.visualization.map_viz
```

---

# Step 7：Streamlit 页面整合

## 目标

形成最终能演示的 Web Demo。

Streamlit 官方文档说明，可通过 `streamlit run your_script.py` 运行应用，适合把 Python 脚本快速转成可交互的数据应用。([Streamlit Docs][4])

## 给 Codex 的指令

```text
请只做“Streamlit 页面整合”任务。

目标：
把已有数据、评分结果、地图和报告整合为一个可演示的 app.py。

请完善 src/app.py，页面结构如下：

1. 首页
   - 项目名称
   - 项目定位
   - 业务对象：社区便利店、轻餐饮
   - 推荐对象：区域 / 1km 网格
   - 技术路线：数据 → 指标 → 评分 → 推荐 → 解释 → 报告 → 演示

2. 数据概览
   - 官方宏观经济指标说明
   - 官方就业数据说明
   - OSM 图层盘点结果
   - 数据限制说明

3. 指标体系
   - 五类指标说明
   - 便利店和轻餐饮权重对比
   - 正向/负向指标说明

4. 区域粗筛
   - 读取 outputs/results/region_stage_score_result.csv
   - 展示便利店/轻餐饮区域推荐榜
   - 支持业态切换

5. 网格细筛
   - 读取 outputs/results/grid_stage_score_result.csv
   - 展示 1km 网格推荐榜
   - 支持业态切换
   - 展示网格中心经纬度、优势、风险

6. 地图展示
   - 嵌入 outputs/figures 下的地图 HTML
   - 如果没有 HTML，则展示提示并让用户先运行 python -m src.visualization.map_viz

7. 智能报告
   - 选择一个 grid_id
   - 展示报告生成结果
   - 支持导出 Markdown

8. 项目说明
   - 当前限制
   - 决赛数据接入计划
   - 后续扩展

禁止事项：
- 不要在页面中写“精准预测盈利”。
- 不要写“门牌号级推荐”。
- 不要写“官方数据已支持网格级就业分布”。
```

## 预期产出

```text
src/app.py
```

## 验收命令

```bash
streamlit run src/app.py
```

---

# Step 8：智能报告生成模块

## 目标

把评分结果转化成可读的选址报告，呼应赛题“大模型智能选址报告”的要求。

赛题明确提到可以构建基于大模型的智能选址报告，为商业主体生成候选点位列表、区域综合分析、竞争态势研判、市场空白点和过度竞争区域识别。

## 给 Codex 的指令

```text
请只做“智能报告生成模块”任务。

目标：
根据 grid_stage_score_result.csv 的结构化结果，生成 Markdown 格式选址报告。
当前阶段优先使用模板生成，不强制接入真实 LLM API。

请完善 src/reporting/report_generator.py，实现：
1. load_grid_results()
2. generate_site_report(grid_id, business_type)
3. export_report(grid_id, business_type, output_path)

报告结构：
一、候选网格基本信息
二、适配业态判断
三、交通可达性分析
四、消费潜力分析
五、共生业态分析
六、竞争压力分析
七、主要优势
八、主要风险
九、经营建议
十、数据来源与限制说明

要求：
- 所有结论必须来自输入字段。
- 不允许编造真实租金、真实客流、真实营收。
- 如果某类数据缺失，要写“当前未接入，后续可补充”。
- 输出 Markdown 到 outputs/reports/。

可选增强：
- 如果环境变量中存在 LLM_API_KEY，再调用大模型；
- 如果不存在，就使用规则模板生成报告。

禁止事项：
- 不要默认依赖外部 API。
- 不要把模板报告写成大模型已经真实调用。
```

## 预期产出

```text
src/reporting/report_generator.py
outputs/reports/*.md
```

## 验收命令

```bash
python -m src.reporting.report_generator
```

---

# Step 9：测试、README、演示材料收尾

## 目标

确保项目能复现，能演示，能交材料。

## 给 Codex 的指令

```text
请只做“测试、README、演示材料收尾”任务。

目标：
让项目具备可复现、可验收、可展示的最低质量。

请完成：
1. 完善 README.md，包含：
   - 项目简介
   - 数据来源
   - 环境安装
   - 一键运行流程
   - 输出文件说明
   - 当前限制
   - 后续扩展
2. 新增或完善 tests/：
   - test_config.py
   - test_data_outputs.py
   - test_scoring_outputs.py
3. 新增 docs/演示脚本.md，包含 5 分钟演示话术。
4. 新增 docs/CODEX最终交付清单.md。
5. 检查所有输出路径是否存在。
6. 检查 README 中的命令是否真实可运行。

README 中的一键运行流程建议为：
   python -m src.data.official_pipeline
   python -m src.osm.inventory
   python -m src.selection.two_stage --top-n 5 --grid-size-m 1000
   python -m src.visualization.map_viz
   python -m src.reporting.report_generator
   streamlit run src/app.py

禁止事项：
- 不要新增复杂依赖。
- 不要重构核心模型。
- 不要删除已有输出文件。
```

## 验收命令

```bash
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; print('syntax ok')"
```

---

# 每一步完成后你要让 Codex 回答什么

每次 Codex 完成一个步骤后，让它按这个格式回复：

```text
本步完成情况：
1. 修改了哪些文件：
2. 新增了哪些文件：
3. 生成了哪些输出：
4. 运行了哪些命令：
5. 命令结果：
6. 当前仍存在的问题：
7. 下一步建议：
```

这样你能清楚判断它有没有跑偏。

---

# 推荐执行节奏

| 轮次 | 任务           | 是否必须 |     预计耗时 |
| -- | ------------ | ---: | -------: |
| 0  | 基线检查         |   必须 | 20-30 分钟 |
| 1  | 配置和路径统一      |   必须 | 30-60 分钟 |
| 2  | 官方数据读取报告     |   必须 |   1-2 小时 |
| 3  | OSM 图层盘点     |   必须 |     1 小时 |
| 4  | 区域粗筛         |   必须 |   1-2 小时 |
| 5  | 1km 网格细筛     |   必须 |   2-3 小时 |
| 6  | 地图可视化        | 强烈建议 |   1-2 小时 |
| 7  | Streamlit 页面 |   必须 |   2-3 小时 |
| 8  | 报告生成         | 强烈建议 |   1-2 小时 |
| 9  | 测试和文档        |   必须 |   1-2 小时 |

---

# 最终验收标准

项目最后至少要能完成这条演示链路：

```text
运行数据处理
→ 运行两阶段评分
→ 打开 Streamlit
→ 查看官方数据说明
→ 查看区域粗筛榜
→ 查看 1km 网格细筛榜
→ 切换便利店/轻餐饮
→ 查看地图
→ 选择一个网格生成报告
```

对应命令：

```bash
python -m src.data.official_pipeline
python -m src.osm.inventory
python -m src.selection.two_stage --top-n 5 --grid-size-m 1000
python -m src.visualization.map_viz
python -m src.reporting.report_generator
streamlit run src/app.py
```

---

# 最重要的执行原则

你让 Codex 做代码时，始终坚持三条：

1. **先稳定输出，再美化页面。**
   没有 `grid_stage_score_result.csv`，地图和 Streamlit 都是空壳。

2. **先网格级推荐，不做门牌号推荐。**
   当前项目定位是“优先考察区域”和“1km 评价网格”，这与你现有实施说明一致。

3. **所有结论必须有数据来源。**
   官方数据说背景，OSM 数据说空间差异，模型结果说评分，报告只解释已有字段。不要让 Codex 编造客流、租金、营收。

[1]: https://osmnx.readthedocs.io/?utm_source=chatgpt.com "OSMnx 2.1.0 documentation"
[2]: https://geopandas.org/en/stable/gallery/spatial_joins.html?utm_source=chatgpt.com "Spatial Joins"
[3]: https://python-visualization.github.io/folium/?utm_source=chatgpt.com "Folium 0.20.0 documentation"
[4]: https://docs.streamlit.io/get-started/fundamentals/main-concepts?utm_source=chatgpt.com "Basic concepts of Streamlit"
