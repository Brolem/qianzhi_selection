# v1 可运行归档

## 定位

该目录保存旧 OSM/GIS 与区域、网格两阶段评分实现，仅用于历史追溯和旧结果复现，不参与当前默认管线。

v1 源码读取独立配置：

```text
src/legacy/v1/config.yaml
```

旧数据和输出位于：

```text
data/legacy/v1/
outputs/legacy/v1/
```

## 命令

```powershell
python -m src.legacy.v1.osm.inventory
python -m src.legacy.v1.osm.pipeline --no-download
python -m src.legacy.v1.selection.two_stage --top-n 5 --grid-size-m 1000
python -m src.legacy.v1.visualization.map_viz
python -m src.legacy.v1.reporting.report_generator
streamlit run src/legacy/v1/app.py
```

官方背景处理如需按旧版入口运行：

```powershell
python -m src.legacy.v1.data.official_pipeline
```

## 边界

- v1 命令不会写入当前 `data/processed/` 或当前 `outputs/results/`。
- v1 不得导入当前业务包。
- 当前项目的一键运行和工作台不会调用 v1。
- 历史文档正文保留原始路径和命令，用于说明当时的仓库状态；实际运行以本说明中的命令为准。
