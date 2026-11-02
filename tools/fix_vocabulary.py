"""词库去重：同名单词只保留信息最全的一条（优先带例句、较高分层）。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "content" / "vocabulary.json"
TIER_RANK = {"高频核心": 0, "六级拓展": 1, "基础回顾": 2}


def main() -> None:
    words = json.loads(PATH.read_text(encoding="utf-8"))
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
    result = [best[key] for key in order]
    for index, word in enumerate(result, 1):
        word["id"] = f"cet6-{index:04d}"
    PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"去重后 {len(result)} 词（原 {len(words)}）")
    tiers = {}
    for word in result:
        tiers[word.get("tier")] = tiers.get(word.get("tier"), 0) + 1
    print("分层：", tiers)


if __name__ == "__main__":
    main()
