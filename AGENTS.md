# AGENTS.md

## 适用范围

本文件适用于 `D:\Users\Desktop\GZAICp\qianzhi_selection` 工作目录及其子目录内的协作、开发、调试、文档整理和交付工作。

## 强制规则

1. 严禁使用用户已禁止的英文不确定表述。
2. 严禁对任何标识符进行大小写、格式或结构匹配猜测，包括但不限于键名、变量名、路径、字段名、配置项、JSON 路径、命令参数和编码结构。
3. 当不确定某个请求、配置、数据结构、变量名、JSON 路径、字段、路径或编码相关的具体表述时，必须优先读取相关文件，从测试脚本、抓包结果、日志、配置文件、源码、文档或实际输出中提取精确表述。
4. 若无法从现有文件中找到精确信息，必须向用户询问，由用户手动执行测试、抓包或检查来获取。
5. 除非用户明确特别允许，否则不得自行补全、推断或猜测任何内容。

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
