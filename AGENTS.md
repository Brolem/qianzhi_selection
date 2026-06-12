# AGENTS.md

## 适用范围

本文件适用于 `D:\Users\Desktop\GZAICp\qianzhi_selection` 工作目录及其子目录内的协作、开发、调试、文档整理和交付工作。

## 强制规则

1. 严禁使用用户已禁止的英文不确定表述。
2. 严禁对任何标识符进行大小写、格式或结构匹配猜测，包括但不限于键名、变量名、路径、字段名、配置项、JSON 路径、命令参数和编码结构。
3. 当不确定某个请求、配置、数据结构、变量名、JSON 路径、字段、路径或编码相关的具体表述时，必须优先读取相关文件，从测试脚本、抓包结果、日志、配置文件、源码、文档或实际输出中提取精确表述。
4. 若无法从现有文件中找到精确信息，必须向用户询问，由用户手动执行测试、抓包或检查来获取。
5. 除非用户明确特别允许，否则不得自行补全、推断或猜测任何内容。
6. 根目录总控文档约束项目目标、方法边界和步骤顺序；真实文件、字段、配置、接口响应、测试结果和运行环境决定具体实现。
7. 当总控文档中的示例路径、字段、命令或实现细节与真实仓库状态冲突时，不得机械执行，必须按实际情况调整。
8. 每次调整必须记录冲突内容、实际依据、实现选择和验证结果。
9. 未经实际验证的能力不得写成已完成，不得以形式上的命令通过替代真实数据验收。

## 功能变更维护规则

每次进行功能修改或功能新增时，必须同步更新本文件。

更新内容必须记录在下方“功能变更记录”中，至少包含：

1. 日期、XX时XX分。
2. 修改或新增的功能。
3. 实际改动的文件路径。
4. 依据的真实文件、日志、测试、配置或用户明确指令。
5. 已执行的验证命令或未验证原因。

如果只是阅读、分析、答疑、格式整理或未触及功能行为，可不新增功能变更记录；但如果修改影响代码行为、数据处理、页面展示、配置含义、报告输出、测试逻辑或交付流程，必须记录。

## 工作要求

1. 修改前先读取相关文件，确认真实结构和真实命名。
2. 修改时保持改动范围清晰，不顺手重构无关内容。
3. 修改后执行与改动范围匹配的验证。
4. 验证失败时必须记录失败命令、失败现象和下一步需要的信息。
5. 不得把未验证的功能描述为已完成或可用。

## 功能变更记录

### 2026-06-10 13:02

- 功能：执行 `黔址优选_Codex多步执行指令.md` Step 2，新增 v2 配置结构与配置读取 helper，同时保留 v1 legacy 配置键和旧模块兼容入口。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\config.yaml`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 2 配置统一实施计划；已读取 `黔址优选_Codex多步执行指令.md` Step 2、当前 `config.yaml`、`src\config.py`、`tests\test_two_stage_site_selection.py`、`tests\test_module_layout.py` 和配置引用扫描结果；用户已确认 v2 六项权重采用等权重，数值为 `0.1666666667`。
- 验证：已先新增 `tests\test_config.py` 并运行 `python -m unittest tests.test_config -v`，RED 阶段因缺少 `ensure_dirs`、`get_poi_categories`、`get_project_root`、`get_weights` 和 `project.name` 不匹配而失败；实现后再次运行 `python -m unittest tests.test_config -v`，结果为 6 个测试通过。已运行 Step 2 原文验收命令，输出包含六项 v2 权重的字典；已运行 `python -m unittest tests.test_module_layout -v`，结果为 4 个测试通过；已运行 `python -m unittest tests.test_two_stage_site_selection -v`，结果为 7 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 38 个测试通过；已运行 src 语法检查，输出 `syntax ok`；首次运行项目禁用词扫描命中本文件规则描述，已改为不直接写出该英文词，随后复查无输出。

### 2026-06-10 13:24

- 功能：执行 `黔址优选_Codex多步执行指令.md` Step 3，新增高德 Web 服务客户端、demo 模式和本地 JSON 缓存能力。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\amap_client.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_amap_client.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 3 执行计划；已读取 `黔址优选_Codex多步执行指令.md` Step 3、当前 `config.yaml`、`src\config.py`、`requirements.txt`、`tests\test_config.py` 和本文件真实内容；`config.yaml` 中真实缓存路径为 `data_paths.amap_cache_dir: "data/cache/amap"`。
- 验证：已先新增 `tests\test_amap_client.py` 并运行 `python -m unittest tests.test_amap_client -v`，RED 阶段因缺少 `src.amap_client` 模块而失败；实现 `src\amap_client.py` 后再次运行 `python -m unittest tests.test_amap_client -v`，结果为 6 个测试通过。首次 GREEN 前发现测试 patch 目标不对，导致请求返回 `INVALID_USER_KEY`，已改为 patch `src.amap_client.urlopen` 并捕获预期日志，复查通过。后续验收、回归、语法检查和禁用词扫描将在本轮最终验证中执行。

### 2026-06-10 17:00

- 功能：执行 `黔址优选_Codex多步执行指令.md` Step 4，在线调用高德行政区划 API 获取目标区县基础信息和区县级边界，并写出 Step 4 正式数据文件。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\district_builder.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_district_builder.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\target_districts.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\target_district_boundaries.geojson`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\cache\amap\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 4 在线获取目标区县边界与基础信息实施计划；已读取 `黔址优选_Codex多步执行指令.md` Step 4、`src\amap_client.py`、`src\config.py`、`config.yaml`、`AGENTS.md`；用户已明确本步必须调用 API 获取数据，且街道数据不作为核心评分对象。
- 验证：已先新增 `tests\test_district_builder.py` 并运行 `python -m unittest tests.test_district_builder -v`，RED 阶段因缺少 `src.district_builder` 模块而失败；实现后再次运行 `python -m unittest tests.test_district_builder -v`，结果为 4 个测试通过。已运行 `$env:AMAP_KEY = [Environment]::GetEnvironmentVariable('AMAP_KEY', 'User'); python src/district_builder.py`，生成 `data\processed\target_districts.csv` 和 `data\processed\target_district_boundaries.geojson`，输出 `boundary warnings: none`。已读取输出确认 `云岩区`、`南明区`、`观山湖区` 三个区县均为 `data_source=amap_api`、`has_boundary=True`，GeoJSON 为 `FeatureCollection`、`coord_system=GCJ-02`、包含 3 个 `Polygon` Feature，未生成 `outputs\results\district_boundary_warnings.md`。

### 2026-06-11 10:33

- 功能：执行 `黔址优选_Codex多步执行指令.md` Step 5，基于 Step 4 真实区县边界，在统一 `EPSG:32648` 投影格网上生成并裁剪 1000 米评价网格。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\grid_builder.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_grid_builder.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\candidate_grids.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\candidate_grids.geojson`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 5 生成 1km 评价网格实施计划；已读取 `黔址优选_Codex多步执行指令.md` Step 5、Step 4 两个真实输出、旧版 `src\selection\two_stage.py` 网格实现、当前空间库版本和配置；用户已确认固定增加 `data_source` 字段、使用统一格网后按区县裁剪、缺边界时仅生成一个中心点回退方格。
- 验证：已先新增 `tests\test_grid_builder.py` 并运行 `python -m unittest tests.test_grid_builder -v`，RED 阶段因缺少 `src.grid_builder` 模块而失败；实现后再次运行该命令，结果为 5 个测试通过。已运行 `python src\grid_builder.py`，生成两个网格输出，共 790 个网格，其中云岩区 136 个、南明区 273 个、观山湖区 381 个。已读取输出确认字段结构符合计划、网格 ID 无重复、面积均大于 0 且不超过 1 平方公里、790 个网格均为 `data_source=amap_boundary`；GeoJSON 标记 `coord_system=GCJ-02`，包含 746 个 `Polygon` 和 44 个 `MultiPolygon`。已运行 `python -m unittest tests.test_district_builder -v`，结果为 4 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 53 个测试通过；已运行递归 src AST 语法检查，输出 `syntax ok`；已验证三区网格越出对应区县边界的面积均为 0；项目规则扫描仅命中 Step 5 固定输出文件名。

### 2026-06-11 15:25

- 功能：执行 `黔址优选_Codex多步执行指令.md` Step 6，新增网格 POI 串行采集、空间分散抽样、分页、缓存、去重、统计、受限网络重试和摘要输出能力；使用用户级 `AMAP_KEY` 完成三区各 20 个网格、15 类 POI 的真实在线采集。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\poi_fetcher.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_poi_fetcher.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\grid_poi_raw.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\grid_poi_counts.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\cache\amap\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\poi_fetch_summary.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 6 网格 POI 采集与统计实施计划；已读取总控文档 Step 6、`config.yaml` 中 15 个真实 `poi_categories`、`src\amap_client.py`、`src\config.py`、Step 5 网格输出和现有测试；用户已确认默认每区 20 个网格、空间均匀分散抽样、每类最多 2 页且每页 25 条。
- 验证：已先新增 `tests\test_poi_fetcher.py` 并运行 `python -m unittest tests.test_poi_fetcher -v`，RED 阶段因缺少 `src.poi_fetcher` 模块而失败；实现后 7 个测试通过。真实采集期间两次出现外部 SSL 握手超时，已读取缓存确认已完成请求均为 `status=1`、`info=OK`，随后新增仅对无响应最多尝试 3 次的失败测试并完成 GREEN，高德明确错误响应仍立即失败。最终真实采集生成 3299 条 POI 明细和 60 条网格统计，云岩区、南明区、观山湖区各 20 个唯一网格，15 类计数字段完整，全部明细为 `source=amap_api`，同网格同类别的非空 `poi_id` 无重复；摘要明确为原型样本，并把缓存命中和重试统一记录为客户端查询调用次数，不误报为真实联网次数。已复用缓存再次运行 Step 6 验收命令，60 个网格全部完成并刷新三个正式输出；已运行 `python -m unittest discover -s tests -v`，结果为 61 个测试通过；已运行递归 src AST 语法检查，输出 `syntax ok`；已基于 `config.yaml` 真实区县和类别配置完成输出验收，结果为 `raw=3299 counts=60 districts=3 categories=15`；Step 6 新增代码的项目规则扫描无异常命中。

### 2026-06-11 17:00

- 功能：执行 Step 7 网格级指标工程，基于 60 个真实采集网格的关键词 POI 统计生成评分输入；新增全局 `log1p + Min-Max` 归一化、四项公共指标、便利店与轻餐饮各自的共生和竞争指标、全零网格审计标记及原子输出能力；同时将“总控规定目标与边界，真实仓库状态决定具体实现”固定为项目总原则。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\feature_engineering.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_feature_engineering.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\data\processed\grid_scoring_input.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\feature_engineering_report.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的 Step 7 网格级指标工程实施计划；已读取总控文档 Step 7、Step 8、`config.yaml`、`src\config.py`、Step 5 网格表、Step 6 POI 统计表和现有测试。总控示例中的宏观与就业文件路径不符合当前真实目录，实际文件位于 `data\processed\official\`，本步只在报告中说明其背景作用，不作为脚本依赖。总控只列一个共生指标和一个竞争指标，但同时定义了两种业态的不同组成字段；为保证后续便利店与轻餐饮评分具有真实差异，本步按用户确认拆分为四个业态专属字段。
- 验证：已先新增 `tests\test_feature_engineering.py` 并运行 `python -m unittest tests.test_feature_engineering -v`，RED 阶段因缺少 `src.feature_engineering` 模块而失败；实现后新增第二个输出替换失败的回归测试，确认旧实现会留下部分更新，再增加双文件回滚逻辑，最终定向测试 9 项通过。已运行 `python src\feature_engineering.py`，生成 60 行 `grid_scoring_input.csv` 和指标工程报告，云岩区、南明区、观山湖区各 20 行，网格标识无重复且与 `grid_poi_counts.csv` 集合完全一致；19 个全零网格均保留并标记为无 POI 活动；8 项指标无空值且全部位于 0-100；评分输入未包含官方宏观或就业字段。已运行 `python -m unittest discover -s tests -v`，结果为 76 个测试通过；已运行递归 src AST 语法检查，输出 `syntax ok`。

### 2026-06-12 11:25

- 功能：执行 Step 8 通用权重评分与推荐结果，新增社区便利店、轻餐饮两套默认均衡差异化评分方案，以及基于 `community_retail`、`food_service` 指标模板的自定义六维权重方案；实现竞争压力反向、全局与区县确定性排名、推荐等级、优势风险解释、区县汇总、独立自定义输出和三文件失败回滚。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\config.yaml`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\scoring_model.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_scoring_model.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\grid_stage_score_result.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\district_summary_result.csv`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\recommendation_summary.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\custom_profiles\custom_retail_01\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的 Step 8 通用权重评分与推荐结果实施计划；赛题 PDF 第 2 页明确要求模型支持用户自定义权重并适配不同业态；已读取 `config.yaml`、`src\config.py`、`src\feature_engineering.py`、`data\processed\grid_scoring_input.csv`、Step 8 测试和相关文档。真实输入为 60 行，三区各 20 行，其中 41 行有 POI 活动、19 行无活动；因此只对 41 行排名，未把全零网格的低竞争解释为推荐优势。赛题中的银行属于业态示例，当前数据未包含银行专属 POI 与指标，故未增加无数据支撑的固定银行方案。
- 验证：RED 阶段运行 `python -m unittest tests.test_config tests.test_scoring_model -v`，因缺少 `get_scoring_templates`、默认权重未更新和 `src.scoring_model` 不存在而失败；实现后定向测试 19 项通过。已运行 `python src\scoring_model.py` 生成默认三项输出，并运行完整自定义参数生成 `custom_retail_01` 独立三项输出；默认结果为 60 行、三区各 20 行，两类方案均有 41 个有效排名和 19 个空排名，活跃网格推荐等级均为推荐 9、谨慎推荐 16、暂不推荐 16；区县汇总为 3 行。旧版 `outputs\results\grid_stage\grid_stage_score_result.csv` 执行前后 SHA256 均为 `C7122B0C1555F83313753EB3F21C8B210B55138717A84307D6101CE21ECCDC6A`。已运行 `python -m unittest discover -s tests -v`，结果为 88 个测试通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误；项目规则扫描只命中 Step 5 已固定的历史输出文件名，禁止性能力词只出现在“禁止/不要”语境。

### 2026-06-12 12:19

- 功能：执行 Step 9 地图生成与自定义方案展示，原地升级 `src\visualization\map_viz.py` 为 v2 地图模块；新增默认与自定义评分方案字段映射、GCJ-02 到 WGS84 显示转换、790 个空间网格状态渲染、固定五档色阶、全局 Top 10 编号标记、悬停与点击详情、中心点回退和双 HTML 失败回滚；地图页新增独立评分方案选择器，并通过 `streamlit-folium` 动态显示默认或自定义方案。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\visualization\map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\requirements.txt`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\figures\convenience_grid_map.html`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\figures\light_food_grid_map.html`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的 Step 9 地图生成与自定义方案展示计划；已读取总控文档 Step 9、Step 8 默认与自定义评分结果、790 个真实网格 GeoJSON、现有地图模块、前端入口、模块布局测试和已安装 `streamlit-folium` 的真实函数签名。总控示例要求新增 `src\map_viz.py`，但仓库真实布局和测试明确禁止根目录重复入口，因此按项目总原则原地升级 `src\visualization\map_viz.py`。用户已确认采用完整空间底图、红金绿分级、Top 编号、简洁悬停加点击详情、显示阶段转 WGS84、两张默认 HTML、自定义方案动态地图和地图页独立选择器。
- 验证：先重写 Step 9 地图测试并扩展前端测试，运行 `python -m unittest tests.test_map_viz tests.test_app -v`，RED 阶段因缺少 `MapProfileSpec`、坐标转换、方案发现、通用地图和前端动态接口而失败；实现后定向测试 19 项通过。真实执行 `python -m src.visualization.map_viz` 生成两张默认 HTML；便利店、轻餐饮和 `custom_retail_01` 地图均核对为 730 个未采集网格、19 个无 POI 活动网格、41 个活跃网格和 10 个 Top 标记。浏览器已检查开放底图对齐、图例、色阶、Top 编号和点击弹窗；发现 Top 编号阻挡网格点击后新增失败测试并增加点击穿透样式，复查可点击到评分详情。Streamlit 地图页已显示两个默认方案和 `custom_retail_01` 自定义方案选项。已运行 `python -m unittest discover -s tests -v`，结果为 97 个测试通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误。
