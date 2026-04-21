"""Relics Platform WebGIS 后端入口。

路径/模型/开关等全部来自 config.yaml + `_common.get_paths()`,
应用内不保留任何硬编码的县区/坐标/Key。
"""
from __future__ import annotations

import base64
import math
import sys
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path

# 把 platform/scripts/ 和 webgis/ 自己加到 sys.path,这样
# `from _common import ...` 和 `from routers import ...` 都能
# 在不把 platform 当包安装的情况下直接 import。
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, PlainTextResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

from _common import PROJECT_ROOT, detect_features, get_paths, load_config  # noqa: E402
from data_loader import store  # noqa: E402
from routers import admin, chat, relics, stats, survey_routes, worklog  # noqa: E402
from terrain_provider import get_tile_heights_fast, load_dem  # noqa: E402

# 瓦片缓存未命中时返回的 1x1 透明 PNG
_EMPTY_TILE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lE"
    "QVQI12NgAAIABQABNjN9GQAAAAlwSFlzAAALEwAACxMBAJqcGAAA"
    "ABl0RVh0U29mdHdhcmUAcGFpbnQubmV0IDQuMC4xMkMEa+wAAAAN"
    "SURBVBhXY2BgYPgPAAEEAQBLzKDhAAAAAElFTkSuQmCC"
)

TILE_URLS = {
    "arcgis_sat": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "osm": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "gaode_anno": "https://wprd0{s}.is.autonavi.com/appmaptile?x={x}&y={y}&z={z}&lang=zh_cn&size=1&scl=1&style=8",
}

_CONFIG: dict = {}
_FEATURES: dict = {}
_PATHS = get_paths()
WEBGIS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEBGIS_DIR / "templates"
STATIC_DIR = WEBGIS_DIR / "static"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
TILE_CACHE_DIR = PROJECT_ROOT / "data" / "output" / "tile_cache"
TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _CONFIG, _FEATURES
    _CONFIG = load_config()
    _FEATURES = detect_features().as_dict

    geo = _CONFIG.get("geo") or {}
    bounds = geo.get("bounds") or {}
    bbox = (
        bounds.get("west", -180.0),
        bounds.get("south", -90.0),
        bounds.get("east", 180.0),
        bounds.get("north", 90.0),
    )

    # 以下三项都是可选数据源,存在即加载
    village_gj = _PATHS.output_boundaries / "villages.geojson"  # 村村达需要
    village_arg = str(village_gj) if village_gj.exists() else ""
    pdf_dir = PROJECT_ROOT / "data" / "input" / "01_archives_pdf"
    survey_csv = _PATHS.input_worklogs / "survey_gps.csv"

    store.load(
        str(_PATHS.output_dataset),
        village_geojson=village_arg,
        pdf_dir=str(pdf_dir) if pdf_dir.exists() else "",
        survey_gps_csv=str(survey_csv) if survey_csv.exists() else "",
        bounds=bbox,
    )

    print(f"[启动] 已加载 {len(store.relics)} 条文物记录")
    print(f"[启动] 已加载 {len(store.photo_index)} 条照片索引")
    print(f"[启动] 已加载 {len(store.drawing_index)} 条图纸索引")
    print(f"[启动] 已索引 {len(store.pdf_map)} 个档案 PDF")
    print(f"[启动] 已加载 {len(store.survey_routes)} 天普查路线")
    if store.village_coverage:
        vc = store.village_coverage
        print(f"[启动] 村村达: {vc['reached']}/{vc['total']} 村已到达")

    cached = sum(1 for _ in TILE_CACHE_DIR.rglob("*.tile"))
    print(f"[启动] 瓦片缓存: {cached} 张 → {TILE_CACHE_DIR}")

    dem_dir = _PATHS.input_dem
    enable_dem = _feature_enabled("enable_dem", _FEATURES.get("dem", False))
    if enable_dem and dem_dir.exists():
        load_dem(str(dem_dir))
    else:
        print(f"[DEM] 已跳过（enable_dem={enable_dem}, exists={dem_dir.exists()}）")

    try:
        chat.init_chat()
    except Exception as e:
        print(f"[AI] 初始化失败: {e}")

    yield


def _feature_enabled(cfg_key: str, auto_value: bool) -> bool:
    """config.features.<cfg_key>: true/false 强制开关,其他值(含 'auto')
    回退到自动检测结果 auto_value。"""
    v = (_CONFIG.get("features") or {}).get(cfg_key, "auto")
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.lower() in ("true", "yes", "on"):
        return True
    if isinstance(v, str) and v.lower() in ("false", "no", "off"):
        return False
    return bool(auto_value)


app = FastAPI(title="Relics Platform", version="1.0.0", lifespan=lifespan)

_PUBLIC_PREFIXES = ("/login", "/api/login", "/static/", "/tiles/", "/api/terrain/", "/api/platform/config")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not (_CONFIG.get("server") or {}).get("enable_auth", False):
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        if request.cookies.get("session") != "authenticated":
            return RedirectResponse(url="/login", status_code=302)
        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(relics.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(survey_routes.router, prefix="/api")
app.include_router(worklog.router, prefix="/api")


# 前端启动时拉取的运行时配置(项目名/中心点/特性开关/Cesium token 等)。
# 同时通过 _bootstrap_script 注入到 HTML 里,前端优先读 window.__PLATFORM_CONFIG,
# 拉不到再回退到本接口。
@app.get("/api/platform/config")
async def platform_config() -> JSONResponse:
    cfg = _CONFIG or {}
    proj = cfg.get("project", {}) or {}
    geo = cfg.get("geo", {}) or {}
    admin_cfg = cfg.get("administrative", {}) or {}
    api_cfg = cfg.get("api", {}) or {}

    def _resolved(val: str) -> str:
        if not val or (isinstance(val, str) and val.startswith("${") and val.endswith("}")):
            return ""
        return val

    cesium_token = _resolved((api_cfg.get("cesium_ion") or {}).get("token", ""))
    sf = api_cfg.get("siliconflow") or {}

    features_resolved = {
        "ai_chat": _feature_enabled("enable_ai_chat", bool(_resolved(sf.get("key", "")))),
        "worklog": _feature_enabled("enable_worklog", _FEATURES.get("worklogs", False)),
        "models_3d": _feature_enabled("enable_3d_model", _FEATURES.get("models_3d", False)),
        "dem": _feature_enabled("enable_dem", _FEATURES.get("dem", False)),
    }

    return JSONResponse({
        "project": {
            "name": proj.get("name", ""),
            "full_name": proj.get("full_name", ""),
            "data_cutoff": proj.get("data_cutoff", ""),
            "data_source": proj.get("data_source", ""),
        },
        "geo": geo,
        "administrative": {
            "county_name": admin_cfg.get("county_name", ""),
            "townships": admin_cfg.get("townships", []),
        },
        "features": features_resolved,
        "cesium_ion_token": cesium_token,
        "ai_chat": {
            "enabled": features_resolved["ai_chat"],
            "default_model": sf.get("default_model", ""),
            "available_models": sf.get("available_models", []),
        },
        "stats": {
            "relics_total": len(store.relics),
            "has_3d_count": sum(1 for r in store.relics if r.get("has_3d")),
        },
    })


@app.get("/api/config")
async def legacy_config() -> JSONResponse:
    """早期前端用的路径,保持 301 兼容。"""
    return await platform_config()


@app.get("/api/terrain/{level}/{x}/{y}")
async def terrain_tile(level: int, x: int, y: int):
    data = await run_in_threadpool(get_tile_heights_fast, level, x, y)
    if data is None:
        return Response(status_code=404)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        },
    )


def _fetch_tile(provider: str, z: int, x: int, y: int) -> bytes | None:
    tpl = TILE_URLS.get(provider)
    if not tpl:
        return None
    s = str((x % 4) + 1) if provider.startswith("gaode") else str(x % 4)
    url = tpl.format(s=s, x=x, y=y, z=z)
    headers = {"User-Agent": "Mozilla/5.0"}
    if provider.startswith("gaode"):
        headers["Referer"] = "https://www.amap.com/"
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=20).read()


@app.get("/tiles/{provider}/{z}/{x}/{y}")
async def tile_proxy(provider: str, z: int, x: int, y: int):
    """离线优先:命中磁盘缓存直接返回,未命中返回 1x1 透明 PNG(不做联网拉取,
    联网预热走 /api/tiles/precache)。"""
    cache_path = TILE_CACHE_DIR / provider / str(z) / str(x) / f"{y}.tile"
    if cache_path.exists():
        return Response(
            content=cache_path.read_bytes(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=31536000"},
        )
    return Response(content=_EMPTY_TILE, media_type="image/png")


def _lon_to_tile_x(lon: float, z: int) -> int:
    return int((lon + 180) / 360 * (1 << z))


def _lat_to_tile_y(lat: float, z: int) -> int:
    lat_rad = math.radians(lat)
    return int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * (1 << z))


def _bounds_from_config() -> tuple[float, float, float, float]:
    geo = _CONFIG.get("geo") or {}
    b = geo.get("bounds") or {}
    return (
        float(b.get("west", 73.0)),
        float(b.get("south", 18.0)),
        float(b.get("east", 135.0)),
        float(b.get("north", 54.0)),
    )


def _tiles_for_bounds(west, south, east, north, z):
    x0 = _lon_to_tile_x(west, z)
    x1 = _lon_to_tile_x(east, z)
    y0 = _lat_to_tile_y(north, z)
    y1 = _lat_to_tile_y(south, z)
    return [(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


@app.get("/api/tiles/cache-status")
async def cache_status(provider: str = "arcgis_sat"):
    bbox = _bounds_from_config()
    total, cached_n = 0, 0
    for z in range(1, 16):
        tiles = _tiles_for_bounds(*bbox, z)
        total += len(tiles)
        for tz, tx, ty in tiles:
            if (TILE_CACHE_DIR / provider / str(tz) / str(tx) / f"{ty}.tile").exists():
                cached_n += 1
    return {"total": total, "cached": cached_n}


@app.post("/api/tiles/precache")
async def precache_tiles(provider: str = "arcgis_sat", min_zoom: int = 1, max_zoom: int = 15):
    import concurrent.futures

    if provider not in TILE_URLS:
        provider = "arcgis_sat"

    bbox = _bounds_from_config()
    tasks, skipped = [], 0
    zm = min(max_zoom + 1, 17)
    for z in range(max(1, min_zoom), zm):
        for tz, tx, ty in _tiles_for_bounds(*bbox, z):
            cp = TILE_CACHE_DIR / provider / str(tz) / str(tx) / f"{ty}.tile"
            if cp.exists():
                skipped += 1
            else:
                tasks.append((provider, tz, tx, ty, cp))

    def _dl_one(args):
        prov, z, x, y, cp = args
        try:
            data = _fetch_tile(prov, z, x, y)
            if data:
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_bytes(data)
                return True
        except Exception:
            return False

    def _run():
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(_dl_one, tasks))

    results = await run_in_threadpool(_run) if tasks else []
    downloaded = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    return {"downloaded": downloaded, "failed": failed, "skipped": skipped}


def _mount_if_exists(path_prefix: str, directory: Path, name: str, *, create: bool = False) -> None:
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    if directory.exists():
        app.mount(path_prefix, StaticFiles(directory=str(directory)), name=name)
    else:
        print(f"[警告] 目录不存在，跳过挂载 {path_prefix}: {directory}")


_mount_if_exists("/photos", _PATHS.output_photos, "photos", create=True)
_mount_if_exists("/drawings", _PATHS.output_drawings, "drawings", create=True)
_mount_if_exists("/boundaries", _PATHS.output_boundaries, "boundaries", create=True)
_mount_if_exists("/worklog-pdfs", _PATHS.output_worklogs, "worklog_pdfs", create=True)
_mount_if_exists("/3d", _PATHS.input_models_3d, "3d_models", create=True)
_mount_if_exists("/pdfs", PROJECT_ROOT / "data" / "input" / "01_archives_pdf", "pdfs")
_mount_if_exists("/survey-photos", _PATHS.input_worklogs / "survey_photos", "survey_photos")
_mount_if_exists("/static", STATIC_DIR, "static")
_mount_if_exists("/assets", FRONTEND_DIST / "assets", "vue_assets")


def _bootstrap_script() -> str:
    """拼出一段 inline <script>,在其它脚本执行前挂载 window.__PLATFORM_CONFIG,
    并在 Cesium 已加载时自动注入 Ion token。"""
    import json as _json

    proj = (_CONFIG.get("project") or {})
    geo = (_CONFIG.get("geo") or {})
    adm = (_CONFIG.get("administrative") or {})
    api = (_CONFIG.get("api") or {})
    sf = api.get("siliconflow") or {}
    cesium_token = (api.get("cesium_ion") or {}).get("token", "") or ""
    if cesium_token.startswith("${") and cesium_token.endswith("}"):
        cesium_token = ""

    payload = {
        "project": {
            "name": proj.get("name", ""),
            "full_name": proj.get("full_name", ""),
            "data_cutoff": proj.get("data_cutoff", ""),
            "data_source": proj.get("data_source", ""),
        },
        "geo": {
            "center": geo.get("center") or {"lng": 116.0, "lat": 35.0, "alt": 75000},
            "bounds": geo.get("bounds") or {},
        },
        "administrative": {
            "county_name": adm.get("county_name", ""),
            "townships": adm.get("townships", []),
        },
        "features": {
            "ai_chat": _feature_enabled("enable_ai_chat", bool(sf.get("key", "").strip() and not sf.get("key", "").startswith("${"))),
            "worklog": _feature_enabled("enable_worklog", _FEATURES.get("worklogs", False)),
            "models_3d": _feature_enabled("enable_3d_model", _FEATURES.get("models_3d", False)),
            "dem": _feature_enabled("enable_dem", _FEATURES.get("dem", False)),
        },
        "cesium_ion_token": cesium_token,
        "stats": {
            "relics_total": len(store.relics),
        },
    }
    js_payload = _json.dumps(payload, ensure_ascii=False)
    return (
        "<script>\n"
        f"window.__PLATFORM_CONFIG = {js_payload};\n"
        "try { if (window.Cesium && window.__PLATFORM_CONFIG.cesium_ion_token) "
        "{ Cesium.Ion.defaultAccessToken = window.__PLATFORM_CONFIG.cesium_ion_token; } } catch(e) {}\n"
        "</script>\n"
    )


def _render_template(name: str) -> str:
    """读 templates/<name>.html,做两件事:
    (1) 替换 {{ full_name }} / {{ county_name }} / {{ data_source }};
    (2) 在 </head> 之前注入 bootstrap script,前端以此拿到配置。
    """
    path = TEMPLATES_DIR / name
    if not path.exists():
        return f"<h1>模板缺失: {name}</h1>"
    html = path.read_text(encoding="utf-8")

    proj = (_CONFIG.get("project") or {})
    adm = (_CONFIG.get("administrative") or {})
    full_name = proj.get("full_name") or ""
    county_name = adm.get("county_name") or proj.get("name") or ""
    data_source = proj.get("data_source") or ""

    for k, v in {
        "{{ full_name }}": full_name,
        "{{ county_name }}": county_name,
        "{{ data_source }}": data_source,
    }.items():
        html = html.replace(k, v)

    bootstrap = _bootstrap_script()
    if "</head>" in html:
        html = html.replace("</head>", bootstrap + "</head>", 1)
    else:
        html = bootstrap + html
    return html


@app.get("/", response_class=HTMLResponse)
async def index():
    return _render_template("index.html")


@app.get("/vue", response_class=HTMLResponse)
async def vue_index():
    index_path = FRONTEND_DIST / "index.html"
    if not index_path.exists():
        return PlainTextResponse(
            "Vue 前端尚未构建。请在项目根目录执行: cd frontend && npm install && npm run build",
            status_code=404,
        )
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/model-viewer", response_class=HTMLResponse)
async def model_viewer():
    return _render_template("model_viewer.html")


@app.get("/pdf-viewer", response_class=HTMLResponse)
async def pdf_viewer():
    return _render_template("pdf_viewer.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return _render_template("admin.html")


class _LoginBody(BaseModel):
    username: str
    password: str


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return _render_template("login.html")


@app.post("/api/login")
async def api_login(body: _LoginBody):
    users = (_CONFIG.get("server") or {}).get("users") or []
    for u in users:
        if u.get("username") == body.username and u.get("password") == body.password:
            resp = JSONResponse({"ok": True})
            resp.set_cookie(
                key="session", value="authenticated",
                httponly=True, samesite="lax", path="/",
            )
            return resp
    return JSONResponse({"detail": "用户名或密码错误"}, status_code=401)
