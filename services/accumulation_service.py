"""积累本业务规则（重构设计方案 §7）。

一级导航里的独立模块：作文句式、主题词汇、翻译表达、我的笔记。
每条包含使用场景、可替换部分和示例，避免只背空泛模板。
"""
from __future__ import annotations

CATEGORIES = ("作文句式", "主题词汇", "翻译表达", "教育", "科技", "文化", "环境", "社会", "经济", "我的笔记")


class AccumulationService:
    def __init__(self, store, seed: list[dict] | None = None):
        self.store = store
        self.seed = seed or []

    def all_items(self) -> list[dict]:
        items = [dict(item, builtin=True) for item in self.seed]
        items.extend(dict(item, builtin=False) for item in self.store.accumulation())
        return items

    def filter(self, query: str = "", category: str = "全部", starred_only: bool = False) -> list[dict]:
        query = (query or "").strip().lower()
        result = []
        for item in self.all_items():
            if category != "全部" and item.get("category") != category:
                continue
            if starred_only and not item.get("starred"):
                continue
            haystack = " ".join(str(item.get(key, "")) for key in
                                ("title", "pattern", "scene", "example", "example_zh", "category", "source", "note"))
            if query and query not in haystack.lower():
                continue
            result.append(item)
        return sorted(result, key=lambda x: (not x.get("starred"), x.get("category", ""), x.get("title", "")))

    def categories(self) -> list[str]:
        present = {item.get("category", "我的笔记") for item in self.all_items()}
        return ["全部"] + [name for name in CATEGORIES if name in present]

    def add(self, item: dict) -> str:
        return self.store.add_accumulation(item)

    def update(self, item_id: str, **fields) -> None:
        self.store.update_accumulation(item_id, **fields)

    def remove(self, item_id: str) -> None:
        self.store.remove_accumulation(item_id)

    def toggle_star(self, item_id: str) -> bool:
        for item in self.store.accumulation():
            if item.get("id") == item_id:
                item["starred"] = not item.get("starred", False)
                self.store.save()
                return item["starred"]
        return False

    def review_queue(self, limit: int = 20) -> list[dict]:
        items = [item for item in self.all_items() if item.get("starred")] or self.all_items()
        return items[:limit]

    def counts(self) -> dict:
        counts: dict[str, int] = {}
        for item in self.all_items():
            counts[item.get("category", "我的笔记")] = counts.get(item.get("category", "我的笔记"), 0) + 1
        return counts
