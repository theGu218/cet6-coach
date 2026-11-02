"""词库清洗：去重 + 清掉 short_meaning 里的残留物（& / h· / 行内音标 / || 习语 / 序号）。

背景：第一版词库由早期脚本从大纲词表拼出来，short_meaning 里混进了多词性标记 `&`、
残破的 `h·`、以及 `[ˈædvəkɪt]` 这类行内音标；有的词 short_meaning 干脆就是 `&`，
选择题干扰项取到这些词时就会露出垃圾。

用法：
    python tools/fix_vocabulary.py          # 清洗并写回 content/vocabulary.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "content" / "vocabulary.json"
TIER_RANK = {"高频核心": 0, "六级拓展": 1, "基础回顾": 2}
SHORT_LIMIT = 18

# 源词表本身的缺字/错标，逐条修正（只收录能确定原文的）
KNOWN_FIXES = {
    "articulate": {"short_meaning": "清楚明白地表达",
                   "meaning": "1. 清楚明白地表达 2. 用关节连接"},
}


def normalize_phonetic(text: str) -> str:
    """把音标里的 ASCII 写法换成 IPA 记号。"""
    text = (text or "").strip()
    text = text.replace("‚", "ˌ").replace("'", "ˈ").replace(":", "ː")
    return text


def clean_text(text: str) -> str:
    """去掉音标、&、h·、中点，压缩空白。"""
    text = text or ""
    text = re.sub(r"\[[^\]]*\]", " ", text)        # 行内音标
    text = text.replace("&", " ")
    text = text.replace("h·", "").replace("·", " ")  # 残破词性标记
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,，;；。:：")


def clean_full_meaning(text: str) -> str:
    """完整释义：保留习语，但把 `||` 换成全角竖线。"""
    text = clean_text(text)
    text = re.sub(r"\s*\|{2,}\s*", " ｜ ", text)
    text = re.sub(r"\s*(\d+)[\.、]\s*", r" \1. ", text)
    return re.sub(r"\s+", " ", text).strip()


def first_sense(text: str, limit: int = SHORT_LIMIT) -> str:
    """取第一个义项，截到适合做选项的长度。"""
    text = clean_text(text)
    if not text:
        return ""
    # 只留第一个义项：先按习语/分号切，再按 "1. 2." 编号切
    first = re.split(r"\s*(?:\|\||；|;)\s*", text)[0]
    first = re.split(r"\s+(?=\d+[\.、]\s*)", first)[0]
    first = re.sub(r"^\s*\d+[\.、]\s*", "", first).strip()
    if len(first) > limit:
        head = first[:limit]
        cut = max(head.rfind("，"), head.rfind(","), head.rfind("、"))
        first = head[:cut] if cut >= 4 else head
    return first.strip(" ,，;；。、")


def clean_word(word: dict) -> dict:
    full = clean_full_meaning(word.get("meaning", ""))
    short_raw = word.get("short_meaning", "")
    short = first_sense(short_raw) or first_sense(full)
    if not short:
        short = full[:SHORT_LIMIT]
    word["meaning"] = full
    word["short_meaning"] = short
    word["phonetic"] = normalize_phonetic(word.get("phonetic", ""))
    fix = KNOWN_FIXES.get(word.get("word", ""))
    if fix:
        word.update(fix)
    return word


def main() -> None:
    words = json.loads(PATH.read_text(encoding="utf-8"))
    before = json.dumps(words, ensure_ascii=False)

    # 1) 去重：同名单词保留信息最全的一条
    best: dict[str, dict] = {}
    order: list[str] = []
    for word in words:
        key = (word.get("word") or "").strip().lower()
        if not key:
            continue
        current = best.get(key)
        if current is None:
            best[key] = word
            order.append(key)
            continue
        score_new = (bool(word.get("example")), -TIER_RANK.get(word.get("tier", ""), 9))
        score_old = (bool(current.get("example")), -TIER_RANK.get(current.get("tier", ""), 9))
        if score_new > score_old:
            best[key] = word
    result = [clean_word(best[key]) for key in order]
    for index, word in enumerate(result, 1):
        word["id"] = f"cet6-{index:04d}"

    PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2) 报告
    dirty = [w for w in result if re.search(r"[&\[\]]|h·|\|\|", w["short_meaning"])]
    too_long = [w for w in result if len(w["short_meaning"]) > SHORT_LIMIT + 6]
    too_short = [w for w in result if len(w["short_meaning"]) < 2]
    print(f"词条 {len(words)} → {len(result)}（去重 {len(words) - len(result)}）")
    print(f"short_meaning 残留脏字符：{len(dirty)}")
    print(f"short_meaning 超长：{len(too_long)}，过短：{len(too_short)}")
    changed = before != PATH.read_text(encoding="utf-8")
    print("内容有变化" if changed else "内容无变化")
    for word in ("articulate", "whereas", "advocate", "intuition", "design", "glitter"):
        found = next((w for w in result if w["word"] == word), None)
        if found:
            print(f"  {word:12} → {found['short_meaning']}　（完整：{found['meaning'][:50]}）")


if __name__ == "__main__":
    main()
