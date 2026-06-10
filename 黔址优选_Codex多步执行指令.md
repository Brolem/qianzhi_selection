# 黔址优选：项目方法调整与前端改造 Codex 多步执行指令

> 版本：v2.0  
> 目标：将项目从旧版“Geofabrik/OSM 两阶段选址推荐”调整为“区县背景约束下的网格级多因子商业选址推荐模型”，并将前端改造成类似百度地图慧眼的商业选址工作台。  
> 当前推荐技术栈：Python + Streamlit + 高德 Web 服务 API + Folium / streamlit-folium + Markdown 报告生成。

---

## 0. 方法总口径

后续项目文档、README、前端页面、答辩材料统一使用以下口径：

> 本项目以贵阳市典型区县为试点，将官方宏观经济指标和就业数据作为区域市场背景，将高德 POI 与地理空间数据作为网格级特征来源，构建“区县背景约束下的网格级多因子商业选址推荐模型”。系统不进行门牌号级推荐，而是输出适合社区便利店和轻餐饮业态的优先考察网格，并提供地图洞察、指标解释和智能选址报告。

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
| 官方宏观经济指标 | 赛事官方数据 | 贵州/贵阳整体市场背景、消费能力、区域发展说明 |
| 官方就业数据 | 赛事官方数据 | 就业客群、收入水平、稳定消费需求背景 |
| POI 数据 | 高德 POI API，百度/腾讯作为备选 | 网格级商业、交通、生活配套、竞品、共生业态统计 |
| 行政区划 | 高德行政区划 API | 区县信息、区县边界、区县中心点 |
| 地图展示 | Folium / streamlit-folium / Streamlit components | 推荐网格地图、热力图、点位提示 |
| 示例数据 | data/demo/ | 无 AMAP_KEY 时保证项目可演示 |

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
   - 官方宏观经济指标和就业数据：用于贵州/贵阳市场背景、消费能力、就业客群说明；
   - 高德 POI API：用于网格级 POI 样本统计；
   - 高德行政区划 API：用于区县信息和边界；
   - 示例数据：无 AMAP_KEY 时使用 data/demo/ 下的离线示例数据。
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

建议分 18 步让 Codex 逐步完成：

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
| Step 13 | 选址分析主页面 | 完成核心交互页面 | 必须 |
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

1. 建议创建新分支：
   git checkout -b refactor-amap-grid-workbench

2. 检查项目目录：
   - data/
   - src/
   - outputs/
   - docs/
   - tests/

3. 检查 src/ 下所有 Python 文件语法：
   python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"

4. 检查现有核心输出是否存在：
   - data/processed/macro_clean.csv
   - data/processed/employment_clean.csv
   - outputs/results/字段说明表.csv
   - outputs/results/数据识别与合理性报告.md

5. 新增 docs/迁移前项目状态.md，说明：
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
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"
```

### 预期产出

```text
docs/迁移前项目状态.md
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

请完善 config.yaml，并新增 src/config.py。

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
   - processed_dir
   - results_dir
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

src/config.py 实现：
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
python -c "from src.config import load_config, ensure_dirs, get_weights; cfg=load_config(); ensure_dirs(cfg); print(get_weights(cfg, 'convenience'))"
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

新增 src/amap_client.py。

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
   - 加入 sleep，默认每次请求间隔 0.2-0.5 秒；
   - 不做并发请求；
   - 不绕过 API 限制。

5. 错误处理：
   - key 缺失：返回 None 或抛出清晰异常，由上层转 demo 数据；
   - 请求失败：记录日志，不中断全部流程；
   - 返回为空：保存空结果。

6. 新增 tests/test_amap_client.py：
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
python -m unittest tests/test_amap_client.py -v
python -c "from src.amap_client import AmapClient; c=AmapClient(); print('client ok')"
```

---

## Step 4：目标区县边界与基础信息

### 目标

获取云岩、南明、观山湖等区县的 adcode、center、boundary。

### 给 Codex 的指令

```text
任务 4：目标区县边界与基础信息。

新增 src/district_builder.py。

输入：
- config.yaml 中的 target_districts
- AMAP_KEY，如果没有则使用 data/demo/target_districts_demo.csv 和 data/demo/target_district_boundaries_demo.geojson

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
5. 无 AMAP_KEY 时：
   - 使用 demo 文件；
   - 如果 demo 文件不存在，生成 docs/需要准备的数据.md，提示用户准备 demo 区县文件。

禁止：
- 不要用街道边界作为核心，因为高德街道边界不稳定/不可得；
- 不要编造真实边界；
- 不要强行让流程崩溃。
```

### 验收命令

```bash
python src/district_builder.py
```

---

## Step 5：生成 1km 候选评价网格

### 目标

在目标区县内生成网格，作为真正评分对象。

### 给 Codex 的指令

```text
任务 5：生成 1km 候选评价网格。

新增 src/grid_builder.py。

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

技术要求：
1. 必须使用投影坐标系生成 1000m x 1000m 网格，不要直接在经纬度上按度切分。
2. 生成后再转回 WGS84 或当前地图使用坐标。
3. 只保留与区县边界相交的网格。
4. 对网格面积过小的边缘网格可以保留，但需要 area_km2 字段。
5. 如果没有真实边界，则用区县 center 生成演示网格，并在 data_source 字段标记 demo。

禁止：
- 不要生成门牌号；
- 不要在经纬度坐标下直接按 0.01 度当作 1km；
- 不要对全贵州生成网格。
```

### 验收命令

```bash
python src/grid_builder.py
```

---

## Step 6：网格级 POI 查询与统计

### 目标

对每个 1km 网格中心点做周边 POI 查询，得到模型输入表。

### 给 Codex 的指令

```text
任务 6：网格级 POI 查询与统计。

新增 src/poi_fetcher.py。

输入：
- data/processed/candidate_grids.csv
- config.yaml 中 poi_categories
- config.yaml 中 default_radius_m，默认 500
- AMAP_KEY；若无 key，则使用 data/demo/grid_poi_counts_demo.csv

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
1. 对每个 grid centroid 和每个 POI 类别调用周边搜索。
2. 半径默认 500m。
3. 每类最多抓取前若干页，默认不要超过官方限制。
4. 所有响应走 AmapClient 缓存。
5. 需要去重：同一个 poi_id 在同一 grid/category 下不要重复统计。
6. 如果同一 POI 在多个类别下重复出现，可以暂时允许，但报告中说明 POI 分类可能存在重叠。
7. 输出 outputs/results/poi_fetch_summary.md：
   - 查询区县数
   - 网格数
   - 类别数
   - API 模式或 demo 模式
   - 每类 POI 数量
   - 数据限制说明

禁止：
- 不要声称抓取全量 POI；
- 不要并发压接口；
- 不要绕过分页限制。
```

### 验收命令

```bash
python src/poi_fetcher.py
```

---

## Step 7：网格级指标工程

### 目标

把 POI 数量转成可解释指标。

### 给 Codex 的指令

```text
任务 7：网格级指标工程。

新增或重构 src/feature_engineering.py。

输入：
- data/processed/grid_poi_counts.csv
- data/processed/candidate_grids.csv
- data/processed/macro_clean.csv
- data/processed/employment_clean.csv

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

4. synergy_score
便利店共生：residential、school、hospital、bus_stop、supermarket；
轻餐饮共生：office、school、mall、bus_stop、cafe、tea。

5. competition_pressure
便利店竞争：convenience_store_count、supermarket_count；
轻餐饮竞争：restaurant_count、fast_food_count、snack_count、cafe_count、tea_count。
这是负向指标，后续评分要反向处理。

6. business_atmosphere
由 mall、restaurant、cafe、tea、supermarket 等体现商业活跃度。

要求：
1. 所有指标归一化到 0-100。
2. 缺失值填 0。
3. 输出字段必须包含：
   grid_id, district_name, centroid_lon, centroid_lat,
   traffic_accessibility,
   consumption_potential,
   employment_customer_proxy,
   synergy_score,
   competition_pressure,
   business_atmosphere

4. 生成 outputs/results/feature_engineering_report.md，解释每个指标如何构造。

禁止：
- 不要把省级就业数据分配到网格；
- 不要伪造真实客流；
- 不要使用没有来源的字段。
```

### 验收命令

```bash
python src/feature_engineering.py
```

---

## Step 8：网格评分与推荐结果

### 目标

输出最终用于前端展示的推荐表。

### 给 Codex 的指令

```text
任务 8：网格评分与推荐结果。

新增或重构 src/scoring_model.py。

输入：
- data/processed/grid_scoring_input.csv
- config.yaml 中便利店和轻餐饮权重

输出：
1. outputs/results/grid_stage_score_result.csv
2. outputs/results/district_summary_result.csv
3. outputs/results/recommendation_summary.md

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

3. 分别计算：
   - convenience_score
   - light_food_score

4. 输出推荐：
   - 全局便利店 Top 10
   - 全局轻餐饮 Top 10
   - 各区县便利店 Top 5
   - 各区县轻餐饮 Top 5

5. 为每个网格生成：
   - main_advantage
   - main_risk
   - recommendation_level：推荐 / 谨慎推荐 / 暂不推荐

6. district_summary_result.csv 包含：
   - district_name
   - grid_count
   - avg_convenience_score
   - avg_light_food_score
   - top_convenience_grid_id
   - top_light_food_grid_id
   - poi_total_count

禁止：
- 不要输出“该门店一定盈利”；
- 不要输出门牌号；
- 不要用区县整体分数替代网格分数。
```

### 验收命令

```bash
python src/scoring_model.py
```

---

## Step 9：地图生成模块

### 目标

生成可嵌入前端的网格热力图和推荐点地图。

### 给 Codex 的指令

```text
任务 9：地图生成模块。

新增 src/map_viz.py。

输入：
- outputs/results/grid_stage_score_result.csv
- data/processed/candidate_grids.geojson

输出：
1. outputs/figures/convenience_grid_map.html
2. outputs/figures/light_food_grid_map.html
3. outputs/figures/poi_overview_map.html，可选

功能要求：
1. 使用 Folium 生成交互地图。
2. 如果 candidate_grids.geojson 存在，展示网格面；
   如果不存在，则展示中心点。
3. 地图支持：
   - 便利店评分热力；
   - 轻餐饮评分热力；
   - Top N 推荐网格高亮；
   - tooltip 显示 grid_id、district_name、score、main_advantage、main_risk。
4. 如果安装 streamlit-folium，则 app.py 中直接嵌入；
   如果没有，则用 components.html 嵌入静态 html。

禁止：
- 不要依赖必须联网才能打开的商业地图 key；
- 不要强制使用高德 JS API；
- 不要在地图上显示真实门牌号推荐。
```

### 验收命令

```bash
python src/map_viz.py
```

---

## Step 10：选址报告生成模块

### 目标

用模板或大模型生成可解释选址报告。

### 给 Codex 的指令

```text
任务 10：选址报告生成模块。

新增或重构 src/report_generator.py。

输入：
- outputs/results/grid_stage_score_result.csv
- data/processed/grid_scoring_input.csv
- 官方数据背景报告

输出：
- outputs/reports/{grid_id}_{business_type}_site_report.md

实现函数：
1. load_grid_results()
2. generate_site_report(grid_id, business_type)
3. export_report(grid_id, business_type, output_path)

报告结构：
一、候选网格基本信息
二、适配业态判断
三、交通可达性分析
四、消费潜力分析
五、就业/办公客群代理分析
六、共生业态分析
七、竞争压力分析
八、主要优势
九、主要风险
十、经营建议
十一、数据来源与限制说明

要求：
- 默认用规则模板生成；
- 如果配置了 LLM_API_KEY，可作为可选增强；
- 所有结论必须来自输入字段；
- 缺失数据要明确写“当前未接入”。

禁止：
- 不要编造租金；
- 不要编造客流；
- 不要编造营收；
- 不要写“已完成真实盈利预测”。
```

### 验收命令

```bash
python src/report_generator.py
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
3. 选址分析
4. 区域对比
5. 网格推荐
6. 地图洞察
7. 智能报告
8. 项目说明

建议目录：
src/app.py 作为入口；
src/pages/
  01_overview.py
  02_data_foundation.py
  03_site_analysis.py
  04_district_compare.py
  05_grid_recommendation.py
  06_map_insight.py
  07_report_center.py
  08_project_notes.py

若不想拆文件，也可以先在 app.py 中用函数组织：
render_overview()
render_data_foundation()
render_site_analysis()
...

禁止：
- 不要改动评分模型；
- 不要把所有页面堆在一个长页面；
- 不要删除旧 app.py，可先备份为 src/app_legacy.py。
```

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
   在“选址分析”页使用：
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

### 验收命令

```bash
streamlit run src/app.py
```

---

## Step 13：实现“选址分析”主页面

### 目标

做出最像百度慧眼截图的核心页面。

### 给 Codex 的指令

```text
任务 13：实现“选址分析”主页面。

页面结构：

Step 1：选择应用场景
使用卡片按钮：
- 智能推荐
- 区域评估
- 单点评估

其中第一版必须实现“智能推荐”；
区域评估和单点评估可以先做页面占位，但不要写假功能。

Step 2：设置分析参数
表单字段：
- 业态：便利店 / 轻餐饮
- 目标区县：云岩区 / 南明区 / 观山湖区 / 花溪区 / 白云区 / 全部
- 网格大小：1km，只读显示
- POI 半径：500m / 800m / 1000m
- 权重方案：默认便利店 / 默认轻餐饮 / 自定义

Step 3：查看推荐结果
左侧：
- 推荐网格 Top 10 表格
右侧：
- 地图展示
下方：
- 指标分解图

Step 4：生成报告
- 选择 grid_id
- 点击生成报告
- 展示 Markdown 报告
- 支持下载 Markdown

要求：
- 所有数据从 outputs/results/grid_stage_score_result.csv 读取；
- 如果文件不存在，提示先运行：
  python src/scoring_model.py
- 不要在页面中虚构结果。
```

### 验收重点

```text
选择业态 → 选择区县 → 出 Top 10 → 看地图 → 生成报告
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

---

## Step 15：实现“网格推荐”页面

### 目标

展示最终推荐结果，是整个项目最核心的前端页面。

### 给 Codex 的指令

```text
任务 15：实现“网格推荐”页面。

输入：
- outputs/results/grid_stage_score_result.csv

页面必须包含：

1. 全局便利店 Top 10
字段：
- grid_id
- district_name
- convenience_score
- traffic_accessibility
- consumption_potential
- synergy_score
- competition_pressure
- main_advantage
- main_risk

2. 全局轻餐饮 Top 10
字段：
- grid_id
- district_name
- light_food_score
- traffic_accessibility
- employment_customer_proxy
- synergy_score
- competition_pressure
- main_advantage
- main_risk

3. 各区县 Top 5
用户选择区县后展示：
- 便利店 Top 5
- 轻餐饮 Top 5

4. 指标分解
用户选择一个 grid_id 后，展示雷达图或横向条形图：
- traffic_accessibility
- consumption_potential
- employment_customer_proxy
- synergy_score
- competition_pressure
- business_atmosphere

禁止：
- 不要只展示总分；
- 必须展示优势和风险；
- 不要写门牌号推荐。
```

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
或由 src/map_viz.py 动态生成。

页面功能：
1. 选择业态：
   - 便利店
   - 轻餐饮

2. 选择区县：
   - 全部
   - 云岩区
   - 南明区
   - 观山湖区
   - 花溪区
   - 白云区

3. 展示地图：
   - 推荐网格中心点或网格面；
   - 评分颜色；
   - Top N 高亮；
   - tooltip 显示 grid_id、区县、得分、优势、风险。

4. 如果地图 HTML 不存在：
   显示提示：
   请先运行 python src/map_viz.py

禁止：
- 不要接入必须联网才能显示的商业地图底图；
- 不要显示门牌号级结论；
- 不要强依赖高德 JS Key。
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
- src/report_generator.py

页面流程：
1. 选择业态：
   - 便利店
   - 轻餐饮

2. 选择 grid_id：
   下拉框显示 grid_id + district_name + score。

3. 点击生成报告。

4. 页面展示 Markdown 报告。

5. 支持下载：
   - Markdown 文件

报告必须包含：
一、候选网格基本信息
二、适配业态判断
三、交通可达性分析
四、消费潜力分析
五、就业/办公客群代理分析
六、共生业态分析
七、竞争压力分析
八、主要优势
九、主要风险
十、经营建议
十一、数据来源与限制说明

禁止：
- 不要编造真实租金；
- 不要编造真实客流；
- 不要编造真实营收。
```

---

## Step 18：一键运行脚本和最终验收

### 目标

让项目能复现，方便交付和演示。

### 给 Codex 的指令

```text
任务 18：一键运行脚本和最终验收。

新增 scripts/run_pipeline.py 或 run_pipeline.bat。

一键流程：
1. python src/data_process.py
2. python src/district_builder.py
3. python src/grid_builder.py
4. python src/poi_fetcher.py
5. python src/feature_engineering.py
6. python src/scoring_model.py
7. python src/map_viz.py
8. python src/report_generator.py

更新 README.md：
- 环境安装
- AMAP_KEY 配置
- 无 AMAP_KEY 时 demo 模式
- 一键运行命令
- Streamlit 启动命令
- 输出文件说明
- 当前限制

新增 docs/最终交付清单.md：
- 数据文件
- 结果文件
- 地图文件
- 报告文件
- 前端页面
- 演示步骤

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
streamlit run src/app.py
```

---

# 4. 最终验收标准

项目最终必须能完成这条演示链路：

```text
打开 Streamlit
→ 项目总览
→ 数据底座说明
→ 进入选址分析
→ 选择智能推荐
→ 选择便利店/轻餐饮
→ 选择云岩/南明/观山湖或全部
→ 查看 Top 10 推荐网格
→ 打开地图洞察
→ 选择一个 grid_id
→ 生成选址报告
→ 下载 Markdown 报告
```

---

# 5. 每步完成后的 Codex 回复格式

每一步完成后，让 Codex 必须按这个格式回复：

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

# 7. 推荐优先级

如果时间不够，优先完成：

| 优先级 | 内容 |
|---|---|
| P0 | 配置文件、高德 API demo 模式、网格生成、POI 统计、评分结果、Streamlit 选址分析页 |
| P1 | 地图洞察、智能报告、区域对比、视觉样式 |
| P2 | 自定义权重、单点评估、报告导出 Word/PDF |
| P3 | 百度/腾讯 POI 备选、多源 POI 融合、H3 六边形、Location-Allocation 优化 |

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

# 8. 参考资料

1. 高德开放平台 POI 2.0 高级 API 文档：  
   https://lbs.amap.com/api/webservice/guide/api-advanced/newpoisearch

2. 高德行政区划查询 API：  
   https://lbs.amap.com/api/webservice/guide/api/district

3. Streamlit 多页应用文档：  
   https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation

4. Streamlit `st.navigation` 文档：  
   https://docs.streamlit.io/develop/api-reference/navigation/st.navigation

5. Folium 官方文档：  
   https://python-visualization.github.io/folium/

6. streamlit-folium GitHub：  
   https://github.com/randyzwitch/streamlit-folium

---

# 9. 最终一句话

后续让 Codex 执行时，不要一次性丢全部内容；应该按 Step 0 → Step 1 → Step 2 的顺序逐步推进，每一步验收通过后再继续。

