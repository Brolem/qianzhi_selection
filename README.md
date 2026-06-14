# 黔址优选：贵阳市典型区县社区商业智能选址原型

## 项目定位

本项目面向贵州人工智能创业大赛公共数据赛道，以云岩区、南明区和观山湖区为试点，构建“区县背景约束下的网格级多因子商业选址推荐模型”。

当前主线使用官方宏观经济与就业数据说明贵州省级市场背景，使用高德行政区划、POI 样本和 1km 评价网格形成社区便利店、轻餐饮及自定义权重方案的相对推荐结果。

系统不做门牌号级推荐，不承诺具体盈利，不生成真实租金、客流、营收预测。

## 当前能力

- 3 个目标区县和 790 个空间评价网格。
- 三区各 20 个、共 60 个 POI 样本网格。
- 15 类 POI 统计和 8 项网格指标。
- 社区便利店、轻餐饮默认评分方案。
- 六维非负权重自定义评分和方案保存。
- 高德 JS API 地图主链及 Folium 兼容回退。
- 结构化 DeepSeek 智能报告和规则模板报告。
- 七页 Streamlit 选址工作台。
- 默认离线、按需联网的一键运行脚本。

## 项目结构

```text
qianzhi_selection/
├── config.yaml                    # 当前主线配置
├── scripts/
│   └── run_pipeline.py            # 当前一键运行入口
├── src/
│   ├── app.py                     # 当前 Streamlit 入口
│   ├── core/                      # 配置与评分方案目录
│   ├── pipeline/                  # 官方数据、高德、区县、网格、POI
│   │   └── official/
│   ├── modeling/                  # 指标工程、评分、自定义权重
│   ├── presentation/              # 地图与智能报告
│   ├── web/
│   │   ├── pages/
│   │   └── ui/
│   └── legacy/
│       └── v1/                    # 可独立运行的旧 OSM/两阶段实现
├── data/
│   ├── raw/official/              # 当前官方原始数据
│   ├── cache/amap/                # 本机高德缓存，不纳入 Git
│   ├── processed/                 # 当前主线处理数据
│   └── legacy/v1/                 # 旧版原始与处理数据
├── outputs/
│   ├── results/                   # 当前评分结果
│   ├── reports/                   # 当前报告
│   ├── figures/                   # 当前地图
│   └── legacy/v1/                 # 旧版结果、报告与地图
├── tests/
│   ├── core/
│   ├── pipeline/
│   ├── modeling/
│   ├── presentation/
│   ├── web/
│   ├── integration/
│   └── legacy/v1/
└── docs/
    ├── history/
    └── legacy/v1/
```

详细职责和数据生命周期见 [项目结构说明](docs/项目结构说明.md)。旧版使用方式见 [v1 说明](docs/legacy/v1/README.md)。

## 安装

已验证运行环境为 Python `3.13.12`。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 当前主线运行

默认离线复现不会调用高德 Web 服务或 DeepSeek：

```powershell
python scripts/run_pipeline.py
```

可选参数：

```powershell
# 重新处理六个官方 Excel
python scripts/run_pipeline.py --refresh-official

# 在线刷新三区边界、空间网格和 60 个 POI 样本网格
python scripts/run_pipeline.py --refresh-amap

# 使用 DeepSeek 生成两类 Top 1 报告
python scripts/run_pipeline.py --with-llm

# 验收成功后使用 0.0.0.0:8501 启动工作台
python scripts/run_pipeline.py --serve
```

直接启动工作台：

```powershell
streamlit run src/app.py
```

单独运行当前模块：

```powershell
python -m src.pipeline.official.official_pipeline
python -m src.pipeline.district_builder
python -m src.pipeline.grid_builder
python -m src.pipeline.poi_fetcher
python -m src.modeling.feature_engineering
python -m src.modeling.scoring_model
python -m src.presentation.map_viz
python -m src.presentation.report_generator --profile convenience --template
```

## 环境变量

```powershell
[Environment]::SetEnvironmentVariable("AMAP_KEY", "<高德Web服务Key>", "User")
[Environment]::SetEnvironmentVariable("AMAP_JS_KEY", "<高德JS API Key>", "User")
[Environment]::SetEnvironmentVariable("AMAP_JS_SECURITY_CODE", "<高德JS安全密钥>", "User")
[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", "<DeepSeek API Key>", "User")
```

- `AMAP_KEY` 仅在刷新高德数据时必须配置。
- `DEEPSEEK_API_KEY` 仅在生成大模型报告时必须配置。
- 高德 JS 凭据缺失时使用 Folium 兼容地图。
- 密钥只从环境变量读取，不写入配置、源码、日志或文档。

## 工作台页面

1. 项目总览
2. 数据底座
3. 区域对比
4. 网格推荐
5. 地图洞察
6. 智能报告
7. 项目说明

网格推荐页支持默认方案、已保存方案和新建自定义方案。地图与报告页面读取同一评分方案目录。

## 当前主线输入

```text
data/processed/target_districts.csv
data/processed/target_district_boundaries.geojson
data/processed/grid_poi_raw.csv
data/processed/grid_poi_counts.csv
data/processed/official/macro_clean.csv
data/processed/official/employment_clean.csv
```

## 当前主线输出

```text
data/processed/grid_scoring_input.csv
outputs/results/grid_stage_score_result.csv
outputs/results/district_summary_result.csv
outputs/results/recommendation_summary.md
outputs/results/profile_metadata.json
outputs/results/pipeline_run_summary.md
outputs/figures/convenience_grid_map.html
outputs/figures/light_food_grid_map.html
outputs/reports/<profile_id>/<grid_id>_选址报告.md
```

运行输出默认不纳入 Git。

## 验证

```powershell
python -m unittest discover -s tests -v
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('src').rglob('*.py')]; ast.parse(pathlib.Path('scripts/run_pipeline.py').read_text(encoding='utf-8')); print('syntax ok')"
git diff --check
```

## 数据边界

- POI 数据是 60 个样本网格的统一关键词查询结果，适合相对比较，不代表完整设施总量。
- 19 个无 POI 活动网格保留用于审计，不进入推荐排名。
- 官方宏观经济与就业数据只用于贵州省级背景说明，不进入网格评分。
- 自定义权重只改变现有六维指标贡献；新增正式业态仍需补充对应数据与指标模板。
- v1 已隔离到 `src/legacy/v1/`、`data/legacy/v1/`、`outputs/legacy/v1/` 和 `tests/legacy/v1/`，不参与当前默认入口。
