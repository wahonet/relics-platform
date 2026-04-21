"""统计相关 API。"""
from __future__ import annotations

from fastapi import APIRouter

from data_loader import store

router = APIRouter(tags=["统计"])


@router.get("/stats")
async def get_stats():
    """各维度统计数据，供 ECharts 使用。"""
    return store.compute_stats()
