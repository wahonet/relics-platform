# 不可移动文物数字档案平台

Your know bro，在这个仓库里，你会看到大量的vibe-coding产物，我就一产品经理。

面向 **第四次全国文物普查** 的县/区级 WebGIS 数字档案平台模板。
把一个县/区的四普原始资料（文物档案 DOCX、外业日志 Excel、行政边界 SHP、DEM、三维模型）放进来，
运行一条命令即可生成结构化数据与交互式三维地图档案。
（产品经理思路是好的，下面的人（指glm5.1）执行乱了）

模板仓库自带**完全虚构**的最小 demo 数据（`演示县 · 示范街道`，15 条文物，坐标位于 120.0–120.2°E / 30.0–30.2°N 矩形范围内），clone 下来 `setup → run_pipeline → start_platform` 三步即可跑通完整流程，再按本文档替换成你自己的数据。（脱密需要）

---

## 功能概览

- **三维 WebGIS** — 基于 CesiumJS，支持卫星/街道底图、本地 DEM 地形、符号化点位、行政边界渲染。
- **档案详情** — 每处文物的基本信息、全部照片、全部图纸、简介、三维模型、四普档案 PDF。
- **多维度统计** — ECharts 仪表盘：类别 / 年代 / 级别 / 乡镇 / 普查类型 / 所有权 / 行业 / 现状 / 影响因素九维钻取，点击图表即叠加筛选。
- **外业普查路线** — 从现场照片 EXIF 还原每日普查轨迹，支持日期叠加、点位照片弹窗。
- **工作日志查看** — 外业日志 Excel → 分日 PDF，支持台账模糊匹配与一键联动地图。
- **村村达分析** — 按村界染色展示"已到达 / 未到达"，并给出未到达村清单。
- **AI 知识库问答** — 基于整个文物库 + 工作日志的大模型问答，支持流式输出；回答里 `📍` 可飞到文物、`📋` 可打开当天日志。
- **配置即平台** — 县名、中心点、边界、投影、API Key 全部在 `config.yaml` 一处维护；前端不写死。
- **功能自动开关** — `features.*: auto` 可根据 `data/` 下子目录是否为空，自动隐藏对应功能按钮。

---

## 快速开始（三步）

### 1. 初始化

双击 `setup.bat`：

- 检测并安装 Python 依赖（Python 3.10+）
- 创建 `data/input/` 与 `data/output/` 目录骨架
- 从 `config.example.yaml` 生成 `config.yaml`
- 打印项目状态

> 若系统没装 Python，可把 [Windows embeddable 便携版 Python](https://www.python.org/downloads/windows/) 解压到 `./python/` 目录，脚本会自动使用。

### 2. 放入数据，改一改 config.yaml

**编辑 `config.yaml`**，至少要改：

| 字段 | 说明 |
|---|---|
| `project.name` / `project.full_name` | 县/区名称、平台标题 |
| `geo.center` / `geo.bounds` | 初始视角 + 外接矩形（决定 DEM 裁剪、瓦片缓存范围） |
| `geo.boundaries.projection` / `central_meridian` / `is_gcj02` | SHP 的投影信息，详见下文 |
| `administrative.county_name` / `townships` | 县名与乡镇顺序 |
| `api.siliconflow.key` 等 | AI 大模型 API Key（推荐用环境变量） |

**放入原始数据**：

| 目录 | 内容 | 必需 |
|---|---|---|
| `data/input/01_archives/` | 四普文物档案 DOCX（可按乡镇子目录组织，如 `01示范街道/xxx.docx`） | 是 |
| `data/input/02_worklogs/` | 外业工作日志 Excel + `外业工作台账.xlsx` | 可选 |
| `data/input/03_boundaries/` | 县/镇/村 Shapefile 或 GeoJSON | 建议 |
| `data/input/04_dem/` | ASTER GDEM v2 GeoTIFF（`ASTGTM2_N*E*_dem.tif`） | 可选 |
| `data/input/05_models_3d/` | 三维模型 3D Tiles（按文物名分子目录） | 可选 |

### 3. 跑数据管线，启动平台

```
双击 run_pipeline.bat      # 数据管线：DOCX → Markdown → CSV/JSON/GeoJSON / 照片 / 图纸 / PDF / 边界
双击 start_platform.bat    # 启动 WebGIS，默认浏览器自动打开 http://127.0.0.1:8000
```

---

## 目录结构

```
relics-platform/
├── config.yaml                ← 项目唯一入口配置（由 setup.bat 从 example 拷贝生成）
├── config.example.yaml        ← 配置模板，升级时对照合并
├── .gitignore                 ← 已忽略 config.yaml / data/ / .env / *.key
│
├── setup.bat                  ← 初始化向导（装依赖、建目录、生成 config.yaml）
├── run_pipeline.bat           ← 数据管线入口
├── start_platform.bat         ← 启动 WebGIS 服务
│
├── data/                      ← 用户数据区（不纳入 Git）
│   ├── input/                 ← 原始资料
│   │   ├── 01_archives/       ← 档案 DOCX
│   │   ├── 02_worklogs/       ← 工作日志 Excel
│   │   ├── 03_boundaries/     ← 行政边界
│   │   ├── 04_dem/            ← DEM GeoTIFF
│   │   └── 05_models_3d/      ← 三维模型 3D Tiles
│   └── output/                ← 管线产物
│       ├── markdown/          ← step01：DOCX 转成的结构化 Markdown
│       ├── dataset/           ← step02：CSV / JSON / GeoJSON 数据集
│       ├── photos/            ← step03：档案内嵌的文物照片
│       ├── drawings/          ← step04：档案内嵌的图纸
│       ├── worklog_pdf/       ← step05：每日外业日志 PDF
│       ├── boundaries/        ← step06：WGS-84 统一化后的边界 GeoJSON
│       └── logs/              ← 各脚本运行日志
│
└── platform/                  ← 平台代码（升级时可整体覆盖此目录）
    ├── webgis/                ← FastAPI 后端 + Cesium 前端
    │   ├── main.py
    │   ├── serve.py           ← 启动入口（读 config.yaml，自动开浏览器）
    │   ├── data_loader.py     ← 启动时把所有数据一次性载入内存
    │   ├── terrain_provider.py← 本地 DEM → Cesium 地形瓦片
    │   ├── routers/           ← API：relics / stats / chat / admin / worklog / survey_routes
    │   ├── static/js/         ← 前端脚本
    │   ├── templates/         ← index / login / model-viewer / pdf-viewer
    │   └── requirements.txt
    ├── scripts/               ← 6 步数据管线
    │   ├── run_pipeline.py
    │   ├── step01_convert_docs.py      ← DOCX → 结构化 Markdown（LLM）
    │   ├── step02_build_dataset.py     ← Markdown → CSV/JSON/GeoJSON（坐标统一）
    │   ├── step03_extract_photos.py    ← 解包文物照片
    │   ├── step04_extract_drawings.py  ← 解包文物图纸
    │   ├── step05_convert_worklogs.py  ← Excel 日志 → PDF
    │   ├── step06_prepare_boundaries.py← Shapefile → WGS-84 GeoJSON
    │   └── _common.py                  ← 配置加载、坐标变换、路径管理
    ├── tools/
    │   └── download_tiles.py  ← 按 bounds 预下载离线瓦片
    ├── assets/                ← 图标等平台自带资源
    └── docs/                  ← 使用文档
```

---

## 数据管线详解

`run_pipeline.bat` 本质上是：

```
python platform\scripts\run_pipeline.py [options]
```

| Step | 脚本 | 必需输入 | 产物 | 说明 |
|---|---|---|---|---|
| 01 | step01_convert_docs | `01_archives/*.docx` | `output/markdown/*.md` | 用大模型把 DOCX 规范化成 Markdown，并抽出各字段列表 |
| 02 | step02_build_dataset | step01 产物 | `dataset/relics.{csv,json}`、`polygons.geojson`、`index.json` | 统一坐标系到 WGS-84（含 GCJ-02 → WGS-84）、三维模型匹配、风险打分 |
| 03 | step03_extract_photos | `01_archives/*.docx` + step02 | `output/photos/`、`photos_index.json` | 按"图纸在前、照片随后"的约定从 DOCX 抽图 |
| 04 | step04_extract_drawings | 同上 | `output/drawings/`、`drawings_index.json` | 同上，图纸永远排在 DOCX 最前面 |
| 05 | step05_convert_worklogs | `02_worklogs/*.xlsx`（可选） | `output/worklog_pdf/YYYYMMDD.pdf` | 排版成 A4 多页 PDF，供日志查看器嵌入 |
| 06 | step06_prepare_boundaries | `03_boundaries/*`（可选） | `output/boundaries/{county,townships,villages}.geojson` | 支持 Shapefile / GeoJSON，自动反投影到 WGS-84 |

### 管线高级用法

```bat
:: 列出所有可用步骤
python platform\scripts\run_pipeline.py --list

:: 只跑某些步骤
run_pipeline.bat --only 02
run_pipeline.bat --from 03 --to 05

:: 跳过某步（已验证可重复跑的脚本都支持断点续跑）
run_pipeline.bat --skip 01

:: 只打印将要执行的步骤，不真正运行
run_pipeline.bat --dry-run
```

可选步骤（worklog、boundaries、dem、3d）若对应 input 目录为空会**自动跳过**，不会中止管线。

---

## 关键配置说明

### 坐标系三连（`geo.source_crs` / `geo.boundaries`）

这是全平台最容易踩坑的地方。

**`geo.source_crs`** 指档案里文物点位的坐标系：

| 取值 | 含义 |
|---|---|
| `wgs84` | 国际标准，野外 GPS 直接读到的就是这个 |
| `gcj02` | 国测局"火星坐标"，高德地图/部分国产 GIS 导出的坐标 |
| `cgcs2000` | 国家大地 2000，与 WGS-84 差亚米级，按 wgs84 处理 |

**`geo.boundaries.projection`** 指 SHP 的投影：

| 取值 | 含义 |
|---|---|
| `none` / `wgs84` / `cgcs2000` | 已经是经纬度，无需反投影 |
| `gauss_kruger` | 高斯-克吕格平面坐标（国内测绘成果最常见），需同时填 `central_meridian` |
| `gcj02` | SHP 本身是 GCJ-02 经纬度（少见） |

**`geo.boundaries.is_gcj02`** 是个专门为"国内四普下发的镇界"开的补丁：

> 某些四普下发的行政边界 SHP，是在 GCJ-02 经纬度基础上再做的高斯投影。
> 此时 `projection: gauss_kruger` 反投影完得到的是 GCJ-02，而不是 WGS-84。
> 如果和文物点位（WGS-84）叠图时发现**整体系统性偏移约 500 米**，把 `is_gcj02` 设为 `true`，`step06` 会在反投影后再做一次 GCJ-02 → WGS-84 修正。

常见中央经线参考：

| 省份 | 山东 | 江苏 | 安徽 | 河南 | 湖北 | 四川 |
|---|---|---|---|---|---|---|
| `central_meridian` | 117 | 120 | 117 | 114 | 111 | 105 |

### 功能开关（`features.*`）

```yaml
features:
  enable_3d_model: auto       # 三维模型查看器
  enable_worklog:  auto       # 工作日志
  enable_dem:      auto       # 本地地形
  enable_ai_chat:  true       # AI 知识库
```

- `auto` — 后端启动时检测对应 `data/` 目录是否为空，为空就让前端隐藏这个功能按钮
- `true` — 强制开启（若数据缺失会在对应页面报错）
- `false` — 强制关闭

### 敏感信息（API Key）

`config.yaml` 里任何 `"${ENV_NAME}"` 形式的值都会在程序启动时从环境变量读取：

```yaml
api:
  siliconflow:
    key: "${SILICONFLOW_KEY}"
  cesium_ion:
    token: "${CESIUM_ION_TOKEN}"
```

推荐通过环境变量注入，避免把 Key 写进会被 commit 的文件：

```cmd
setx SILICONFLOW_KEY "sk-xxxxxxxxxxxx"
setx CESIUM_ION_TOKEN "eyJhbGciOi..."
```

`.gitignore` 已默认忽略 `.env` / `.env.*` / `*.key` / `config.yaml` / `data/`，可以放心提交代码。

---

## AI 问答模块

前端聊天面板对接的是后端 `/api/chat` 流式接口。

- **服务端配置** — `config.yaml → api.siliconflow`，支持 SiliconFlow / OpenAI 兼容 API（DeepSeek、GLM、Kimi 等均可）。
- **上下文构造** — 启动时 `data_loader` 把全部文物 + 全部日志预烘焙成一段 system prompt，和用户问题一起送给模型。参数在 `top_k_relics / top_k_worklog / history_turns / temperature` 里调。
- **地图联动** — 回答里出现 `[[显示文字|fly:ARCHIVE_CODE]]` / `[[显示文字|log:YYYY-MM-DD]]` / `[[显示文字|t:乡镇&l:级别]]` 会被渲染成可点击链接，点击即触发地图飞行/日志/筛选。

如果模型回答漂移、上下文超长，可把 `top_k_*` 适当调小。

---

## 离线瓦片（可选）

想让 WebGIS 在弱网或无网环境下依旧能看底图：

```cmd
python platform\tools\download_tiles.py
```

脚本会根据 `config.yaml → geo.bounds` 覆盖的范围，预下载所有层级瓦片到 `data/output/tile_cache/`。后端的 `/tiles/{provider}/{z}/{x}/{y}` 路由优先命中缓存。

---

## 常见问题

**Q：文物点位集体偏到了边界外面几百米？**
A：99% 是坐标系问题。
① 先看 `geo.source_crs` 和 `geo.boundaries` 两处设置是否和你的数据源匹配；
② 国内四普下发的镇界大概率要开 `is_gcj02: true`，见上文；
③ 边界修改后需要重跑 `run_pipeline.bat --only 06`。

**Q：启动提示 `ModuleNotFoundError: platform.webgis` ？**
A：Python 内置了 `platform` 标准库模块，会和项目目录重名。请用 `start_platform.bat`（内部调的是 `python platform\webgis\serve.py` 绝对路径），不要手写 `uvicorn platform.webgis.main:app`。

**Q：`[Errno 10048] 端口被占用`？**
A：上一次服务没彻底退出。`taskkill /F /IM python.exe`，或在 `config.yaml → server.port` 换一个端口。

**Q：AI 问答总报 401 / 余额不足？**
A：`SILICONFLOW_KEY` 没生效。先 `echo %SILICONFLOW_KEY%` 确认，然后**重开**一个 cmd 或重开 IDE（环境变量是进程启动时读取的）。

**Q：demo 跑起来是好的，但替换成自己县的数据后管线失败？**
A：最常见是 DOCX 目录命名不规范。约定：`data/input/01_archives/{序号}{乡镇名}/{文物名}.docx`，例如 `01示范街道/某某村古寨遗址.docx`。序号可省略，乡镇目录可省略（直接把 DOCX 平铺在 `01_archives/` 下也行）。

---

## 技术栈

- **后端** — Python 3.10+ / FastAPI / Uvicorn / Pydantic v2
- **前端** — CesiumJS / ECharts / pdf.js（零构建工具链，浏览器直接加载）
- **数据管线** — python-docx / openpyxl / reportlab / Pillow / pyshp / numpy / tifffile / shapely
- **大模型** — OpenAI 兼容协议（默认接 SiliconFlow）
- **坐标** — 自实现 GCJ-02 ⇄ WGS-84，高斯-克吕格反投影

---

## 开发状态

- [x] **A** — 工程骨架、config、.bat 入口、管线编排器
- [x] **B** — 6 步数据管线脚本（DOCX/Excel/SHP/DEM 全流程）
- [x] **C** — WebGIS 迁移：FastAPI 后端 + Cesium 前端全量接入 config.yaml
- [ ] **D** — 边界/模型自动识别优化、admin 后台打磨
- [ ] **E** — 一键打包（内嵌 Python + 数据零依赖分发）

---

## 许可

源码以 **MIT License** 发布。平台里使用的第三方库各自遵循其开源协议；
`data/input/` 中的文物档案、照片、边界等数据**不属于本仓库**，版权归采集单位所有。
