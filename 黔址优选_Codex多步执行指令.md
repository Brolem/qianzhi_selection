# 黔址优选：项目方法调整与前端改造 Codex 多步执行指令

> 版本：v2.0  
> 目标：将项目从旧版“Geofabrik/OSM 两阶段选址推荐”调整为“区县背景约束下的网格级多因子商业选址推荐模型”，并将前端改造成类似百度地图慧眼的商业选址工作台。  
> 当前推荐技术栈：Python + Streamlit + 高德 Web 服务 API + 高德 JS API 2.0 + Folium 兼容回退 + Markdown 报告生成。
> 当前状态：Step 0 到 Step 18 已完成；本文同时保留历史执行顺序和当前 v2 真实入口，2026 年 6 月 15 日按仓库现状复核。

---

## 执行总原则

本文件约束项目目标、方法边界和 Step 0 到 Step 18 的执行顺序，但其中的示例路径、字段、命令和实现细节必须经过当前仓库真实状态验证后使用。

项目执行依据按以下原则处理：

1. 总控文档规定项目目标、方法边界和阶段顺序。
2. 真实文件、字段、配置、接口响应、测试结果和运行环境决定具体实现。
3. 总控示例与真实仓库状态冲突时，不得机械执行，也不得猜测标识符或数据结构。
4. 调整实现时必须记录冲突内容、实际依据、实现选择和验证结果。
5. 未经实际验证的能力不得写成已完成，不以形式上的命令通过替代真实数据验收。

---

## 0. 方法总口径

后续项目文档、README、前端页面、答辩材料统一使用以下口径：

> 本项目以贵阳市典型区县为试点，将官方宏观经济指标和就业数据作为贵州省级市场背景，将高德 POI 与地理空间数据作为网格级特征来源，构建“区县背景约束下的网格级多因子商业选址推荐模型”。系统不进行门牌号级推荐，而是输出适合社区便利店和轻餐饮业态的优先考察网格，并提供地图洞察、指标解释和智能选址报告。

---

## 1. 当前方法调整结论

### 1.1 不再把 Geofabrik/OSM 作为主数据源

原因：

1. 中国境内 OSM/Geofabrik 的 POI 完整度、商业门店覆盖、分类准确度通常不如高德、百度、腾讯等国内 LBS 平台。
2. 本项目做的是社区便利店和轻餐饮选址，真正关键的数据是餐饮、便利店、学校、医院、商场、写字楼、小区、公交站等 POI。
3. OSM 可保留为 legacy 或备用数据源，但新主线应改为国内位置服务 API。

### 1.2 不再强调“区县粗筛 → 网格细筛”的两阶段筛选

当前只做贵阳市 3–5 个区县，区县数量较少，区县粗筛意义有限。

新的方法是：

```text
区县层：限定范围、展示背景、做分组汇总
网格层：真正评分、推荐、解释、报告生成
```

建议模型名称：

> 区县背景约束下的网格级多因子商业选址推荐模型

### 1.3 推荐粒度

当前版本推荐对象：

```text
1km 评价网格
```

不做：

```text
真实门牌号推荐
精准盈利预测
真实租金预测
真实客流预测
```

### 1.4 目标区县

第一版必须支持：

1. 云岩区
2. 南明区
3. 观山湖区

增强版可扩展：

4. 花溪区
5. 白云区

### 1.5 数据来源

| 数据类型 | 来源 | 用途 |
|---|---|---|
| 官方宏观经济指标 | 赛事官方数据 | 贵州省级市场背景、消费与区域发展说明 |
| 官方就业数据 | 赛事官方数据 | 贵州省级就业背景与数据适用边界说明 |
| POI 数据 | 高德 POI API，百度/腾讯作为备选 | 网格级商业、交通、生活配套、竞品、共生业态统计 |
| 行政区划 | 高德行政区划 API | 区县信息、区县边界、区县中心点 |
| 地图展示 | 高德 JS API 2.0 / Streamlit components / Folium 兼容回退 | GCJ-02 推荐网格地图、热力图、点位提示 |
| 离线复现输入 | `data/processed/` 中已跟踪的区县、边界、网格和 POI 样本 | 无 `AMAP_KEY` 时由 Step 18 默认流程复现指标、评分、地图和模板报告 |

---

## 2. Codex 总控说明

在开始具体任务前，先把下面这段发给 Codex：

```text
项目方法调整总控说明：

当前项目“黔址优选”需要从旧版“Geofabrik/OSM 两阶段选址推荐”调整为“区县背景约束下的网格级多因子商业选址推荐模型”，并将前端从普通数据报表改造成类似百度地图慧眼的商业选址工作台。

新的项目定位：
1. 研究范围：贵阳市典型区县，第一版包括云岩区、南明区、观山湖区；增强版可加入花溪区、白云区。
2. 业务对象：社区便利店、轻餐饮。
3. 推荐对象：1km 评价网格，不做真实门牌号级推荐。
4. 数据来源：
   - 官方宏观经济指标和就业数据：用于贵州省级市场、消费与就业背景说明，不下钻到贵阳、区县或网格；
   - 高德 POI API：用于网格级 POI 样本统计；
   - 高德行政区划 API：用于区县信息和边界；
   - 离线复现输入：无 AMAP_KEY 时使用仓库已跟踪的 data/processed/ 区县、边界、网格和 POI 样本，不重新调用高德。
5. 方法主线：
   官方数据背景说明 → 目标区县确定 → 生成 1km 网格 → 高德 POI 查询与缓存 → 网格级指标构建 → 便利店/轻餐饮差异化评分 → 全局 Top N 与各区县 Top N 推荐 → 地图洞察 → 智能报告。
6. 前端目标：
   使用 Streamlit 做成“黔址优选商业智能选址工作台”，包含左侧导航、顶部标题栏、步骤式选址流程、地图展示、推荐表格、指标解释和报告生成。
7. 禁止事项：
   - 不要声称获取全量高德 POI；
   - 不要绕过 API 限制；
   - 不要做门牌号级推荐；
   - 不要写精准预测盈利；
   - 不要伪造真实客流、租金、营收；
   - 不要把省级就业数据硬拆到 1km 网格；
   - 不要删除旧文件，旧 OSM 相关代码可以保留为 legacy，但不要作为新主线。
```

---

## 3. 执行总览

项目历史上按 18 步实施，当前 Step 0 到 Step 18 均已完成。下表用于追溯任务边界和验收来源：

| 步骤 | 任务 | 目标 | 是否必须 |
|---:|---|---|---|
| Step 0 | 建立迁移分支与基线检查 | 确认当前项目状态 | 必须 |
| Step 1 | 调整项目方法文档和命名 | 统一方法口径 | 必须 |
| Step 2 | 统一配置文件 | 管理路径、区县、权重、POI 类别 | 必须 |
| Step 3 | 高德 API 客户端与缓存 | 封装高德请求 | 必须 |
| Step 4 | 目标区县边界与基础信息 | 获取区县 adcode、center、boundary | 必须 |
| Step 5 | 1km 候选网格生成 | 生成核心评分对象 | 必须 |
| Step 6 | 网格 POI 查询与统计 | 形成 POI 特征基础 | 必须 |
| Step 7 | 网格级指标工程 | 从 POI 统计转成模型指标 | 必须 |
| Step 8 | 网格评分与推荐结果 | 输出 Top N 推荐 | 必须 |
| Step 9 | 地图生成模块 | 输出可嵌入前端的地图 | 强烈建议 |
| Step 10 | 报告生成模块 | 输出 Markdown 选址报告 | 强烈建议 |
| Step 11 | Streamlit 多页架构 | 改造成工作台入口 | 必须 |
| Step 12 | 前端视觉样式 | 仿百度慧眼平台风格 | 强烈建议 |
| Step 13 | 选址决策流程整合 | 去除重复入口，能力并入 Step 15 | 必须 |
| Step 14 | 区域对比页面 | 做区县背景对比 | 建议 |
| Step 15 | 网格推荐页面 | 展示核心推荐结果 | 必须 |
| Step 16 | 地图洞察页面 | 展示推荐地图 | 强烈建议 |
| Step 17 | 智能报告页面 | 展示并导出报告 | 强烈建议 |
| Step 18 | 一键运行脚本和验收 | 项目可复现、可演示 | 必须 |

---

# 第一阶段：项目方法迁移

---

## Step 0：建立迁移分支与基线检查

### 目标

确认当前项目可运行，先不改业务逻辑。

### 给 Codex 的指令

```text
任务 0：建立迁移分支与基线检查。

请只做检查，不做业务重构。

1. 历史迁移分支已经完成。当前分支为：
   codex/v2.0

2. 检查项目目录：
   - data/
   - src/
   - outputs/
   - docs/
   - tests/

3. 检查 src/ 和一键脚本下所有 Python 文件语法：
   python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; ast.parse(pathlib.Path('scripts/run_pipeline.py').read_text(encoding='utf-8')); print('syntax ok')"

4. 检查现有核心输出是否存在：
   - data/processed/official/macro_clean.csv
   - data/processed/official/employment_clean.csv
   - outputs/results/metadata/字段说明表.csv
   - outputs/reports/数据识别与合理性报告.md

5. 历史状态文档保存为 docs/history/迁移前项目状态.md，说明：
   - 当前数据源
   - 当前评分逻辑
   - 当前前端入口
   - 需要废弃或降级为 legacy 的 OSM/Geofabrik 模块
   - 本次迁移目标

禁止：
- 不要修改评分逻辑；
- 不要修改 Streamlit 页面；
- 不要删除 OSM 旧代码。
```

### 验收命令

```bash
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; ast.parse(pathlib.Path('scripts/run_pipeline.py').read_text(encoding='utf-8')); print('syntax ok')"
```

### 预期产出

```text
docs/history/迁移前项目状态.md
```

---

## Step 1：调整项目方法文档和命名

### 目标

把旧的“两阶段 OSM 选址”口径改成新方法。

### 给 Codex 的指令

```text
任务 1：调整项目方法文档和命名。

请把项目主方法从：
“两阶段空间选址推荐”
调整为：
“区县背景约束下的网格级多因子商业选址推荐模型”。

需要修改或新增：

1. docs/方法调整说明.md
内容包括：
- 为什么不再以 Geofabrik/OSM 为主数据源；
- 为什么只做贵阳市典型区县；
- 为什么区县只作为背景约束，不作为核心筛选对象；
- 为什么 1km 网格是核心评分对象；
- 为什么高德 POI 数据只能作为原型验证和样本数据；
- 当前不做门牌号级推荐。

2. 修改 docs/初赛方案.md 或新增 docs/初赛方案_新版.md
新技术路线改为：
官方宏观经济与就业数据
→ 贵阳市典型区县选择
→ 高德行政区划与 POI 数据接入
→ 1km 评价网格生成
→ 网格 POI 统计
→ 多因子评分
→ 便利店/轻餐饮差异化推荐
→ 地图展示
→ 智能报告生成。

3. 修改 README.md 中项目定位：
从“贵州省范围”改为：
“以贵阳市典型区县为试点的社区商业智能选址原型”。

禁止：
- 不要删除旧方案文件；
- 旧方案可标记为 legacy；
- 不要写“全量 POI”；
- 不要写“精准预测盈利”。
```

### 预期产出

```text
docs/方法调整说明.md
docs/初赛方案_新版.md
README.md
```

---

## Step 2：统一配置文件

### 目标

后续高德 Key、目标区县、POI 类别、权重都由配置管理。

### 给 Codex 的指令

```text
任务 2：统一配置文件。

请完善 config.yaml，并新增 src/core/config.py。

config.yaml 需要包含：

1. project
   - name: 黔址优选
   - city: 贵阳市
   - grid_size_m: 1000
   - default_radius_m: 500
   - optional_radius_m: [500, 800, 1000]

2. target_districts
   第一版：
   - 云岩区
   - 南明区
   - 观山湖区
   可选增强：
   - 花溪区
   - 白云区

3. data_paths
   - official_raw_dir
   - official_processed_dir
   - processed_dir
   - results_dir
   - results_metadata_dir
   - reports_dir
   - figures_dir
   - amap_cache_dir
   - demo_dir

4. poi_categories
   - convenience_store: 便利店
   - supermarket: 超市
   - restaurant: 餐饮
   - fast_food: 快餐
   - snack: 小吃
   - cafe: 咖啡
   - tea: 茶饮
   - school: 学校
   - hospital: 医院
   - mall: 商场
   - office: 写字楼
   - residential: 小区
   - bus_stop: 公交站
   - subway_station: 地铁站
   - parking: 停车场

5. weights
   convenience:
     traffic_accessibility
     consumption_potential
     employment_customer_proxy
     synergy_score
     competition_pressure
     business_atmosphere
   light_food:
     traffic_accessibility
     consumption_potential
     employment_customer_proxy
     synergy_score
     competition_pressure
     business_atmosphere

6. 当前还包含：
   - poi_typecodes
   - scoring_templates
   - map
   - llm

src/core/config.py 实现：
- load_config()
- get_project_root()
- get_path(name)
- ensure_dirs()
- get_weights(business_type)
- get_poi_categories()

要求：
- 所有路径使用 pathlib.Path；
- 若配置缺失，需要有清晰错误提示；
- 不要在业务代码中硬编码路径。
```

### 验收命令

```bash
python -c "from src.core.config import load_config, ensure_dirs, get_weights; cfg=load_config(); ensure_dirs(cfg); print(get_weights(cfg, 'convenience'))"
```

---

# 第二阶段：高德数据接入与网格评分

---

## Step 3：高德 API 客户端与缓存

### 目标

高德 API 请求模块化、可缓存、可离线回放。

### 给 Codex 的指令

```text
任务 3：新增高德 API 客户端。

新增 src/pipeline/amap_client.py。

功能要求：

1. 从环境变量读取 AMAP_KEY。
   - 环境变量名：AMAP_KEY
   - 如果不存在，不报错，但客户端进入 demo 模式。

2. 实现 AmapClient 类：
   - __init__(self, api_key=None, cache_dir=None)
   - get_district(keyword, city=None)
   - search_poi_around(location, keywords, radius=500, city=None, page=1, offset=20)
   - search_poi_polygon(polygon, keywords, city=None, page=1, offset=20)，如果暂时不用可以先保留接口
   - _request_with_cache(url, params, cache_key)

3. 缓存规则：
   - 所有原始响应保存到 data/cache/amap/
   - 相同参数不重复请求
   - 缓存文件名用参数 hash
   - 保存 JSON 原始响应

4. 请求限制：
   - 客户端每次真实请求前固定等待 0.2 秒；
   - 不做并发请求；
   - 不绕过 API 限制。

5. 错误处理：
   - key 缺失：返回 None 或抛出清晰异常，由上层转 demo 数据；
   - 请求失败：记录日志，不中断全部流程；
   - 返回为空：保存空结果。

6. 新增 tests/pipeline/test_amap_client.py：
   - 测试无 AMAP_KEY 时不会崩溃；
   - 测试 cache key 可生成；
   - 测试参数构造正确。

禁止：
- 不要爬高德网页；
- 不要绕过 API；
- 不要声称获得全量数据。
```

### 验收命令

```bash
python -m unittest tests/pipeline/test_amap_client.py -v
python -c "from src.pipeline.amap_client import AmapClient; c=AmapClient(); print('client ok')"
```

---

## Step 4：目标区县边界与基础信息

### 目标

获取云岩、南明、观山湖等区县的 adcode、center、boundary。

### 给 Codex 的指令

```text
任务 4：目标区县边界与基础信息。

新增 src/pipeline/district_builder.py。

输入：
- config.yaml 中的 target_districts
- AMAP_KEY

输出：
1. data/processed/target_districts.csv
字段：
- district_name
- city_name
- adcode
- center_lon
- center_lat
- has_boundary
- data_source

2. data/processed/target_district_boundaries.geojson
字段：
- district_name
- adcode
- geometry

实现要求：
1. 调用高德行政区划 API 获取区县信息。
2. 解析 polyline 边界为 polygon。
3. 注意高德坐标系为 GCJ-02，当前前端地图若用高德/folium 需要标注坐标系。
4. 如果边界解析失败：
   - 仍保存 center；
   - has_boundary=False；
   - 记录到 outputs/results/district_boundary_warnings.md。
5. 当前真实边界刷新不提供内置离线区县文件：
   - `python scripts/run_pipeline.py --refresh-amap` 会在执行前强制检查 `AMAP_KEY`；
   - 默认离线流程直接使用已跟踪的 Step 4–6 输入，不重复执行本模块；
   - 单独执行本模块且未配置 `AMAP_KEY` 只会得到无响应警告和不完整输出，不作为交付路径。

禁止：
- 不要用街道边界作为核心，因为高德街道边界不稳定/不可得；
- 不要编造真实边界；
- 不要强行让流程崩溃。
```

### 验收命令

```bash
python -m src.pipeline.district_builder
```

---

## Step 5：生成 1km 候选评价网格

### 目标

在目标区县内生成网格，作为真正评分对象。

### 给 Codex 的指令

```text
任务 5：生成 1km 候选评价网格。

新增 src/pipeline/grid_builder.py。

输入：
- data/processed/target_district_boundaries.geojson
- config.yaml 中 grid_size_m，默认 1000

输出：
1. data/processed/candidate_grids.geojson
2. data/processed/candidate_grids.csv

字段：
- grid_id
- district_name
- adcode
- centroid_lon
- centroid_lat
- area_km2
- geometry_wkt
- data_source

技术要求：
1. 必须使用投影坐标系生成 1000m x 1000m 网格，不要直接在经纬度上按度切分。
2. 米制计算使用 `EPSG:32648`；输出数值沿用高德数据坐标表达，并在 GeoJSON 中明确标记 `coord_system=GCJ-02`。
3. 只保留与区县边界相交的网格。
4. 对网格面积过小的边缘网格可以保留，但需要 area_km2 字段。
5. 如果没有真实边界，则用区县 center 生成一个回退方格，并在 data_source 字段精确标记为 `demo_center`。

禁止：
- 不要生成门牌号；
- 不要在经纬度坐标下直接按 0.01 度当作 1km；
- 不要对全贵州生成网格。
```

### 验收命令

```bash
python -m src.pipeline.grid_builder
```

---

## Step 6：网格级 POI 查询与统计

### 目标

对三区各 20 个空间分散样本网格的中心点做周边 POI 查询，得到模型输入表。

### 给 Codex 的指令

```text
任务 6：网格级 POI 查询与统计。

新增 src/pipeline/poi_fetcher.py。

输入：
- data/processed/candidate_grids.csv
- config.yaml 中 poi_categories
- config.yaml 中 default_radius_m，默认 500
- AMAP_KEY；在线采集必须配置。默认离线交付直接复用已跟踪的 `grid_poi_raw.csv` 和 `grid_poi_counts.csv`

输出：
1. data/processed/grid_poi_raw.csv
字段：
- grid_id
- district_name
- category_key
- category_keyword
- poi_id
- poi_name
- poi_type
- lon
- lat
- address
- source

2. data/processed/grid_poi_counts.csv
字段：
- grid_id
- district_name
- convenience_store_count
- supermarket_count
- restaurant_count
- fast_food_count
- snack_count
- cafe_count
- tea_count
- school_count
- hospital_count
- mall_count
- office_count
- residential_count
- bus_stop_count
- subway_station_count
- parking_count

实现要求：
1. 默认先从每个区县确定性抽取 20 个空间分散网格，再对每个样本网格中心点和每个 POI 类别调用周边搜索；`--all-grids` 才处理输入文件中的全部网格。
2. 半径默认 500m。
3. 每类最多抓取前若干页，默认不要超过官方限制。
4. 所有响应走 AmapClient 缓存。
5. 需要去重：同一个 poi_id 在同一 grid/category 下不要重复统计。
6. 如果同一 POI 在多个类别下重复出现，可以暂时允许，但报告中说明 POI 分类可能存在重叠。
7. 输出 outputs/results/poi_fetch_summary.md：
   - 查询区县数
   - 网格数
   - 类别数
   - `amap_api` 或 `demo` 模式
   - 每类 POI 数量
   - 数据限制说明

8. 当前 `config.yaml` 保留 `data_paths.demo_dir`，`poi_fetcher` 也会精确查找
   `data/demo/grid_poi_counts_demo.csv`，但仓库当前没有该文件。因此无 Key
   的稳定入口是 `python scripts/run_pipeline.py`，不是单独重跑 Step 6。

禁止：
- 不要声称抓取全量 POI；
- 不要并发压接口；
- 不要绕过分页限制。
```

### 验收命令

```bash
python -m src.pipeline.poi_fetcher
```

---

## Step 7：网格级指标工程

### 目标

把 POI 数量转成可解释指标。

### 给 Codex 的指令

```text
任务 7：网格级指标工程。

新增或重构 src/modeling/feature_engineering.py。

输入：
- data/processed/grid_poi_counts.csv
- data/processed/candidate_grids.csv

官方数据实际位于：
- data/processed/official/macro_clean.csv
- data/processed/official/employment_clean.csv

这两个官方文件只用于背景与报告说明，不是 `feature_engineering.py` 的运行输入。

输出：
- data/processed/grid_scoring_input.csv

构造以下指标：

1. traffic_accessibility
由 bus_stop_count、subway_station_count、parking_count 构成。

2. consumption_potential
由 residential_count、supermarket_count、mall_count、school_count、hospital_count 构成。
官方宏观经济和就业数据只作为背景，不硬拆到网格。

3. employment_customer_proxy
由 office_count、mall_count、school_count、restaurant_count 构成，用作就业/办公/学生客群代理。

4. convenience_synergy_score
由 residential、school、hospital、bus_stop、supermarket 构成。

5. light_food_synergy_score
由 office、school、mall、bus_stop、cafe、tea 构成。

6. convenience_competition_pressure
由 convenience_store_count、supermarket_count 构成。

7. light_food_competition_pressure
由 restaurant_count、fast_food_count、snack_count、cafe_count、tea_count 构成。

8. business_atmosphere
由 mall、restaurant、cafe、tea、supermarket 等体现商业活跃度。

要求：
1. 所有指标归一化到 0-100。
2. 缺失值填 0。
3. 输出字段必须包含：
   grid_id, district_name, centroid_lon, centroid_lat,
   traffic_accessibility,
   consumption_potential,
   employment_customer_proxy,
   convenience_synergy_score,
   light_food_synergy_score,
   convenience_competition_pressure,
   light_food_competition_pressure,
   business_atmosphere

4. 生成 outputs/results/feature_engineering_report.md，解释每个指标如何构造。

禁止：
- 不要把省级就业数据分配到网格；
- 不要伪造真实客流；
- 不要使用没有来源的字段。
```

### 验收命令

```bash
python -m src.modeling.feature_engineering
```

---

## Step 8：网格评分与推荐结果

### 目标

输出最终用于前端展示的推荐表。

### 给 Codex 的指令

```text
任务 8：网格评分与推荐结果。

新增或重构 src/modeling/scoring_model.py。

输入：
- data/processed/grid_scoring_input.csv
- config.yaml 中便利店和轻餐饮权重
- config.yaml 中 community_retail 和 food_service 指标模板

输出：
1. outputs/results/grid_stage_score_result.csv
2. outputs/results/district_summary_result.csv
3. outputs/results/recommendation_summary.md
4. outputs/results/profile_metadata.json

评分逻辑：
1. 正向指标：
   - traffic_accessibility
   - consumption_potential
   - employment_customer_proxy
   - synergy_score
   - business_atmosphere

2. 负向指标：
   - competition_pressure
评分时使用 competition_score = 100 - competition_pressure。

3. 默认分别计算：
   - convenience_score
   - light_food_score

4. 支持用户自定义方案：
   - 自定义 profile_id 和 profile_name
   - 选择 community_retail 或 food_service 指标模板
   - 设置六项非负权重，权重总和必须为 1
   - 自定义结果独立写入 outputs/results/custom_profiles/<profile_id>/

5. 输出推荐：
   - 全局便利店 Top 10
   - 全局轻餐饮 Top 10
   - 各区县便利店 Top 5
   - 各区县轻餐饮 Top 5

6. 为每种方案分别生成：
   - 竞争得分
   - 综合得分
   - 全局排名与区县排名
   - 主要优势与主要风险
   - recommendation_level：推荐 / 谨慎推荐 / 暂不推荐

7. 只有 has_poi_activity=True 的网格参与排名。
   无活动网格得分为 0，排名留空，固定标记为暂不推荐。

8. district_summary_result.csv 包含：
   - district_name
   - grid_count
   - active_grid_count
   - avg_convenience_score
   - avg_light_food_score
   - top_convenience_grid_id
   - top_light_food_grid_id
   - poi_total_count

9. 在不改变综合得分、权重、排名和推荐等级的前提下增加区域市场诊断：
   - 只使用全市有 POI 活动网格计算 P33 和 P67
   - 市场阶段：市场空白型、待培育型、成熟商圈型、一般观察型
   - 竞争状态：过度竞争预警、未触发过度竞争预警
   - 无活动网格标记为无 POI 活动和不参与诊断
   - 需求客群代理为消费潜力与就业/办公客群代理的均值，不是真实客流
   - 相同指标模板的自定义方案使用相同诊断，权重只影响综合得分和排名

禁止：
- 不要输出“该门店一定盈利”；
- 不要输出门牌号；
- 不要用区县整体分数替代网格分数。
- 不要把市场空白解释为保证盈利；
- 不要把过度竞争预警解释为企业真实经营状况。
```

### 验收命令

```bash
python -m src.modeling.scoring_model
```

自定义方案示例：

```powershell
python -m src.modeling.scoring_model `
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

---

## Step 9：地图生成模块

### 目标

生成可嵌入前端的网格热力图和推荐点地图。

### 给 Codex 的指令

```text
任务 9：地图生成模块。

原地升级 src/presentation/map_viz.py，保留当前模块布局和
python -m src.presentation.map_viz 入口，不新增重复的 src/map_viz.py。

输入：
- outputs/results/grid_stage_score_result.csv
- data/processed/candidate_grids.geojson

输出：
1. outputs/figures/convenience_grid_map.html
2. outputs/figures/light_food_grid_map.html
3. outputs/figures/poi_overview_map.html，可选

功能要求：
1. 使用高德 JS API 2.0 作为正式交互地图主链，Folium 作为兼容回退。
2. 如果 candidate_grids.geojson 存在，展示网格面；
   如果不存在，则展示中心点。
3. 地图支持：
   - 便利店评分热力；
   - 轻餐饮评分热力；
   - Top N 推荐网格高亮；
   - tooltip 显示 grid_id、district_name、score、main_advantage、main_risk。
4. 790 个空间网格作为完整背景：
   - 未采集网格显示浅灰；
   - 无 POI 活动网格显示中性灰；
   - 活跃网格按固定 0-100 色阶着色；
   - 全局 Top 10 使用编号标记和加粗边界。
5. 高德主链直接使用 GCJ-02，不改写 Step 4 到 Step 8 的正式数据；
   Folium 回退路径才临时转换为 WGS84。
6. 地图页使用 Streamlit components 嵌入高德 HTML，支持默认与自定义评分方案；
   页面提供“使用兼容地图”开关，无 JS 凭据时自动回退 Folium。
7. 自定义方案读取 outputs/results/custom_profiles/<profile_id>/
   grid_score_result.csv 中稳定的 profile_* 字段，不预生成自定义 HTML。
8. 高德 Web 服务继续使用 AMAP_KEY；地图独立读取 AMAP_JS_KEY 与
   AMAP_JS_SECURITY_CODE，凭据不得写入仓库文件。
9. 悬停和点击详情增加程序生成的市场阶段、竞争状态和诊断摘要；
   地图颜色和 Top 10 标记仍只由原评分与排名决定。

禁止：
- 不要把高德 Key 或安全密钥写入 config.yaml、源码、日志或文档；
- 不要把浏览器端高德 HTML 提交到 Git；
- 不要在地图上显示真实门牌号推荐。
```

### 验收命令

```bash
python -m src.presentation.map_viz
```

---

## Step 10：选址报告生成模块

### 目标

基于 Step 8 正式评分结果，用 DeepSeek 或规则模板生成可解释选址报告。

### 给 Codex 的指令

```text
任务 10：选址报告生成模块。

实际模块路径为 src/presentation/report_generator.py。
新增共享评分方案目录 src/core/profile_catalog.py。

输入：
- outputs/results/grid_stage_score_result.csv
- outputs/results/profile_metadata.json
- outputs/results/custom_profiles/<profile_id>/grid_score_result.csv
- outputs/results/custom_profiles/<profile_id>/profile_metadata.json
- data/processed/official/macro_clean.csv
- data/processed/official/employment_clean.csv

输出：
- outputs/reports/<profile_id>/<grid_id>_选址报告.md

实现函数：
1. profile_specs_by_id()
2. active_profile_results(profile)
3. generate_site_report(grid_id, profile)
4. export_report(report, grid_id, profile, output_path)

报告结构：
一、评价网格基本信息
二、适配业态与推荐等级
三、交通可达性分析
四、消费潜力分析
五、就业/办公客群代理分析
六、共生业态分析
七、竞争压力分析
八、商业氛围与权重方案
九、主要优势与风险
十、经营建议
十一、数据来源与限制说明

要求：
- 默认读取 DEEPSEEK_API_KEY 并使用 deepseek-v4-pro 非思考模式；
- 使用 DeepSeek JSON Output 生成结构化分析素材，不要求模型直接输出 Markdown；
- 结构化结果必须包含 11 个章节分析、真实证据字段、经营建议依据和四项质量检查；
- Python 校验结构、证据字段、竞争方向和禁写内容后，从真实评分记录写入数值并渲染 Markdown；
- 模型分析文字不得自行复述或计算数值；
- 交通可达性只解释公交站、地铁站和停车场 POI，不扩展为路网密度或道路等级；
- JSON 空响应使用同一模型重试一次；
- Pro 仅在连接、超时、限流、服务端错误或模型不可用时回退 deepseek-v4-flash；
- 鉴权、余额、请求格式、参数、输入数据和内容质量错误不得回退；
- CLI 可通过 --template 明确使用规则模板；
- 支持 convenience、light_food 和有效自定义评分方案；
- 只为有 POI 活动且具有有效排名的网格生成报告；
- 所有结论必须来自输入字段；
- 官方宏观与就业数据当前只作贵州省级背景和适用边界说明，不参与网格评分；
- employment_customer_proxy 只能解释为 POI 构成的就业/办公客群代理；
- 返回正文为空或缺少规定章节时不得导出。

禁止：
- 不要编造租金；
- 不要编造客流；
- 不要编造营收；
- 不要写“已完成真实盈利预测”。
```

### 验收命令

```bash
python -m src.presentation.report_generator --profile convenience --grid-id grid_520103_000078
```

---

# 第三阶段：前端改造

---

## Step 11：Streamlit 多页架构改造

### 目标

把 `app.py` 从单页报表改成选址工作台入口。

### 给 Codex 的指令

```text
任务 11：Streamlit 多页架构改造。

请把前端改造成类似百度地图慧眼的“选址工作台”。

技术要求：
1. 使用 st.set_page_config(layout="wide")。
2. 优先使用 Streamlit 的 st.Page 和 st.navigation 组织多页。
3. 如果当前 Streamlit 版本不支持 st.navigation，则退化为 sidebar radio。

页面结构：
1. 项目总览
2. 数据底座
3. 区域对比
4. 网格推荐
5. 地图洞察
6. 智能报告
7. 项目说明

当前目录：
src/app.py 作为唯一当前入口；
src/web/pages/
  overview.py
  data_foundation.py
  district_compare.py
  grid_recommendation.py
  map_insight.py
  report_center.py
  project_notes.py
src/web/ui/workbench.py 作为共享视觉模块。

禁止：
- 不要改动评分模型；
- 不要把所有页面堆在一个长页面；
- 不要删除旧 app.py，可先备份为 src/legacy/v1/app.py。
```

### 当前实际实施

- 当前 Streamlit 版本为 `1.58.0`，正式入口使用 `st.Page` 和 `st.navigation`，并保留 sidebar radio 回退。
- Step 11 最初建立八页结构；Step 13–15 实施时删除职责重复的独立“选址分析”页，当前 `src/app.py` 负责宽屏配置、七页注册和导航；原入口保留为 `src/legacy/v1/app.py`。
- 页面模块实际位于 `src/web/pages/`，文件名采用无数字前缀的 Python 模块名，并通过稳定的页面注册顺序控制导航。
- `src/web/decision_context.py` 保存评分方案和网格选择，使网格推荐、地图洞察和智能报告能够复用当前决策上下文。
- “网格推荐”“地图洞察”和“智能报告”使用各页面独立评分方案选择器，不保留全局固定业态侧栏。
- 项目总览增加真实 POI 和得分图表；区域对比展示原始 POI 分组统计；网格推荐统一承载自定义权重和即时评分。
- 地图和报告页面迁移后继续兼容 Step 9–10 的默认、自定义方案、静态回退、会话缓存和模板报告行为。

### 验收命令

```bash
streamlit run src/app.py
```

---

## Step 12：前端视觉样式改造

### 目标

让页面从默认 Streamlit 变成商业平台风格。

### 给 Codex 的指令

```text
任务 12：前端视觉样式改造。

请在 Streamlit 中增加 CSS，使页面风格接近商业选址工作台。

要求：
1. 顶部深色标题栏：
   黔址优选 | 社区商业智能选址决策系统

2. 左侧导航：
   使用 sidebar 或 st.navigation。

3. 主色：
   蓝色作为强调色。

4. 页面背景：
   浅灰。

5. 内容卡片：
   白底、圆角、轻阴影、适当留白。

6. 指标卡：
   展示已接入区县数、候选网格数、POI 类别数、推荐结果数。

7. 步骤式流程卡：
   决策流程整合到“网格推荐”页：
   Step 1 选择应用场景
   Step 2 设置分析参数
   Step 3 查看推荐结果
   Step 4 生成报告

8. 响应式布局：
   表格和地图左右分栏；
   参数区和结果区分区显示。

禁止：
- 不要过度花哨；
- 不要引入复杂前端框架；
- 不要依赖外部 CDN；
- 不要破坏 Streamlit 运行。
```

### 当前实施状态

- 实际共享视觉模块为 `src/web/ui/workbench.py`，主题配置为 `.streamlit/config.toml`。
- `src/app.py` 在运行七页导航前统一加载主题和标题栏，未隐藏 Streamlit 原生工具栏。
- 首页四项主指标读取真实数据与配置，当前为 3 个目标区县、790 个空间评价网格、15 类 POI 和 41 个活跃推荐网格；60 个采样网格和 2 套默认评分方案作为辅助信息展示。正式保存自定义方案后，页面再通过共享方案目录动态发现。
- 标题栏桌面端居中显示并使用 24px 字号，窄屏下固定缩小字号和间距。
- “网格推荐”“地图洞察”“智能报告”分别采用参数与结果分区；智能报告保持按钮触发，不在页面加载时调用模型。
- 响应式样式使用 900px 和 600px 两个断点，不依赖外部 CDN、外部字体、JavaScript 或复杂前端框架。
- Step 13–15 已在该视觉基础上完成页面去重、首页和区域图表、自定义权重、即时评分及推荐结果整合。


### 验收命令

```bash
streamlit run src/app.py
```

---

## Step 13：选址决策流程整合

### 目标

消除“选址分析”和“网格推荐”的职责重复，将核心决策能力集中到 Step 15。

### 给 Codex 的指令

```text
任务 13：选址决策流程整合。

要求：
1. 删除独立“选址分析”页面和导航项。
2. 默认方案、自定义权重、推荐结果和指标分解并入 Step 15。
3. 地图和报告保留独立页面，不在网格推荐中重复嵌入。
4. 保留 Step 编号，记录页面去重原因和真实实施结果。
```

### 验收重点

```text
七页导航中不存在重复的“选址分析”入口；
网格推荐是评分参数与推荐结果的唯一主入口。
```

---

## Step 14：实现“区域对比”页面

### 目标

区县只做背景和分组，不做最终选址结论。

### 给 Codex 的指令

```text
任务 14：实现“区域对比”页面。

输入：
- outputs/results/district_summary_result.csv
- data/processed/grid_poi_counts.csv

页面展示：
1. 区县概览表：
   - district_name
   - grid_count
   - poi_total_count
   - avg_convenience_score
   - avg_light_food_score
   - top_convenience_grid_id
   - top_light_food_grid_id

2. 柱状图：
   - 各区县便利店 POI 数量
   - 各区县餐饮 POI 数量
   - 各区县学校/医院/商场/写字楼/小区数量
   - 各区县公交/地铁/停车场数量

3. 文字说明：
   - 区县对比用于背景画像和结果分组；
   - 最终推荐仍以 1km 网格评分为准。

禁止：
- 不要输出“某区一定最好”；
- 不要以区县平均分替代网格级推荐。
```

### 当前实际实施

- 保留三区汇总表。
- 根据 `data/processed/grid_poi_counts.csv` 聚合并展示三组原始 POI 数量。
- 图表使用 Altair，所有数量保持原始统计口径，不把区县平均分写成最终推荐结论。

---

## Step 15：实现“网格推荐”页面

### 目标

展示最终推荐结果，是整个项目最核心的前端页面。

### 给 Codex 的指令

```text
任务 15：实现“网格推荐”页面。

输入：
- data/processed/grid_scoring_input.csv
- outputs/results/grid_stage_score_result.csv
- outputs/results/custom_profiles/<profile_id>/

页面必须包含：

1. 方案来源：
- 默认社区便利店
- 默认轻餐饮
- 已保存自定义方案
- 新建自定义方案

2. 新建方案：
- 明确选择 community_retail 或 food_service 指标模板
- 六项百分比数字输入，范围 0-100
- 显示已分配和剩余权重
- 提供便利店、轻餐饮、平均分配、重置和一键归一

3. 即时评分：
- 六项全零时禁止计算
- 非零且合计不为 100.00% 时使用归一权重预览
- 直接调用 score_profile()，不启动子进程
- 41 个活跃网格参与排名，19 个无活动网格不进入推荐名单

4. 推荐结果：
- 全局 Top 10
- 用户选择区县后的 Top 5
- 六维正向指标、主要优势、主要风险和推荐等级
- 竞争维度显示 100 - competition_pressure 的低竞争得分
- 展示四类市场阶段和过度竞争预警数量
- 支持市场阶段与竞争状态筛选
- 未启用诊断筛选时保持 Top 10 或区县 Top 5
- 启用诊断筛选后展示全部匹配网格，并按原排名排序

5. 正式保存：
- profile_id 只允许小写字母、数字和下划线
- 中文方案名称非空
- 输入合计必须精确为 100.00%
- 已存在标识不得覆盖
- 写出评分结果、区县汇总、推荐摘要和方案元数据四个文件

禁止：
- 不要只展示总分；
- 必须展示优势和风险；
- 不要写门牌号推荐。
```

### 当前实际实施

- 页面直接构造 `ScoringProfile` 并调用 `score_profile()` 完成内存预览。
- 百分之一最大余数法保证归一结果恰好为 100.00%，相同输入重复执行结果一致。
- 正式方案调用现有四文件事务；保存成功后地图和智能报告页面可通过共享方案目录发现。
- 区域诊断复用 `src/modeling/market_diagnostics.py`，只使用全市活跃网格的相对三分位，不改变综合得分、排名和推荐等级。

---

## Step 16：实现“地图洞察”页面

### 目标

做出“选址地图”的直观展示。

### 给 Codex 的指令

```text
任务 16：实现“地图洞察”页面。

输入：
- outputs/figures/convenience_grid_map.html
- outputs/figures/light_food_grid_map.html
或由 src/presentation/map_viz.py 动态生成。

页面功能：
1. 选择业态：
   - 便利店
   - 轻餐饮

2. 展示地图：
   - 推荐网格中心点或网格面；
   - 评分颜色；
   - Top N 高亮；
   - tooltip 显示 grid_id、区县、得分、优势、风险。

3. 高德 JS API 使用 GCJ-02 原始网格数据；用户可主动切换 Folium 兼容地图。
4. 缺少 AMAP_JS_KEY 或 AMAP_JS_SECURITY_CODE 时自动回退 Folium，并显示准确说明。

当前实际页面只提供评分方案和兼容地图开关，地图始终展示完整 790 个空间网格；区县信息进入悬停和点击详情。地图页区县筛选仍属于后续路线，未写成当前能力。

禁止：
- 不要把任何高德凭据写入仓库；
- 不要显示门牌号级结论；
- 不要在高德加载失败时伪装成成功。
```

---

## Step 17：实现“智能报告”页面

### 目标

把模型结果转化成可以提交/展示的报告。

### 给 Codex 的指令

```text
任务 17：实现“智能报告”页面。

输入：
- outputs/results/grid_stage_score_result.csv
- outputs/results/profile_metadata.json
- outputs/results/custom_profiles/<profile_id>/
- src/presentation/report_generator.py

页面流程：
1. 选择评分方案：
   - 默认社区便利店
   - 默认轻餐饮
   - 有效自定义评分方案

2. 选择 grid_id：
   仅列出有 POI 活动且具有有效排名的网格；
   下拉框显示全局排名 + district_name + grid_id + score。

3. 点击生成报告。

4. 页面展示 Markdown 报告。

5. 支持下载：
   - Markdown 文件

报告必须包含：
一、评价网格基本信息
二、适配业态与推荐等级
三、交通可达性分析
四、消费潜力分析
五、就业/办公客群代理分析
六、共生业态分析
七、竞争压力分析
八、商业氛围与权重方案
九、主要优势与风险
十、经营建议
十一、数据来源与限制说明

禁止：
- 不要编造真实租金；
- 不要编造真实客流；
- 不要编造真实营收。
```

### 当前实际实施

- 页面模块为 `src/web/pages/report_center.py`，报告引擎为 `src/presentation/report_generator.py`，不使用总控旧示例中的根目录模块路径。
- 页面使用独立评分方案选择器，支持默认社区便利店、默认轻餐饮和有效自定义评分方案；只列出有 POI 活动且具有有效排名的网格。
- 页面仅在用户点击“生成智能报告”后调用 DeepSeek，并按评分方案和网格写入 Streamlit 会话状态，页面刷新不会重复调用。
- 默认使用 `deepseek-v4-pro` 非思考模式；仅连接、超时、限流、服务端错误或模型不可用时回退 `deepseek-v4-flash`。鉴权、余额、请求参数和输入数据错误直接展示，不通过模板或切换模型伪装成功。
- DeepSeek 调用失败后，用户可明确点击“使用模板报告”；模板报告与 API 成功状态分别显示。
- 报告采用 Step 10 已确认的 11 章结构，保留“商业氛围与权重方案”，将主要优势和主要风险合并为一个章节。
- 页面支持 Markdown 预览与下载；业务报告不显示模型品牌，页面状态区显示实际使用的 Pro、Flash 或模板模式。
- 2026 年 6 月 13 日已使用用户级 `DEEPSEEK_API_KEY` 完成真实连通性验证，`deepseek-v4-pro` 成功返回完整报告，未触发 Flash 回退。

### 验收命令

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "User")
python -m unittest tests.presentation.test_report_generator tests.web.test_app -v
streamlit run src/app.py
```

---

## Step 18：一键运行脚本和最终验收

### 目标

让项目能复现，方便交付和演示。

### 给 Codex 的指令

```text
任务 18：一键运行脚本和最终验收。

新增 `scripts/run_pipeline.py`。

默认离线流程：
1. 校验 Step 4–6 已跟踪输入。
2. `python -m src.modeling.feature_engineering`
3. `python -m src.modeling.scoring_model`
4. `python -m src.presentation.map_viz`
5. 为便利店和轻餐饮 Top 1 生成规则模板报告。
6. 验收区县、网格、评分、地图和报告。
7. 写出 `outputs/results/pipeline_run_summary.md`。

可选参数：
- `--refresh-official`：重新处理六个官方 Excel。
- `--refresh-amap`：要求 `AMAP_KEY`，刷新三区边界、网格和三区各 20 个 POI 样本网格。
- `--with-llm`：要求 `DEEPSEEK_API_KEY`，生成两类 Top 1 DeepSeek 报告。
- `--serve`：验收成功后在 `0.0.0.0:8501` 启动 Streamlit；端口占用时停止，不启动第二个实例。

所有模块使用 `sys.executable -m` 调用。任一阶段失败后停止后续阶段，运行摘要不得包含密钥值。

更新 README.md：
- 环境安装
- AMAP_KEY 配置
- 无 AMAP_KEY 时使用已跟踪输入完成默认离线复现
- 一键运行命令
- Streamlit 启动命令
- 输出文件说明
- 当前限制

锁定当前已验证的 Python 和依赖版本。

新增 docs/最终交付清单.md：
- 数据文件
- 结果文件
- 地图文件
- 报告文件
- 前端页面
- 演示步骤

同步 docs/系统架构说明.md：
- 当前交付按五层架构说明：数据层、管线层、模型层、报告层、前端层。
- 数据层对应 `data/` 与 `outputs/`。
- 管线层对应 `src/pipeline/`。
- 模型层对应 `src/modeling/`。
- 报告层对应 `src/presentation/`。
- 前端层对应 `src/app.py` 与 `src/web/`。
- `src/core/` 与 `config.yaml` 作为横向支撑，不作为单独业务层。

新增 docs/5分钟演示脚本.md：
演示逻辑：
传统选址痛点
→ 官方公共数据价值
→ 高德 POI/GIS 补充空间要素
→ 区县背景约束
→ 1km 网格统一评分
→ 便利店/轻餐饮差异化推荐
→ 地图洞察
→ 智能报告
```

### 验收命令

```bash
python scripts/run_pipeline.py
python scripts/run_pipeline.py --serve
```

### 实际实现说明

总控早期示例中的 `src/data_process.py`、`src/map_viz.py` 和 `src/report_generator.py` 不符合当前模块布局。实际入口分别为：

```text
src.pipeline.official.official_pipeline
src.presentation.map_viz
src.presentation.report_generator
```

默认运行不重新调用外部 API，保证比赛交付可重复；在线刷新和 DeepSeek 报告必须显式启用。
默认离线基线精确验收 3 个区县、790 个空间网格、60 个 POI 样本网格、41 个活跃网格和 19 个无活动网格。

---

# 4. 最终验收标准

项目最终必须能完成这条演示链路：

```text
打开 Streamlit
→ 项目总览
→ 数据底座说明
→ 进入网格推荐
→ 选择默认方案、已保存方案或新建自定义方案
→ 必要时设置六项权重和指标模板
→ 选择云岩/南明/观山湖或全部
→ 查看 Top 10 推荐网格
→ 打开地图洞察
→ 选择一个 grid_id
→ 生成选址报告
→ 下载 Markdown 报告
```

---

# 5. 历史执行回复格式

Step 0 到 Step 18 实施期间，每一步按这个格式回复；后续维护不再据此自动新增步骤：

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

---

# 6. 全项目禁止事项

任何一步都禁止：

1. 声称获取了全量高德 POI；
2. 绕过或规避 API 限制；
3. 把省级或市级就业数据硬拆到 1km 网格；
4. 做门牌号级推荐；
5. 写精准预测盈利；
6. 编造真实客流、真实租金、真实营收；
7. 把 demo 数据包装成真实官方数据；
8. 删除旧文件而不备份；
9. 大规模重构后不跑测试；
10. 只改前端、不保证数据链路可运行。

---

# 7. 已完成范围与后续路线

下表中的 P0 和 P1 已纳入 Step 0 到 Step 18 的当前实现。P2 和 P3 只是后续路线，不是 Step 19 或更高步骤，也不得写成当前已完成能力。

| 优先级 | 内容 |
|---|---|
| 已完成 P0 | 配置、高德客户端与缓存、网格生成、POI 样本统计、评分结果、网格推荐、自定义权重 |
| 已完成 P1 | 地图洞察、智能报告、区域对比、视觉样式 |
| 后续 P2 | 单点评估、报告导出 Word/PDF |
| 后续 P3 | 百度/腾讯 POI 备选、多源 POI 融合、H3 六边形、Location-Allocation 优化 |

最小可交付版本必须包含：

```text
数据底座说明
1km 网格评分结果
便利店 Top 10
轻餐饮 Top 10
地图展示
推荐解释
Markdown 报告
```

---

# 8. 当前仓库结构边界

完成 Step 18 后，仓库按职责重组：

- 当前配置与评分方案：`src/core/`
- 当前数据管线：`src/pipeline/`
- 当前指标与评分：`src/modeling/`
- 当前地图与报告：`src/presentation/`
- 当前工作台页面与视觉组件：`src/web/`
- v1 可运行归档：`src/legacy/v1/`

当前稳定入口保持为：

```powershell
python scripts/run_pipeline.py
streamlit run src/app.py
```

v1 使用独立配置、数据和输出目录，不参与当前默认入口。详细说明见 `docs/项目结构说明.md` 和 `docs/legacy/v1/README.md`。

Step 18 是当前执行计划终点。此后的工作属于维护、核验或另行批准的增强任务：

1. 不自动延伸为 Step 19。
2. 不把 P2/P3 路线写成当前能力。
3. 不新增并列的 v2.1、v3 或重复入口目录。
4. 新增功能继续放入现有职责包，并同步更新测试、说明文档和 `AGENTS.md` 记录。
5. 当前主线不得导入 `src/legacy/v1/`，旧版也不得导入当前业务包。

---

# 9. 参考资料

1. 高德开放平台 POI 2.0 高级 API 文档：  
   https://lbs.amap.com/api/webservice/guide/api-advanced/newpoisearch

2. 高德行政区划查询 API：  
   https://lbs.amap.com/api/webservice/guide/api/district

3. Streamlit 多页应用文档：  
   https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation

4. Streamlit `st.navigation` 文档：  
   https://docs.streamlit.io/develop/api-reference/navigation/st.navigation

5. 高德地图 JS API 2.0 文档：
   https://lbs.amap.com/api/javascript-api-v2/summary

6. Folium 官方文档：
   https://python-visualization.github.io/folium/

7. streamlit-folium GitHub：
   https://github.com/randyzwitch/streamlit-folium

---

# 10. 最终一句话

Step 0 到 Step 18 已完成。后续维护必须先读取真实仓库，再在现有职责边界内实施和验证；未经用户明确批准，不新增后续步骤或扩大当前能力口径。
