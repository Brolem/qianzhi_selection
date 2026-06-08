# AGENTS.md

## 适用范围

本文件适用于 `D:\Users\Desktop\GZAICp` 工作目录及其子目录内的所有协作、开发、调试、文档整理和交付工作。

## 强制规则

1. 严禁使用 `candidate` 等不确定表述。
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

### 2026-06-08 15:36

- 功能：新增本协作规则文件，并规定后续每次功能修改或新增时必须更新 `AGENT.MD`。
- 改动文件：`D:\Users\Desktop\GZAICp\AGENT.MD`。
- 依据：用户在当前会话中明确要求“写一个AGENT.MD，在每次做功能修改或新增时，更新AGENT.MD”，并提供反猜测协作规则。
- 验证：创建后读取 `D:\Users\Desktop\GZAICp\AGENT.MD` 确认内容写入。

- 功能：执行 `项目执行计划.md` Step 6 地图可视化，新增网格细筛结果 HTML 地图生成能力。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\requirements.txt`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\figures\convenience_grid_map.html`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\figures\light_food_grid_map.html`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 6 地图可视化实施计划；已读取 `outputs/results/grid_stage/grid_stage_score_result.csv` 和 `outputs/results/region_stage/region_stage_score_result.csv` 的真实字段名；首次运行 `python -m unittest tests.test_map_viz -v` 失败原因为 `ModuleNotFoundError: No module named 'src.map_viz'`。
- 验证：已运行 `python -m unittest tests.test_map_viz -v`，结果为 4 个测试通过；已运行 `python src\map_viz.py`，生成 `outputs\figures\convenience_grid_map.html` 和 `outputs\figures\light_food_grid_map.html`；已运行 `python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"`，输出 `syntax ok`；已运行 `python -m unittest discover -s tests -v`，结果为 18 个测试通过。

### 2026-06-08 16:58

- 功能：执行 `docs\项目执行计划.md` Step 7 Streamlit 页面整合，将 `src\app.py` 扩展为 8 页可演示 Web Demo，并接入地图 HTML 与模板报告展示。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 7 Streamlit 页面整合实施计划；已读取 `src\app.py`、`src\report_generator.py`、`AGENTS.md` 和 Step 7 依赖输出文件的真实路径；首次运行 `python -m unittest tests.test_app -v` 失败原因为 `ImportError: cannot import name 'business_columns' from 'src.app'`。
- 验证：已运行 `python -m unittest tests.test_app -v`，结果为 5 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 23 个测试通过；已运行 `python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').glob('*.py')]; print('syntax ok')"`，输出 `syntax ok`；已运行 `src\app.py` 禁用表述扫描，无匹配输出；已运行 `python -m streamlit run src/app.py --server.headless true --server.port 8507 --server.address 127.0.0.1`，日志显示 `URL: http://127.0.0.1:8507` 和 `Uvicorn server started on 127.0.0.1:8507`，随后已停止服务。

- 功能：执行 Step 8 结构整理与千问大模型报告生成接入；新增功能目录并保留旧入口；报告生成默认调用千问/DashScope OpenAI 兼容接口，模板报告作为显式兜底。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\data\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\osm\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\selection\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\visualization\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\reporting\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\requirements.txt`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_module_layout.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_report_generator.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\outputs\reports\grid_8316193_000003_社区便利店_选址报告.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“PLEASE IMPLEMENT THIS PLAN”中的 Step 8 结构整理与千问大模型报告实施计划；已读取 `docs\项目执行计划.md` Step 8、当前 `src\report_generator.py`、`src\app.py`、`requirements.txt` 和 `outputs\results\grid_stage\grid_stage_score_result.csv` 真实字段；千问接口依据用户提供计划中的官方文档链接与 OpenAI 兼容配置要求。
- 验证：已运行 `python -m unittest tests.test_module_layout -v`，结果为 2 个测试通过；已运行 `python -m unittest tests.test_report_generator -v`，结果为 4 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 29 个测试通过；已运行 `python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; print('syntax ok')"`，输出 `syntax ok`；已运行 `pip install -r requirements.txt`，安装 `openai` 依赖后 `python -c "import openai; print(openai.__version__)"` 输出 `2.41.0`；已运行 `python src\report_generator.py --template`，生成 `outputs\reports\grid_8316193_000003_社区便利店_选址报告.md`；已运行 `python src\report_generator.py`，因本机未设置 `DASHSCOPE_API_KEY` 明确报错；已运行 `python src\map_viz.py` 和 `python src\two_stage_site_selection.py --help` 验证旧入口可用；已运行 `python -m streamlit run src/app.py --server.headless true --server.port 8507 --server.address 127.0.0.1`，日志显示 `URL: http://127.0.0.1:8507` 和 `Uvicorn server started on 127.0.0.1:8507`，随后已停止服务。

### 2026-06-08 17:38

- 功能：按用户要求暂不配置千问 API Key，并将 `src` 根目录旧入口统一移动到 `src\entrypoints\`，使根目录仅保留应用入口、配置和功能目录。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\entrypoints\`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_module_layout.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_map_viz.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_osm_inventory.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_osm_guizhou_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_two_stage_site_selection.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“先不配置API，后续再配置。将旧入口删除或统一放入一个文件夹里”；已读取 `AGENTS.md`、`tests\test_module_layout.py` 和 `src\report_generator.py` 等根目录入口文件，确认这些根目录文件为兼容入口包装。
- 验证：本轮已先更新 `tests\test_module_layout.py` 作为结构整理测试；后续执行 `python -m unittest tests.test_module_layout -v` 时，沙箱外执行审批被当前用量限制拒绝，错误信息为 `You've hit your usage limit`，因此本轮最终测试、全量测试和语法检查未能执行。需要后续在本机运行 `python -m unittest tests.test_module_layout -v`、`python -m unittest discover -s tests -v` 和 `python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; print('syntax ok')"` 完成确认。

### 2026-06-08 21:05

- 功能：更新 Markdown 文档中的当前模块位置和手动执行入口路径，使文档匹配 `src\entrypoints\` 与功能分目录后的代码结构。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\技术路线草图.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确指令“因为更新了代码结构，所以更新各个markdown文档下的文件位置”；已运行 Markdown 路径扫描命令确认旧入口路径主要存在于 `README.md`、`docs\项目执行计划.md`、`docs\技术路线草图.md` 和 `AGENTS.md` 历史记录中；已读取相关 Markdown 文件内容后更新当前执行文档。
- 验证：已运行 `rg -n "src[/\\](data_process|official_pipeline|osm_inventory|osm_guizhou_pipeline|two_stage_site_selection|map_viz|report_generator)\.py|src/(data_process|official_pipeline|osm_inventory|osm_guizhou_pipeline|two_stage_site_selection|map_viz|report_generator)\.py|src\\(data_process|official_pipeline|osm_inventory|osm_guizhou_pipeline|two_stage_site_selection|map_viz|report_generator)\.py" -g "*.md"`，结果显示当前剩余命中仅位于 `AGENTS.md` 的历史记录；已运行 `rg -n "src/|src\\" README.md docs -g "*.md"`，确认 `README.md` 与 `docs\` 下当前路径已指向 `src\entrypoints\` 或功能分目录。

### 2026-06-08 21:11

- 功能：按用户已删除 `src\entrypoints\` 的当前结构，更新文档、页面提示和模块布局测试，使执行命令通过 `python -m src...` 指向功能模块。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\技术路线草图.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_module_layout.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确说明“我把entrypoints这个旧入口删掉了”；已运行 `Test-Path src\entrypoints` 确认结果为 `False`；已运行 `Get-ChildItem -Name src` 确认当前 `src` 下仅有 `data`、`osm`、`reporting`、`selection`、`visualization`、`app.py`、`config.py` 等真实路径；已运行入口函数扫描确认功能模块中存在 `main()` 或 `run_official_pipeline()`。
- 验证：已运行 `python src\selection\two_stage_site_selection.py --help`、`python src\visualization\map_viz.py`、`python src\reporting\report_generator.py --template`，均因包上下文缺失报 `ModuleNotFoundError: No module named 'src'`；随后已将当前执行命令改为 `python -m src...` 形式。已运行 `python -m src.selection.two_stage_site_selection --help`，正常输出帮助；已运行 `python -m src.visualization.map_viz`，生成两份地图 HTML；已运行 `python -m src.reporting.report_generator --template`，生成模板报告；已运行 `rg -n "entrypoints|python src[/\\](data|osm|selection|visualization|reporting)|src[/\\](data_process|official_pipeline|osm_inventory|osm_guizhou_pipeline|two_stage_site_selection|map_viz|report_generator)\.py" README.md docs tests src\app.py -g "*.md" -g "*.py"`，无输出；已运行 `python -m unittest tests.test_module_layout -v`，结果为 3 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 30 个测试通过；已运行 src 语法检查，输出 `syntax ok`。

### 2026-06-08 21:28

- 功能：在保留 `data`、`osm`、`selection`、`visualization`、`reporting` 功能分目录的前提下，重命名重复模块名并修复 import、页面提示和文档命令。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\data\preprocess.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\data\official_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\osm\inventory.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\osm\pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\selection\two_stage.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_module_layout.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_osm_inventory.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_osm_guizhou_pipeline.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_two_stage_site_selection.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\README.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\项目执行计划.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\docs\技术路线草图.md`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户明确要求“请先扫描项目结构和 import 依赖，再执行重命名和移动，避免移动文件后 import 报错”；已运行 `Get-ChildItem -Recurse -File src`、`rg -n "^(from|import) " src tests`、`Get-ChildItem -Recurse -File src\data`、旧模块名扫描命令，确认 `src\data` 下为 Python 代码且 import 依赖集中在 tests、`src\data\official_pipeline.py`、`src\selection\two_stage.py`、`README.md`、`docs\项目执行计划.md`、`docs\技术路线草图.md`、`src\app.py`。
- 验证：已先修改 `tests\test_module_layout.py` 并运行 `python -m unittest tests.test_module_layout -v`，RED 阶段因 `src.data.preprocess`、`src.osm.inventory`、`src.osm.pipeline`、`src.selection.two_stage` 不存在而失败；移动和修复 import 后再次运行 `python -m unittest tests.test_module_layout -v`，结果为 4 个测试通过；已运行 `python -m unittest discover -s tests -v`，结果为 31 个测试通过；已运行 src 语法检查，输出 `syntax ok`；已运行 `python -m src.data.official_pipeline`、`python -m src.osm.inventory`、`python -m src.osm.pipeline --help`、`python -m src.selection.two_stage --help`、`python -m src.visualization.map_viz`、`python -m src.reporting.report_generator --template`，均成功；已运行旧模块 import 与旧命令扫描，当前剩余命中仅为 `tests\test_module_layout.py` 中检查旧文件不存在的断言。

### 2026-06-08 21:47

- 功能：修复 `streamlit run src/app.py` 以脚本路径运行时无法导入 `src.reporting.report_generator` 的问题。
- 改动文件：`D:\Users\Desktop\GZAICp\qianzhi_selection\src\app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\tests\test_app.py`；`D:\Users\Desktop\GZAICp\qianzhi_selection\AGENTS.md`。
- 依据：用户截图显示 `ModuleNotFoundError: No module named 'src'`，报错位置为 `src\app.py` 第 19 行 `from src.reporting.report_generator import generate_site_report`；已读取 `src\app.py` 和 `tests\test_app.py`，确认根因为 Streamlit 以 `src/app.py` 脚本路径运行时项目根目录未稳定出现在 `sys.path`。
- 验证：已新增 `tests.test_app.AppHelperTests.test_app_script_imports_when_streamlit_runs_file_path`，RED 阶段复现 `ModuleNotFoundError: No module named 'src'`；修复后运行该测试通过；已运行 `python -m unittest tests.test_app -v`，结果为 6 个测试通过；已运行 src 语法检查，输出 `syntax ok`；已运行 `python -m streamlit run src/app.py --server.headless true --server.port 8507 --server.address 127.0.0.1`，日志显示 `URL: http://127.0.0.1:8507` 和 `Uvicorn server started on 127.0.0.1:8507`，无 `ModuleNotFoundError`，随后已停止服务；已运行 `python -m unittest discover -s tests -v`，结果为 32 个测试通过。
