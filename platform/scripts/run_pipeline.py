"""数据管线编排器。

用法:
    python run_pipeline.py              顺序执行所有步骤
    python run_pipeline.py --from 02    从第 2 步开始
    python run_pipeline.py --to 04      执行到第 4 步为止
    python run_pipeline.py --only 03    仅执行第 3 步
    python run_pipeline.py --list       列出全部步骤
    python run_pipeline.py --dry-run    只显示计划不实际跑

optional=True 的步骤在对应输入缺失时会被自动跳过;
optional=False 的步骤缺输入则整条管线中止并返回非零码。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from _common import PROJECT_ROOT, detect_features, get_logger, load_config

SCRIPTS_DIR = Path(__file__).resolve().parent


STEPS = [
    {
        "id": "01",
        "name": "转换档案 DOCX → Markdown",
        "script": "step01_convert_docs.py",
        "requires": ["archives"],
        "optional": False,
    },
    {
        "id": "02",
        "name": "构建结构化数据集",
        "script": "step02_build_dataset.py",
        "requires": [],
        "optional": False,
    },
    {
        "id": "03",
        "name": "提取照片",
        "script": "step03_extract_photos.py",
        "requires": ["archives"],
        "optional": False,
    },
    {
        "id": "04",
        "name": "提取图纸",
        "script": "step04_extract_drawings.py",
        "requires": ["archives"],
        "optional": False,
    },
    {
        "id": "05",
        "name": "转换工作日志 Excel → PDF",
        "script": "step05_convert_worklogs.py",
        "requires": ["worklogs"],
        "optional": True,
    },
    {
        "id": "06",
        "name": "预处理行政边界",
        "script": "step06_prepare_boundaries.py",
        "requires": ["boundaries"],
        "optional": True,
    },
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Relics Platform - 数据管线编排器")
    p.add_argument("--from", dest="from_id", default=None,
                   help="起始步骤编号，如 02")
    p.add_argument("--to", dest="to_id", default=None,
                   help="结束步骤编号（含），如 04")
    p.add_argument("--only", dest="only_id", default=None,
                   help="仅执行指定步骤，如 03")
    p.add_argument("--list", action="store_true", help="列出所有步骤后退出")
    p.add_argument("--dry-run", action="store_true",
                   help="只显示将要执行的步骤，不实际运行")
    return p.parse_args()


def _list_steps() -> None:
    print("步骤列表：")
    for s in STEPS:
        tag = "[可选]" if s["optional"] else "[必须]"
        print(f"  {s['id']}  {tag}  {s['name']}  ({s['script']})")


def _select_steps(args: argparse.Namespace) -> list[dict]:
    if args.only_id:
        return [s for s in STEPS if s["id"] == args.only_id]
    selected = STEPS[:]
    if args.from_id:
        selected = [s for s in selected if s["id"] >= args.from_id]
    if args.to_id:
        selected = [s for s in selected if s["id"] <= args.to_id]
    return selected


def _run_step(step: dict, log) -> int:
    script_path = SCRIPTS_DIR / step["script"]
    if not script_path.exists():
        log.error(f"脚本不存在: {script_path}")
        return 1
    log.info(f"→ 开始 step{step['id']}: {step['name']}")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(SCRIPTS_DIR),
    )
    dt = time.time() - t0
    if proc.returncode == 0:
        log.info(f"✓ step{step['id']} 完成（耗时 {dt:.1f}s）")
    else:
        log.error(f"✗ step{step['id']} 失败（退出码 {proc.returncode}，耗时 {dt:.1f}s）")
    return proc.returncode


def main() -> int:
    args = _parse_args()
    if args.list:
        _list_steps()
        return 0

    log = get_logger("pipeline")

    try:
        load_config()
    except FileNotFoundError as e:
        log.error(str(e))
        return 2

    features = detect_features().as_dict
    selected = _select_steps(args)

    if not selected:
        log.error("没有匹配的步骤")
        return 2

    log.info(f"项目根目录: {PROJECT_ROOT}")
    log.info(f"输入数据状态: {features}")
    log.info(f"计划执行 {len(selected)} 个步骤")

    for step in selected:
        needs = step["requires"]
        missing = [r for r in needs if not features.get(r, False)]

        if args.dry_run:
            if missing and not step["optional"]:
                log.info(
                    f"[dry-run] step{step['id']}: {step['name']} "
                    f"(将因缺少 {missing} 而失败)"
                )
            elif missing and step["optional"]:
                log.info(
                    f"[dry-run] step{step['id']}: {step['name']} "
                    f"(将自动跳过，可选且缺 {missing})"
                )
            else:
                log.info(f"[dry-run] step{step['id']}: {step['name']}")
            continue

        if missing:
            if step["optional"]:
                log.warning(
                    f"跳过 step{step['id']}（可选，缺少输入: {missing}）"
                )
                continue
            log.error(
                f"step{step['id']} 需要的数据缺失: {missing}；"
                "请补齐数据后重试。"
            )
            return 3

        rc = _run_step(step, log)
        if rc != 0:
            log.error(f"管线因 step{step['id']} 失败中止。")
            return rc

    if args.dry_run:
        log.info("[dry-run] 计划展示完成（未实际运行）。")
    else:
        log.info("全部步骤完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
