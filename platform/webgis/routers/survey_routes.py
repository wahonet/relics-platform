"""普查路线 API。"""
from __future__ import annotations

from fastapi import APIRouter

from data_loader import store

router = APIRouter(tags=["普查路线"])


@router.get("/survey-routes")
async def get_survey_routes():
    """按日期分组的普查路线数据（若未提供普查 GPS CSV 则为空）。"""
    return store.survey_routes


@router.get("/village-coverage")
async def get_village_coverage():
    """村村达覆盖分析结果。"""
    return store.village_coverage or {
        "total": 0, "reached": 0, "unreached": 0, "villages": [],
    }
