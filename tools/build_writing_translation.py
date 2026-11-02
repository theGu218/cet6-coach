"""从真题 Markdown 生成作文题与翻译题（content/writing.json、content/translation.json）。

来源：
  content/raw/english-exem-md/CET6/*  六套 2023 年真题原文（作文 Directions、翻译中文段落）
  content/raw/corpus/                 六级翻译全量题库（73 篇）、作文首句续写题库（30 套）

只收录真题题目；参考范文 / 参考译文由后续流程补充（content/raw/authored/*.json）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "raw"
EXAM_DIR = RAW / "english-exem-md" / "CET6"
CORPUS_TRANS = RAW / "corpus" / "01_历年翻译真题_2015-2025" / "六级翻译全量题库_73篇.md"
CORPUS_WRITE = RAW / "corpus" / "02_历年作文真题_2022-2025" / "六级作文首句续写题库_30套.md"
OUT_WRITING = ROOT / "content" / "writing.json"
OUT_TRANSLATION = ROOT / "content" / "translation.json"

SET_CN = {"一": 1, "二": 2, "三": 3}

# 来源文本的已知 OCR 缺字，按 id 做定点修正（保持与真题原意一致）
CORRECTIONS = {
    "2023-12-3-translation": [("了提升养老机构的服务质量", "为了提升养老机构的服务质量")],
}


def clean(text: str) -> str:
    text = re.sub(r"<u>|</u>", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = text.replace("&emsp;", " ").replace("*", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def label(year: int, month: int, set_no: int) -> str:
    return f"{year}年{month}月 · 第{set_no}套"


def strip_heading(block: str) -> str:
    """去掉 “/ Translation / (30 minutes)” 这行残留。"""
    lines = block.split("\n")
    if lines and re.match(r"^\s*/\s*\w", lines[0]):
        lines = lines[1:]
    return "\n".join(lines)


def strip_directions(block: str) -> str:
    """去掉 Directions 说明段（成对下划线括起来的斜体整行）。"""
    out = []
    skipping = False
    for line in block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("**Directions"):
            skipping = True
        if skipping:
            if stripped.endswith("_") and not stripped.startswith("**Directions") or (
                    stripped.startswith("**Directions") and stripped.count("_") >= 2):
                skipping = False
            continue
        out.append(line)
    return "\n".join(out)


def exam_sections() -> list[dict]:
    exams = []
    for path in sorted(EXAM_DIR.glob("*/cet6-*.md")):
        match = re.search(r"cet6-(\d{4})-(\d{2})-(\d)\.md$", path.name)
        if not match:
            continue
        year, month, set_no = int(match.group(1)), int(match.group(2)), int(match.group(3))
        text = path.read_text(encoding="utf-8")
        writing = ""
        sentence = ""
        theme = ""
        translation = ""
        part1 = re.search(r"## Part I\b(.+?)(?=\n## Part II)", text, re.S)
        if part1:
            block = strip_heading(part1.group(1))
            writing = clean(block)
            quote = re.search(r'begins with the sentence\s*[“"](.+?)[”"]', writing)
            if quote:
                sentence = quote.group(1).strip()
        part4 = re.search(r"## Part IV\b(.+?)(?=\n## |\Z)", text, re.S)
        if part4:
            translation = clean(strip_directions(strip_heading(part4.group(1))))
        exams.append({"year": year, "month": month, "set": set_no, "writing": writing,
                      "sentence": sentence, "theme": theme, "translation": translation})
    return exams


def corpus_writing() -> list[dict]:
    if not CORPUS_WRITE.exists():
        return []
    text = CORPUS_WRITE.read_text(encoding="utf-8")
    items = []
    for block in re.split(r"\n### ", text):
        match = re.search(r'<a id="(\d{4})(\d{2})-第(\d)套"></a>第 (\d) 套', block)
        if not match:
            continue
        year, month, set_no = int(match.group(1)), int(match.group(2)), int(match.group(3))
        directions = ""
        sentence = ""
        theme = ""
        dir_match = re.search(r"\*\*Directions:\*\*\s*(.+)", block)
        if dir_match:
            directions = clean(dir_match.group(1))
        if not directions:
            # 个别套次没有 Directions 段落，用整块清理后的文本兜底
            fallback = clean(re.sub(r"^.*?</a>.*?\n", "", block, count=1, flags=re.S))
            fallback = re.sub(r"^第 \d+ 套( — .*?)?\s*", "", fallback).strip()
            directions = fallback[:600]
        sen_match = re.search(r"\*\*给定首句：\*\*\s*(.+)", block)
        if sen_match:
            sentence = clean(sen_match.group(1))
        if not sentence:
            quote = re.search(r'begins with the sentence \*?"(.+?)"\*?', block, re.S)
            if quote:
                sentence = quote.group(1).strip()
        theme_match = re.search(r"\*\*主题：\*\*\s*(.+)", block)
        if theme_match:
            theme = clean(theme_match.group(1))
        items.append({"year": year, "month": month, "set": set_no, "directions": directions,
                      "sentence": sentence, "theme": theme})
    return items


def corpus_translation() -> list[dict]:
    if not CORPUS_TRANS.exists():
        return []
    text = CORPUS_TRANS.read_text(encoding="utf-8")
    items = []
    for block in re.split(r"\n### ", text):
        match = re.search(r'<a id="(\d{4})(\d{2})-第(\d)套"></a>第 (\d) 套(?: — (.+))?', block)
        if not match:
            continue
        year, month, set_no = int(match.group(1)), int(match.group(2)), int(match.group(3))
        theme = clean(match.group(5) or "")
        body = re.sub(r"^.*?</a>.*?\n", "", block, count=1, flags=re.S)
        body = re.sub(r"^第 \d+ 套( — .*?)?\n", "", body)
        body = re.split(r"\n-{3,}|\n## ", body)[0]
        body = clean(body)
        if len(body) < 40:
            continue
        items.append({"year": year, "month": month, "set": set_no, "theme": theme, "chinese": body})
    return items


def authored() -> dict:
    """人工 / 子代理撰写的范文与参考译文：content/raw/authored/*.json。"""
    folder = RAW / "authored"
    merged: dict = {"writing": {}, "translation": {}}
    if not folder.exists():
        return merged
    for path in sorted(folder.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for key in ("writing", "translation"):
            merged[key].update(payload.get(key, {}) or {})
    return merged


def build() -> None:
    authored_data = authored()
    exams = exam_sections()

    writing, translation = [], []
    for exam in exams:
        key = f"{exam['year']}-{exam['month']:02d}-{exam['set']}"
        wid = f"{key}-writing"
        extra = authored_data["writing"].get(wid, {})
        writing.append({
            "id": wid, "label": label(exam["year"], exam["month"], exam["set"]),
            "year": exam["year"], "month": exam["month"], "set": exam["set"],
            "title": f"{exam['year']}年{exam['month']}月六级作文（第{exam['set']}套）",
            "directions": exam["writing"] or "Directions 解析失败",
            "sentence": exam["sentence"],
            "theme": extra.get("theme", ""),
            "minutes": 30,
            "source": "wamich/english-exem-md（真题原文）",
            "outline": extra.get("outline", []),
            "expressions": extra.get("expressions", []),
            "words": extra.get("words", []),
            "sample": extra.get("sample", ""),
            "sample_zh": extra.get("sample_zh", ""),
        })
        tid = f"{key}-translation"
        extra_t = authored_data["translation"].get(tid, {})
        chinese = exam["translation"] or "原文解析失败"
        for old, new in CORRECTIONS.get(tid, []):
            chinese = chinese.replace(old, new)
        translation.append({
            "id": tid, "label": label(exam["year"], exam["month"], exam["set"]),
            "year": exam["year"], "month": exam["month"], "set": exam["set"],
            "title": extra_t.get("title", f"{exam['year']}年{exam['month']}月六级翻译（第{exam['set']}套）"),
            "chinese": chinese,
            "minutes": 30,
            "source": "wamich/english-exem-md（真题原文）",
            "reference": extra_t.get("reference", ""),
            "points": extra_t.get("points", []),
            "words": extra_t.get("words", []),
        })

    have = {(item["year"], item["month"], item["set"]) for item in writing}
    for item in corpus_writing():
        if (item["year"], item["month"], item["set"]) in have:
            continue
        key = f"{item['year']}-{item['month']:02d}-{item['set']}"
        writing.append({
            "id": f"{key}-writing", "label": label(item["year"], item["month"], item["set"]),
            "year": item["year"], "month": item["month"], "set": item["set"],
            "title": f"{item['year']}年{item['month']}月六级作文（第{item['set']}套）",
            "directions": item["directions"], "sentence": item["sentence"],
            "theme": item["theme"], "minutes": 30,
            "source": "xzyj50609/cet6-translation-writing-corpus（真题 Directions）",
            "outline": [], "expressions": [], "words": [], "sample": "", "sample_zh": "",
        })

    have = {(item["year"], item["month"], item["set"]) for item in translation}
    for item in corpus_translation():
        if (item["year"], item["month"], item["set"]) in have:
            continue
        key = f"{item['year']}-{item['month']:02d}-{item['set']}"
        translation.append({
            "id": f"{key}-translation", "label": label(item["year"], item["month"], item["set"]),
            "year": item["year"], "month": item["month"], "set": item["set"],
            "title": item["theme"] or f"{item['year']}年{item['month']}月六级翻译（第{item['set']}套）",
            "chinese": item["chinese"], "minutes": 30,
            "source": "xzyj50609/cet6-translation-writing-corpus（真题原文）",
            "reference": "", "points": [], "words": [],
        })

    writing.sort(key=lambda x: (x["year"], x["month"], x["set"]), reverse=True)
    translation.sort(key=lambda x: (x["year"], x["month"], x["set"]), reverse=True)
    OUT_WRITING.write_text(json.dumps(writing, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_TRANSLATION.write_text(json.dumps(translation, ensure_ascii=False, indent=1), encoding="utf-8")
    with_sample = sum(1 for item in writing if item["sample"])
    with_ref = sum(1 for item in translation if item["reference"])
    print(f"作文 {len(writing)} 套（含范文 {with_sample}）→ {OUT_WRITING.name}")
    print(f"翻译 {len(translation)} 套（含参考译文 {with_ref}）→ {OUT_TRANSLATION.name}")
    missing = [item for item in writing if not item["sentence"]]
    if missing:
        print("缺少给定首句：", [item["id"] for item in missing])


if __name__ == "__main__":
    build()
