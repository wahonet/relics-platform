"""数据管线公共工具:配置加载/路径解析/日志/坐标系。

所有 step0X 脚本应通过 `from _common import ...` 获取统一入口,
不要在脚本里再写硬编码路径或重复的坐标系算法。
"""
from __future__ import annotations

import logging
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Windows 默认 cp936 无法输出部分 Unicode 字符,统一切到 UTF-8
for stream_name in ("stdout", "stderr"):
    s = getattr(sys, stream_name, None)
    if s is not None and hasattr(s, "reconfigure"):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "[错误] 未安装 pyyaml。请先运行 setup.bat 或手动执行:\n"
        "       python -m pip install pyyaml\n"
    )
    sys.exit(1)


PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PLATFORM_ROOT: Path = PROJECT_ROOT / "platform"
CONFIG_PATH: Path = PROJECT_ROOT / "config.yaml"
CONFIG_EXAMPLE_PATH: Path = PROJECT_ROOT / "config.example.yaml"


@dataclass(frozen=True)
class Paths:
    root: Path
    input_archives: Path       # DOCX 档案
    input_worklogs: Path       # 外业工作日志 Excel
    input_boundaries: Path     # 行政边界 Shapefile / GeoJSON
    input_dem: Path            # DEM GeoTIFF
    input_models_3d: Path      # 3D Tiles
    output_markdown: Path      # step01 产物
    output_dataset: Path       # step02 产物
    output_photos: Path        # step03 产物
    output_drawings: Path      # step04 产物
    output_worklogs: Path      # step05 产物(工作日志 PDF)
    output_boundaries: Path    # step06 产物(边界 GeoJSON)
    output_logs: Path


def get_paths() -> Paths:
    root = PROJECT_ROOT
    return Paths(
        root=root,
        input_archives=root / "data" / "input" / "01_archives",
        input_worklogs=root / "data" / "input" / "02_worklogs",
        input_boundaries=root / "data" / "input" / "03_boundaries",
        input_dem=root / "data" / "input" / "04_dem",
        input_models_3d=root / "data" / "input" / "05_models_3d",
        output_markdown=root / "data" / "output" / "markdown",
        output_dataset=root / "data" / "output" / "dataset",
        output_photos=root / "data" / "output" / "photos",
        output_drawings=root / "data" / "output" / "drawings",
        output_worklogs=root / "data" / "output" / "worklog_pdfs",
        output_boundaries=root / "data" / "output" / "boundaries",
        output_logs=root / "data" / "output" / "logs",
    )


def ensure_data_dirs() -> None:
    """setup.bat 首次运行时创建全部 data/ 目录。"""
    p = get_paths()
    for f in p.__dataclass_fields__:
        if f == "root":
            continue
        getattr(p, f).mkdir(parents=True, exist_ok=True)


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    """递归把字符串里的 ${VAR} 替换成环境变量值;未定义则保留原样。"""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)), value
        )
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: Path | str | None = None) -> dict:
    cfg_path = Path(path) if path else CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"未找到 {cfg_path}\n请先运行项目根目录的 setup.bat 完成初始化。"
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return _expand_env(cfg)


# ── 坐标系:GCJ-02 ↔ WGS-84 ───────────────────────────────────
# 国内四普档案多为 GCJ-02(火星坐标),测绘下发的 shp 也常在 GCJ-02 上
# 再做高斯克吕格投影。step02 把点位归一到 WGS-84,step06 可选地对
# 行政边界做同样修正,让两者叠图时不漂移。
_GCJ_A = 6378245.0
_GCJ_EE = 0.00669342162296594323


def _gcj_delta(lng: float, lat: float) -> tuple[float, float]:
    x, y = lng - 105.0, lat - 35.0
    d_lat = (
        -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        + (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        + (160.0 * math.sin(y / 12.0 * math.pi) + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    )
    d_lng = (
        300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        + (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        + (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    )
    rad_lat = lat / 180.0 * math.pi
    magic = 1 - _GCJ_EE * math.sin(rad_lat) ** 2
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((_GCJ_A * (1 - _GCJ_EE)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (_GCJ_A / sqrt_magic * math.cos(rad_lat) * math.pi)
    return d_lng, d_lat


def gcj02_to_wgs84(lng: float, lat: float) -> tuple[float, float]:
    d_lng, d_lat = _gcj_delta(lng, lat)
    return round(lng - d_lng, 8), round(lat - d_lat, 8)


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    d_lng, d_lat = _gcj_delta(lng, lat)
    return round(lng + d_lng, 8), round(lat + d_lat, 8)


_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(step_name: str) -> logging.Logger:
    """每个 step 一个 logger,文件输出到 data/output/logs/<step>.log,
    同时镜像到 stdout。"""
    if step_name in _LOGGERS:
        return _LOGGERS[step_name]

    paths = get_paths()
    paths.output_logs.mkdir(parents=True, exist_ok=True)
    log_file = paths.output_logs / f"{step_name}.log"

    logger = logging.getLogger(step_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.propagate = False
    _LOGGERS[step_name] = logger
    return logger


@dataclass
class FeatureStatus:
    has_archives: bool
    has_worklogs: bool
    has_boundaries: bool
    has_dem: bool
    has_3d_models: bool

    @property
    def as_dict(self) -> dict:
        return {
            "archives": self.has_archives,
            "worklogs": self.has_worklogs,
            "boundaries": self.has_boundaries,
            "dem": self.has_dem,
            "models_3d": self.has_3d_models,
        }


def _non_empty(d: Path, patterns: tuple[str, ...]) -> bool:
    if not d.exists():
        return False
    return any(any(d.rglob(pat)) for pat in patterns)


def detect_features() -> FeatureStatus:
    """扫描 data/input 判断哪些功能模块有数据。main.py 的 feature toggle
    在 auto 模式下依赖此结果。"""
    p = get_paths()
    return FeatureStatus(
        has_archives=_non_empty(p.input_archives, ("*.docx", "*.DOCX")),
        has_worklogs=_non_empty(p.input_worklogs, ("*.xlsx", "*.xls")),
        has_boundaries=_non_empty(
            p.input_boundaries, ("*.shp", "*.geojson", "*.json")
        ),
        has_dem=_non_empty(p.input_dem, ("*.tif", "*.tiff")),
        has_3d_models=_non_empty(p.input_models_3d, ("tileset.json",)),
    )


def print_status() -> None:
    """setup.bat / run_pipeline.bat 末尾调用,打印当前项目概览。"""
    print("=" * 60)
    print("  Relics Platform - 项目状态")
    print("=" * 60)
    print(f"\n[路径] 项目根目录: {PROJECT_ROOT}")

    if CONFIG_PATH.exists():
        try:
            cfg = load_config()
            proj = cfg.get("project", {})
            print(f"[配置] {CONFIG_PATH.name} 已存在")
            print(f"       项目名: {proj.get('name', '(未设置)')}")
            print(f"       全称: {proj.get('full_name', '(未设置)')}")
        except Exception as e:
            print(f"[配置] {CONFIG_PATH.name} 解析失败: {e}")
    else:
        print(f"[配置] {CONFIG_PATH.name} 不存在,请先运行 setup.bat")

    feat = detect_features()
    print("\n[数据] 输入检测:")
    label_map = {
        "archives": "文物档案 DOCX",
        "worklogs": "工作日志 Excel",
        "boundaries": "行政边界",
        "dem": "DEM 栅格",
        "models_3d": "3D 模型",
    }
    for key, label in label_map.items():
        status = "OK" if feat.as_dict[key] else "--"
        print(f"       [{status}] {label}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_status()
