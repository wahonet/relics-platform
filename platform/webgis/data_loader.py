"""全局数据容器,启动时把 data/output/ 下的 step02-06 产物一次性读入内存。

读取的文件:
    data/output/dataset/relics_full.json        文物主数据
    data/output/dataset/relics_points/polygons.geojson
    data/output/dataset/photo_index.csv         step03 产物(可选)
    data/output/dataset/drawing_index.csv       step04 产物(可选)
    data/output/dataset/township_stats.csv
    data/output/boundaries/villages.geojson     step06 产物(村村达用)
    data/input/02_worklogs/survey_gps.csv       普查轨迹(可选)
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("uvicorn.error")


class DataStore:
    """全局数据容器。main.py lifespan 里调用 load() 初始化一次,
    此后各路由直接通过模块级单例 `store` 读取,不再打开文件。"""

    def __init__(self) -> None:
        self.relics: list[dict] = []
        self.relics_map: dict[str, dict] = {}
        self.photo_index: list[dict] = []
        self.photo_map: dict[str, list[dict]] = {}
        self.drawing_index: list[dict] = []
        self.drawing_map: dict[str, list[dict]] = {}
        self.pdf_map: dict[str, str] = {}
        self.geojson_points: dict = {}
        self.geojson_polygons: dict = {}
        self.township_stats: list[dict] = []
        self.survey_routes: dict[str, list[dict]] = {}
        self.village_coverage: dict = {}
        # 来自 config.geo.bounds,用于过滤 survey_gps.csv 里离群的 GPS 点
        self._bounds: Optional[tuple[float, float, float, float]] = None

    def load(
        self,
        dataset_dir: str | Path,
        *,
        village_geojson: str | Path = "",
        pdf_dir: str | Path = "",
        survey_gps_csv: str | Path = "",
        bounds: Optional[tuple[float, float, float, float]] = None,
    ) -> None:
        """一次性加载全部数据源。village_geojson/pdf_dir/survey_gps_csv 为空或
        指向不存在的路径时对应功能会被静默跳过。"""
        dp = Path(dataset_dir)
        self._bounds = bounds

        self._load_relics(dp / "relics_full.json")
        self._load_photo_index(dp / "photo_index.csv")
        self._load_drawing_index(dp / "drawing_index.csv")
        self._load_geojson(dp)
        self._load_township_stats(dp / "township_stats.csv")

        if pdf_dir:
            self._load_pdf_index(Path(pdf_dir))

        if survey_gps_csv and Path(survey_gps_csv).exists():
            self._load_survey_routes(Path(survey_gps_csv))

        if village_geojson and Path(village_geojson).exists() and self.survey_routes:
            self._compute_village_coverage(Path(village_geojson))

    def _load_relics(self, path: Path) -> None:
        if not path.exists():
            log.warning("[数据] 未找到 %s", path)
            return
        with open(path, "r", encoding="utf-8") as f:
            self.relics = json.load(f)
        for r in self.relics:
            code = r.get("archive_code")
            if code:
                self.relics_map[code] = r

    def _load_photo_index(self, path: Path) -> None:
        if not path.exists():
            return
        self.photo_index = self._read_csv(path)
        for p in self.photo_index:
            code = p.get("archive_code")
            if code:
                self.photo_map.setdefault(code, []).append(p)

    def _load_drawing_index(self, path: Path) -> None:
        if not path.exists():
            return
        self.drawing_index = self._read_csv(path)
        for d in self.drawing_index:
            code = d.get("archive_code")
            if code:
                self.drawing_map.setdefault(code, []).append(d)

    def _load_geojson(self, data_path: Path) -> None:
        pts = data_path / "relics_points.geojson"
        polys = data_path / "relics_polygons.geojson"
        if pts.exists():
            with open(pts, "r", encoding="utf-8") as f:
                self.geojson_points = json.load(f)
        if polys.exists():
            with open(polys, "r", encoding="utf-8") as f:
                self.geojson_polygons = json.load(f)

    def _load_township_stats(self, path: Path) -> None:
        if path.exists():
            self.township_stats = self._read_csv(path)

    def _load_pdf_index(self, pdf_dir: Path) -> None:
        """扫描一层 PDF 子目录,建立 {子目录名(视作 archive_code): 首个 pdf 相对路径}。"""
        if not pdf_dir.exists():
            log.warning("[PDF] 目录不存在: %s", pdf_dir)
            return
        for sub in pdf_dir.iterdir():
            if not sub.is_dir():
                continue
            pdfs = sorted(sub.glob("*.pdf"))
            if pdfs:
                self.pdf_map[sub.name] = f"{sub.name}/{pdfs[0].name}"
        log.info("[PDF] %d 个档案 PDF 已索引", len(self.pdf_map))

    def _load_survey_routes(self, path: Path) -> None:
        """加载普查轨迹 CSV,并按日期分组、按时间排序。
        列名兼容中文(拍摄时间/经度/纬度/文件名)和英文(time/lon/lat/filename)。"""
        rows = self._read_csv(path)
        if not rows:
            return

        def _pick(row: dict, *keys: str) -> str:
            for k in keys:
                if k in row and row[k] not in (None, ""):
                    return str(row[k]).strip()
            return ""

        west, south, east, north = self._bounds or (-180.0, -90.0, 180.0, 90.0)
        groups: dict[str, list[dict]] = {}

        for row in rows:
            dt_str = _pick(row, "拍摄时间", "time", "datetime")
            lat_str = _pick(row, "纬度", "lat", "latitude")
            lon_str = _pick(row, "经度", "lon", "lng", "longitude")
            if not dt_str or not lat_str or not lon_str:
                continue
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                continue
            if not (south < lat < north and west < lon < east):
                continue

            parts = dt_str.split(" ", 1)
            date_raw = parts[0]
            time_raw = parts[1] if len(parts) > 1 else "00:00:00"

            dp = date_raw.replace("/", "-").split("-")
            if len(dp) == 3:
                date = f"{int(dp[0]):04d}-{int(dp[1]):02d}-{int(dp[2]):02d}"
            else:
                date = date_raw

            tp = time_raw.split(":")
            time_val = ":".join(p.zfill(2) for p in tp[:3])
            if len(tp) < 3:
                time_val += ":00"

            groups.setdefault(date, []).append({
                "filename": _pick(row, "文件名", "filename"),
                "time": time_val,
                "lat": lat,
                "lon": lon,
            })

        for pts in groups.values():
            pts.sort(key=lambda p: p["time"])
        self.survey_routes = dict(sorted(groups.items()))
        total = sum(len(v) for v in self.survey_routes.values())
        log.info("[普查路线] 已加载 %d 天 / %d 个点", len(self.survey_routes), total)

    def _compute_village_coverage(self, village_path: Path) -> None:
        """村村达:把每天的轨迹串成 LineString 与村面求相交,村内存在文物点
        也记为到达。输出 {total, reached, unreached, villages[]}。"""
        try:
            from shapely.geometry import Point, LineString, shape
            from shapely import STRtree
            from shapely.ops import prep
        except ImportError:
            log.warning("[村村达] 缺少 shapely 依赖，跳过空间分析")
            return

        with open(village_path, "r", encoding="utf-8") as f:
            vdata = json.load(f)
        features = vdata.get("features", [])
        if not features:
            return

        village_list: list[dict] = []
        polygons: list = []
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry")
            if not geom:
                continue
            try:
                poly = shape(geom)
                if not poly.is_valid:
                    poly = poly.buffer(0)
            except Exception:
                continue
            centroid = poly.centroid
            village_list.append({
                "name": props.get("ZLDWMC") or props.get("name") or "",
                "township": props.get("_township") or props.get("township") or "",
                "center_lat": round(centroid.y, 6),
                "center_lon": round(centroid.x, 6),
            })
            polygons.append(poly)

        tree = STRtree(polygons)
        prepped = [prep(p) for p in polygons]
        reached: set[int] = set()
        first_date: dict[int, str] = {}
        reached_by: dict[int, str] = {}

        for date in sorted(self.survey_routes.keys()):
            pts = self.survey_routes[date]
            coords = [(p["lon"], p["lat"]) for p in pts]
            if len(coords) >= 2:
                route_geom = LineString(coords)
            elif len(coords) == 1:
                route_geom = Point(coords[0])
            else:
                continue
            for idx in tree.query(route_geom):
                if idx not in reached and prepped[idx].intersects(route_geom):
                    reached.add(idx)
                    first_date[idx] = date
                    reached_by[idx] = "route"

        for r in self.relics:
            lat = r.get("center_lat")
            lng = r.get("center_lng")
            if not lat or not lng:
                continue
            try:
                pt = Point(float(lng), float(lat))
            except (TypeError, ValueError):
                continue
            for idx in tree.query(pt):
                if idx not in reached and prepped[idx].intersects(pt):
                    reached.add(idx)
                    first_date[idx] = ""
                    reached_by[idx] = "relic"

        villages = []
        for i, v in enumerate(village_list):
            v["reached"] = i in reached
            v["first_date"] = first_date.get(i, "")
            v["reached_by"] = reached_by.get(i, "")
            villages.append(v)

        reached_count = sum(1 for v in villages if v["reached"])
        self.village_coverage = {
            "total": len(villages),
            "reached": reached_count,
            "unreached": len(villages) - reached_count,
            "villages": villages,
        }
        log.info(
            "[村村达] %d/%d 村已到达 (%.1f%%)",
            reached_count,
            len(villages),
            reached_count / len(villages) * 100 if villages else 0,
        )

    def get_relic(self, code: str) -> Optional[dict]:
        return self.relics_map.get(code)

    def get_photos(self, code: str) -> list[dict]:
        return self.photo_map.get(code, [])

    def get_drawings(self, code: str) -> list[dict]:
        return self.drawing_map.get(code, [])

    def get_relics_summary(self) -> list[dict]:
        """返回不含简介/边界点的精简列表,用于地图打点和列表渲染。"""
        fields = [
            "archive_code", "name", "category_main", "category_sub",
            "era", "era_stats", "heritage_level", "township", "address",
            "center_lat", "center_lng", "center_alt",
            "has_boundary", "area", "condition_level", "risk_score",
            "ownership_type", "has_3d", "model_3d_path",
            "photo_count", "drawing_count",
            "survey_type", "industry", "risk_factors",
        ]
        result = []
        for r in self.relics:
            item = {k: r.get(k) for k in fields}
            pdf = self.pdf_map.get(r.get("archive_code", ""))
            item["has_pdf"] = pdf is not None
            item["pdf_path"] = pdf or ""
            result.append(item)
        return result

    def compute_stats(self) -> dict:
        total = len(self.relics)
        by_category: dict[str, int] = {}
        by_township: dict[str, int] = {}
        by_condition: dict[str, int] = {}
        by_era: dict[str, int] = {}
        has_3d_count = 0
        has_boundary_count = 0

        for r in self.relics:
            by_category[r.get("category_main", "未知")] = by_category.get(r.get("category_main", "未知"), 0) + 1
            by_township[r.get("township", "未知")] = by_township.get(r.get("township", "未知"), 0) + 1
            by_condition[r.get("condition_level", "未知")] = by_condition.get(r.get("condition_level", "未知"), 0) + 1
            by_era[r.get("era_stats", "未知")] = by_era.get(r.get("era_stats", "未知"), 0) + 1
            if r.get("has_3d"):
                has_3d_count += 1
            if r.get("has_boundary"):
                has_boundary_count += 1

        return {
            "total": total,
            "has_3d_count": has_3d_count,
            "has_boundary_count": has_boundary_count,
            "by_category": by_category,
            "by_township": by_township,
            "by_condition": by_condition,
            "by_era": by_era,
        }

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        with open(path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))


store = DataStore()
