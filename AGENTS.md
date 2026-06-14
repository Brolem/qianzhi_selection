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

### 2026-06-12 13:27

- 功能：执行 Step 10 DeepSeek 智能选址报告迁移，新增默认与自定义评分方案共享目录、结构化六维权重元数据、四文件原子评分输出、v2 十一章节报告、`deepseek-v4-pro` 非思考模式优先调用和限定 `deepseek-v4-flash` 回退；智能报告页改为独立方案选择、41 个活跃网格过滤、按钮触发、会话缓存和模板兜底。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\config.yaml`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\profile_catalog.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\scoring_model.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\reporting\report_generator.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\visualization\map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_profile_catalog.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_scoring_model.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_report_generator.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的 Step 10 实施计划；已读取总控文档 Step 10、Step 8 正式与自定义评分字段、现有千问报告模块、前端报告页、赛题 PDF 三页全文、官方宏观与就业数据真实地域编码和 DeepSeek 官方思考模式、模型及错误码文档。真实官方数据均为 `520000` 贵州省级，因此只进入报告的数据适用边界，不参与网格评分；`employment_customer_proxy` 明确保持为 POI 构成的就业/办公客群代理。用户已确认 Pro 优先、仅暂时性错误回退 Flash、支持默认与自定义方案、仅 41 个活跃网格、点击后调用和页面显示实际模型。
- 验证：共享方案和评分元数据测试先因缺少 `src.profile_catalog`、四文件事务和元数据输出而形成 RED；实现后相关测试通过。报告测试先因缺少 DeepSeek 接口、v2 字段和十一章节校验而形成 RED；实现后覆盖 Pro 非思考参数、404/429/5xx/连接/超时回退、400/401/402/403/422 不回退、无效正文、无活动网格、模板报告和原子导出。已重新运行默认评分与 `custom_retail_01` 自定义评分，生成两份 `profile_metadata.json`；已重新生成两张默认地图。已用用户级 `DEEPSEEK_API_KEY` 真实执行一次 `python -m src.reporting.report_generator --profile convenience --grid-id grid_520103_000078`，生成 `outputs\reports\convenience\grid_520103_000078_选址报告.md`，核对 11 个规定章节全部存在。已运行 `python -m unittest discover -s tests -v`，结果为 107 个测试通过。

### 2026-06-12 16:54

- 功能：执行 Step 11 Streamlit 多页工作台改造，将单文件入口拆分为八个独立页面模块；正式入口使用 `st.Page` 与 `st.navigation`，保留 sidebar radio 兼容回退；项目总览、数据底座、选址分析、区域对比和网格推荐读取真实 v2 输出，地图洞察与智能报告迁移并保留 Step 9–10 行为。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app_legacy.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_workbench_pages.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准并要求实施的 Step 11 计划；已读取总控文档 Step 11–17、当前 `src\app.py`、`tests\test_app.py`、Step 8–10 真实输出和评分方案目录；运行环境确认 Streamlit 为 `1.58.0`，同时存在 `st.Page` 与 `st.navigation`。真实 v2 范围为 3 个区县、790 个空间网格、60 个 POI 样本网格、41 个活跃评分网格和 3 个有效评分方案。
- 验证：先修改 `tests\test_app.py` 并新增 `tests\test_workbench_pages.py`，运行 `python -m unittest tests.test_app tests.test_workbench_pages -v`，RED 阶段因缺少 `PAGE_REGISTRATIONS` 和 `src.pages` 失败；实现后 19 项测试通过。已运行地图、报告和工作台定向回归共 37 项测试并通过；真实数据只读检查确认项目总览、六项数据底座、三区汇总及三套方案 Top 10 均可读取。已运行 `python -m unittest discover -s tests -v`，结果为 115 项测试通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误；项目规则扫描仅命中 Step 5 固定历史文件名。浏览器已逐页检查八个导航项，旧版“区域粗筛”和“网格细筛”不再出现在正式导航；地图页成功渲染地图 iframe，报告页显示评分方案、活跃网格和生成按钮且未发起 DeepSeek 请求；浏览器控制台无错误。

### 2026-06-12 22:09

- 功能：执行 Step 13–15 页面去重与自定义评分改造，删除职责重复的独立“选址分析”页，将导航调整为七页；首页新增五类 POI 主题摘要和活跃网格区县平均得分哑铃图；区域对比新增三组原始 POI 数量图；网格推荐统一支持默认方案、已保存方案、新建自定义方案、六项百分比权重预算、确定性归一、内存即时评分、全局 Top 10、区县 Top 5、六维分解及四文件正式保存。标题栏调整为桌面端居中 24px，并收紧窄屏字号和间距。用户试用横向客群设施图后要求恢复，最终保留纵向分组柱状图并将横轴类别标签固定为横排；区域图表调整为“便利店与餐饮、交通设施”上方并排，“客群与商业设施”下方通栏，仅保留一处区县图例。首页 15 类密集热力图经三种真实数据视觉对比后，按用户选择替换为社区零售、餐饮消费、生活客群、商业办公和交通配套五类主题摘要；重叠箱线图改为两类默认方案的区县平均分哑铃图，并将真实数据展示区间调整为 20–40。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\interactive_scoring.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\overview.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\district_compare.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\grid_recommendation.py`；删除 `D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\site_analysis.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\ui\workbench.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_interactive_scoring.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_workbench_pages.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_workbench_ui.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\requirements.txt`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\初赛方案_新版.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的 Step 13–15 页面去重与自定义评分实施计划，以及用户对客群设施图恢复原方向的最新指令；已读取真实 `config.yaml` 权重与模板、`data\processed\grid_poi_counts.csv`、`data\processed\grid_scoring_input.csv`、`outputs\results\grid_stage_score_result.csv`、`src\scoring_model.py`、`src\profile_catalog.py`、现有页面模块和测试。实际数据为 3 个区县、15 类 POI、790 个空间网格、60 个评分样本网格和 41 个活跃网格；前端自定义评分直接复用 `ScoringProfile`、`score_profile()` 和现有四文件事务，不另建评分逻辑。
- 验证：先新增权重预算、即时评分、方案保存、七页导航、首页图表和区域图表测试并确认 RED；实现后定向测试通过。已运行 `python -m unittest discover -s tests -v`，结果为 134 项测试通过；递归 src AST 语法检查输出 `syntax ok`；真实数据检查确认首页五类主题摘要为 3 个区县×5 个主题共 15 行，得分分布只使用 41 个活跃网格的两类得分，区域对比为 3 个区县的原始 POI 聚合；100% 交通权重预览与默认便利店 Top 10 名单发生真实变化。浏览器已确认七个导航项、桌面端标题居中、首页两张 Altair 图、首页均分横轴为 20–40、区域三组图使用上二下一布局且类别标签横排、默认及新建自定义方案、全零权重阻止计算、100% 交通权重即时更新排名、六维指标图和无横向溢出；未保存浏览器验收方案，未发起 DeepSeek 请求。`git diff --check` 无格式错误；禁止性能力词只出现在“禁止/不要”语境，项目规则扫描仅命中历史固定输出文件名。

### 2026-06-13 09:24

- 功能：继续优化工作台信息密度与隐私展示。首页两张图统一高度和说明文字边界，左侧图获得略宽空间；两图均使用共享的页面级横向图例，保证区县与评分方案的色块、文字大小和间距一致，右侧明确显示“社区便利店、轻餐饮”。区县平均得分改为分组水平条形图，避免数字与图形重叠。数据底座移除本机绝对文件路径列。删除独立结果目录 `outputs\results\custom_profiles\custom_retail_01\`，保留新建自定义评分方案能力。网格推荐详情参考 GitHub Streamlit 看板的紧凑摘要与进度指标模式，将三张嵌套指标卡改为单一决策摘要，并将六维指标改为带基准轨道、分段颜色和末端数值的子弹图。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\data_foundation.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\grid_recommendation.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\overview.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\ui\workbench.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_workbench_pages.py`；删除未纳入 Git 跟踪的 `D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\results\custom_profiles\custom_retail_01\`。
- 依据：用户对首页图例、数据路径隐私、已保存自定义方案、网格详情布局和首页左右对齐的明确反馈；已读取真实页面实现、评分方案动态发现逻辑和真实输出目录。删除前确认该方案由运行时目录动态发现，代码、地图和报告均未直接依赖该目录；删除后 `available_profile_specs()` 只返回两套默认方案。视觉实现参考 GitHub 上 `dataprofessor/population-dashboard`、`streamlit/demo-seattle-weather` 和 `amrrs/streamlit_metric_dashboard` 的紧凑多栏、单层摘要和图形化指标做法，未引入新依赖。
- 验证：已按测试先行新增路径列移除、共享图例、首页等高图表、决策摘要和三层子弹图规格测试并确认失败；实现后定向测试通过。浏览器已确认首页两套图例顶部横排、色块与文字尺寸一致，左侧图不再被等宽布局压缩，右侧显示“社区便利店、轻餐饮”，得分数字不重叠；数据底座不再显示本机路径；网格摘要显示 `83.03 / 100`、`全局 #1` 和推荐徽标，六维图显示灰色基准轨道、分段颜色及末端数值。已确认 `custom_retail_01` 目录不存在，动态方案列表只包含“默认｜社区便利店”和“默认｜轻餐饮”。已运行 `python -m unittest discover -s tests -v`，结果为 136 项测试通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误。

### 2026-06-13 12:38

- 功能：将地图主链从 Folium 开放底图迁移为高德地图 JS API 2.0，直接使用现有 GCJ-02 区县边界、790 个网格和中心点；保留 Folium 兼容回退。地图页新增“使用兼容地图”开关，并继续支持默认及有效自定义评分方案、五档评分色阶、数据覆盖状态、全局 Top 10、悬停摘要和点击详情。默认地图导出根据高德 JS 凭据是否存在选择高德 HTML 或 Folium HTML，继续使用双文件原子替换和失败回滚。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\config.yaml`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\visualization\map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\map_insight.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_config.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\初赛方案_新版.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确批准的“高德 JS API 地图迁移与页面适配计划”，并确认用户级 `AMAP_JS_KEY` 与 `AMAP_JS_SECURITY_CODE` 已配置；已读取现有地图模块、地图页、配置、评分方案目录、790 网格 GeoJSON、测试和高德地图 JS API 2.0 官方文档。高德 Web 服务继续使用 `AMAP_KEY`，浏览器地图使用独立的 JS Key 与安全密钥；敏感值只从环境变量读取。
- 验证：测试先因缺少地图配置读取、高德凭据读取、GCJ-02 数据准备、高德 HTML 构建和页面主链接口形成 RED；实现后定向回归通过。差异审查发现 Folium 回退中心点函数缺少返回值，已新增精确失败测试并修复，定向地图、配置和应用测试共 43 项通过。已用用户级 JS 凭据执行 `python -m src.visualization.map_viz`，两张默认 HTML 均使用高德 Loader；两类地图均核对为 790 个网格、730 个未采集网格、19 个无 POI 活动网格、41 个活跃网格和 10 个 Top 标记。浏览器已在 `http://localhost:8503/map-insight` 验证高德底图、GCJ-02 网格、Top 10、图例和高德版权正常渲染，未出现高德鉴权或域名错误；切换“使用兼容地图”后 Folium 图层与 Top 10 正常显示，再切回高德地图成功。已运行完整单元测试，结果为 144 项通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误；Git 跟踪文件中的高德 JS Key 与安全密钥明文命中数均为 0；项目规则扫描只命中 Step 5 已固定的历史输出文件名。

### 2026-06-13 12:53

- 功能：精简地图评分图例，只显示 `0-20`、`20-40`、`40-60` 三个区间；地图评分计算和高于 60 分网格的实际着色保持不变。将“全局 Top 10”的图例符号由方框改为带数字 `1` 的圆形标记，与地图上的编号圆标保持一致；高德地图与 Folium 兼容地图同步更新。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\visualization\map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户对地图图例的明确视觉调整指令和截图；已读取高德 HTML 图例、Folium 图例及现有地图测试的真实结构。
- 验证：已先增加高德与 Folium 图例测试，确认旧实现因仍包含 `60-80`、`80-100` 且使用方框而失败；实现后两项测试通过。已重启 `8503` Streamlit 进程并在浏览器核对高德主链和 Folium 回退，两套图例均只显示三个评分区间，Top 10 均显示圆圈数字 `1`，最后恢复为高德地图。已运行完整单元测试，结果为 145 项通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误。

### 2026-06-13 13:04

- 功能：完成 Step 17 智能报告页面正式验收与文档收口。保留 Step 10 已确认的 11 章报告结构；将总控文档中的旧模块路径、两类固定业态入口和旧章节表述更新为当前共享评分方案、有效排名网格、DeepSeek 调用策略、模板兜底、会话缓存及 Markdown 下载实现。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确确认保留 Step 10 现行结构，并要求大模型 API 不可用时必须明确告知、待配置完成后再执行；已读取 `src\pages\report_center.py`、`src\reporting\report_generator.py`、共享评分方案目录、现有报告与应用测试、真实报告输出及总控 Step 17。
- 验证：先检查用户级 `DEEPSEEK_API_KEY`，确认已配置；随后进行一次最小真实调用，`deepseek-v4-pro` 非思考模式成功返回 1657 字符的完整报告，未触发 Flash 回退。定向运行报告、应用和评分方案目录测试共 30 项通过；真实数据核对为 2 套当前有效默认方案，每套均有 41 个活跃排名网格，报告章节数为 11。浏览器已在 `http://localhost:8503/report-center` 确认方案选择、网格选择、排名/区县/网格/得分标签、生成按钮和中性空状态正常；本次浏览器验收未再次调用 API。已运行完整单元测试，结果为 145 项通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误；Git 跟踪文件中的 `DEEPSEEK_API_KEY` 明文命中数为 0；限制性能力词扫描均处于禁止、边界或历史说明语境。

### 2026-06-13 13:27

- 功能：优化智能报告页的等待反馈与正文排版。点击“生成智能报告”后使用 Streamlit 状态模块显示正在生成、完成或失败，提示生成通常需要数秒且避免重复点击；会话缓存命中时不重复显示生成状态、不重复调用模型。报告 Markdown 放入独立稳定容器，仅缩小报告章节标题、正文和列表字号，保持报告面板标题及模型状态提示原有层级。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\pages\report_center.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\ui\workbench.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_workbench_ui.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确要求报告生成等待期间增加加载或提示模块，并要求报告结果正文在当前页面中适当缩小；已读取真实报告页、工作台视觉系统、现有应用测试及 Streamlit `1.58.0` 的 `st.status`、`st.container(key=...)` 接口签名。实现继续使用现有 DeepSeek 调用、错误提示、模板兜底和会话缓存。
- 验证：先新增生成中、完成、失败、缓存不重复显示以及报告正文独立容器的断言，确认旧实现因缺少状态模块和专用正文容器而失败；实现后定向测试通过。已运行应用、视觉系统和报告生成定向测试共 34 项并通过；已运行完整单元测试，结果为 145 项通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误。浏览器已在 `http://localhost:8501/report-center` 确认报告参数、唯一生成按钮、中性空状态及报告专用 CSS 已加载；本次浏览器核验未点击生成按钮，未新增 DeepSeek API 调用。已清理重复 Streamlit 进程，最终仅保留 PID `25552` 监听 `0.0.0.0:8501`。

### 2026-06-13 13:49

- 功能：将 DeepSeek 智能报告升级为“结构化分析 JSON + Python 校验与 Markdown 渲染”。模型通过 JSON Output 生成 11 个章节的分析素材、证据字段、经营建议依据和四项质量检查，不直接写入报告数值；程序校验证据白名单、竞争指标方向、无依据内容和模型自行写入的数值，再从真实评分记录写入分数、排名、权重、坐标与数据边界并渲染固定 11 章报告。JSON 空响应只对同一模型重试一次，内容质量失败不通过 Flash 回退掩盖。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\reporting\report_generator.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_report_generator.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\推荐项目方案.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户要求将网页检索形成的高质量提示词方案集成到项目；已读取当前报告生成器、报告测试和真实报告输出，并核对 DeepSeek 官方 JSON Output、思考模式和上下文缓存文档。现有真实报告曾把交通指标扩展为路网密度、给出无数据支持的具体落位建议，并存在竞争方向表述风险，因此新增指标字典、逐章证据白名单、限制规则和程序化事实写入。
- 验证：先新增 JSON Output 请求、固定提示词、证据字段、质量检查、模型数值禁写、无依据结论、程序化 Markdown 和空响应同模型重试测试，确认旧实现缺少对应接口并按 Markdown 校验而失败；实现后报告、应用入口和评分方案目录定向测试共 34 项通过。第一次真实 Pro 调用发现 `business_fit` 合理引用 `profile.weights` 但契约未列出，已补失败测试并增加逐章证据字段清单；第二次真实调用发现限制章节中的“具体铺位”否定说明被误判，已补失败测试并仅对限制章节放行边界声明；第三次真实调用成功使用 `deepseek-v4-pro` 返回结构化分析并生成 11 章报告，未触发 Flash 回退。已通过 CLI 正式生成 `outputs\reports\convenience\grid_520103_000078_选址报告.md`，核对为 11 个二级章节，明确写出交通指标仅由公交站、地铁站和停车场构成，并同时展示原始竞争压力与反向低竞争得分；“具体铺位”仅出现在需现场核实的限制说明中。已运行 `python -m unittest discover -s tests`，结果为 149 项测试通过；递归 src AST 语法检查输出 `syntax ok`；`git diff --check` 无格式错误。

### 2026-06-14 09:55

- 功能：执行 Step 18 一键运行与最终交付收口。新增默认离线复现入口，使用仓库已跟踪的 60 个真实 POI 样本网格依次重建指标工程、两类默认评分、两张地图和两类 Top 1 模板报告；新增官方数据、高德在线刷新、DeepSeek 报告和 Streamlit 启动的显式参数；增加输入预检、阶段失败停止、离线与在线两套验收口径、8501 端口保护和脱敏运行摘要。同步锁定当前验证依赖，修正官方数据报告旧版筛选口径，并补齐最终交付清单与 5 分钟演示脚本。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\scripts\run_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_run_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\data\official_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_module_layout.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\requirements.txt`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\最终交付清单.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\5分钟演示脚本.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\文档索引.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\技术路线草图.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\黔址优选_Codex多步执行指令.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户批准的 Step 18 实施计划；已读取总控 Step 18、当前模块入口、配置、真实 CSV 字段、输出目录、环境变量使用点和现有测试。总控早期示例中的 `src\data_process.py`、`src\map_viz.py` 和 `src\report_generator.py` 与仓库真实布局冲突，实际采用 `src.data.official_pipeline`、`src.visualization.map_viz` 和 `src.reporting.report_generator`。当前仓库跟踪 60 网格真实样本但不跟踪高德完整缓存和运行输出，因此默认采用离线稳定复现，在线刷新必须显式启用。
- 验证：先新增一键流程 10 项测试并运行，因缺少 `scripts.run_pipeline` 形成 RED；实现后补充运行摘要仓库相对路径回归测试，最终 Step 18 测试共 11 项通过。官方报告口径测试先因仍包含旧版筛选主线而失败，修正后通过。已两次真实执行 `python scripts/run_pipeline.py`，最近一次生成 3 个区县、790 个空间网格、60 个 POI 样本网格、41 个活跃网格和 19 个无活动网格的验收摘要，地图与报告路径均为仓库相对路径。已执行 `python scripts/run_pipeline.py --with-llm`，两类 Top 1 报告均通过真实 DeepSeek 链路生成，未使用模板兜底。已通过 `--serve` 在唯一的 `0.0.0.0:8501` 实例启动工作台；浏览器核对七页导航、首页 `3 / 790 / 15 / 41` 指标、网格推荐 Top 10 与六维分解、高德地图 iframe 及 `0-60` 图例、智能报告参数页和项目说明。已运行完整单元测试，结果为 161 项通过；递归 src 与一键脚本 AST 语法检查输出 `syntax ok`；`python -m pip check` 输出 `No broken requirements found.`；`git diff --check` 无格式错误；四项 API 环境变量明文未进入 Git 跟踪文件。
