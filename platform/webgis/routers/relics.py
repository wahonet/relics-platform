"""文物查询相关 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from data_loader import store

router = APIRouter(tags=["文物"])


@router.get("/relics")
async def list_relics():
    """全部文物精简列表，供地图打点。"""
    return store.get_relics_summary()


@router.get("/relics/{code}")
async def get_relic(code: str):
    """单个文物完整信息（含简介）。"""
    relic = store.get_relic(code)
    if not relic:
        raise HTTPException(status_code=404, detail=f"文物 {code} 不存在")
    return relic


@router.get("/relics/{code}/photos")
async def get_relic_photos(code: str):
    if not store.get_relic(code):
        raise HTTPException(status_code=404, detail=f"文物 {code} 不存在")
    return store.get_photos(code)


@router.get("/relics/{code}/drawings")
async def get_relic_drawings(code: str):
    if not store.get_relic(code):
        raise HTTPException(status_code=404, detail=f"文物 {code} 不存在")
    return store.get_drawings(code)


@router.get("/geojson/points")
async def geojson_points():
    return store.geojson_points


@router.get("/geojson/polygons")
async def geojson_polygons():
    return store.geojson_polygons
