"""内置内容仓库：词库、真题、作文题、翻译题、积累本种子数据。

所有内容放在 content/*.json，打包时随 EXE 一起分发；用户数据不在这里。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from repositories.store import resource_path


def content_dir() -> Path:
    return resource_path("content")


@lru_cache(maxsize=16)
def _load(name: str):
    path = content_dir() / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _analyses() -> dict:
    """逐题解析放在 content/analyses/<exam>.json，缺了就降级显示。"""
    folder = content_dir() / "analyses"
    merged: dict = {}
    if not folder.exists():
        return merged
    for path in sorted(folder.glob("*.json")):
        try:
            merged[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
    return merged


def vocabulary() -> list[dict]:
    return _load("vocabulary.json")


def _merge(target: dict, extra: dict) -> None:
    """解析并入题目对象；answer 以数据层（已核对）为准，不被解析文件覆盖。"""
    for key, value in extra.items():
        if key == "answer":
            continue
        target[key] = value


def reading() -> list[dict]:
    """真题阅读（内置 2023 手校 + 2024–2025 抓取），合并可选的学习解析。"""
    exams = list(_load("reading.json"))
    known = {exam["id"] for exam in exams}
    for exam in _load("exams_scraped.json"):
        if exam.get("id") and exam["id"] not in known:
            exams.append(exam)
            known.add(exam["id"])
    exams.sort(key=lambda item: (item.get("year", 0), item.get("month", 0), item.get("set", 0)))
    analyses = _analyses()
    for exam in exams:
        analysis = analyses.get(exam["id"])
        exam["has_analysis"] = bool(analysis)
        if not analysis:
            continue
        cloze = analysis.get("cloze", {})
        for blank in exam["cloze"].get("blanks", []):
            _merge(blank, cloze.get("blanks", {}).get(str(blank["num"]), {}))
        exam["cloze"]["passage_zh"] = cloze.get("passage_zh", "")
        matching = analysis.get("matching", {})
        for statement in exam["matching"].get("statements", []):
            _merge(statement, matching.get("statements", {}).get(str(statement["num"]), {}))
        exam["matching"]["article_zh"] = matching.get("article_zh", "")
        for passage in exam["careful"]:
            extra = analysis.get("careful", {}).get(passage["id"], {})
            passage["passage_zh"] = extra.get("passage_zh", "")
            passage["vocabulary"] = extra.get("vocabulary", [])
            passage["long_sentence"] = extra.get("long_sentence", {})
            for question in passage["questions"]:
                _merge(question, extra.get("questions", {}).get(str(question["num"]), {}))
    return exams


def writing() -> list[dict]:
    return _load("writing.json")


def translation() -> list[dict]:
    return _load("translation.json")


def accumulation_seed() -> list[dict]:
    return _load("accumulation_seed.json")


def reading_index(exams: list[dict] | None = None) -> dict:
    exams = exams if exams is not None else reading()
    return {exam["id"]: exam for exam in exams}
