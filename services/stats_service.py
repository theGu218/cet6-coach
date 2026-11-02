"""统计与复盘的业务口径（重构设计方案 §6 错题复盘、§11 验收）。"""
from __future__ import annotations


class StatsService:
    def __init__(self, store, vocab, reading):
        self.store = store
        self.vocab = vocab
        self.reading = reading

    def overview(self) -> dict:
        base = self.store.stats()
        vocab = self.vocab.summary()
        by_kind = self.reading.accuracy_by_kind()
        totals = [total for _, total in by_kind.values() if total]
        return {
            **base,
            "vocab": vocab,
            "reading_accuracy": round(sum(by_kind[k][0] * by_kind[k][1] for k in by_kind) / sum(totals)) if totals else 0,
            "reading_answered": sum(totals),
            "by_kind": by_kind,
            "by_reason": self.reading.accuracy_by_reason(),
            "weekly": self.store.activity_series(7),
            "tasks_done": self.tasks_done(),
        }

    def tasks_done(self) -> dict:
        today = self.store.activity_today()
        due = self.vocab.due_words()
        return {
            "reviews": bool(today.get("reviews")),
            "new_words": today.get("new_words", 0),
            "new_words_target": int(self.store.settings.get("daily_words", 20)),
            "reading": bool(today.get("questions")),
            "due_left": len(due),
        }

    def recent_sessions(self, limit: int = 20) -> list[dict]:
        return self.store.sessions(limit)

    def weak_points(self) -> list[dict]:
        """按错误原因排序，给出下一步建议。"""
        reasons = self.reading.accuracy_by_reason()
        total = sum(reasons.values())
        items = []
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            if not count:
                continue
            share = round(count / total * 100)
            advice = {
                "词汇不懂": "回到核心词汇，把错题里的生词加入生词本，按 1/2/4/7 天复习。",
                "句子不懂": "先做长难句拆解：找主干、划从句，再回原文核对。",
                "定位错误": "练习先用题干关键词定位段落，再逐句比对，不要凭印象选。",
                "逻辑误判": "复盘时刻意区分“原文说了”与“我推测的”，重点看转折与让步。",
                "粗心": "交卷前留 2 分钟检查：题干问的是哪个对象、是否否定。",
            }.get(reason, "重做该类错题，并记录这次错在哪里。")
            items.append({"reason": reason, "count": count, "share": share, "advice": advice})
        return items
