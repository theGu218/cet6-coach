"""词汇复习业务规则（重构设计方案 §5）。

核心原则：
- 掌握不能靠一次“认识”，需要在不同学习日多次检测 + 语境检测；
- 初期间隔 1、2、4、7、15、30 天，按答题表现调整；
- 答错不清零历史，进入“待巩固”并当天重新到期；
- 三种题型按阶段解锁：英译汉 → 汉译英 → 语境选择。
"""
from __future__ import annotations

import random
import re
from datetime import date, timedelta

MODES = ("en_zh", "zh_en", "context")
MODE_NAMES = {"en_zh": "英译汉", "zh_en": "汉译英", "context": "语境选择"}
MODE_STAGE = {"en_zh": 1, "zh_en": 2, "context": 3}
INTERVALS = (1, 2, 4, 7, 15, 30)
MASTERED_INTERVAL = 30
TIER_ORDER = ("高频核心", "基础回顾", "六级拓展")


class VocabularyService:
    def __init__(self, words: list[dict], store):
        self.words = words
        self.by_word = {word["word"].lower(): word for word in words}
        self.store = store

    # ---------------- 状态 ----------------
    def state(self, word: str) -> dict:
        return self.store.word_state(word)

    def item(self, word: str) -> dict | None:
        return self.by_word.get(word.lower())

    def next_mode(self, word: str) -> str:
        state = self.state(word)
        item = self.item(word)
        stage = state.get("stage", 0)
        if item is None:
            return "en_zh"
        if stage >= 2 and item.get("example"):
            return "context"
        if stage >= 1:
            return "zh_en"
        return "en_zh"

    # ---------------- 三个队列 ----------------
    def due_words(self, today: str | None = None, rng: random.Random | None = None) -> list[dict]:
        """到期旧词：到期日早的先复习；**同一天到期**的组内随机，避免按字母序出题。"""
        today = today or date.today().isoformat()
        rng = rng or random
        due = []
        for item in self.words:
            state = self.state(item["word"])
            if not state.get("seen"):
                continue
            if state.get("reduced") and not state.get("needs_review"):
                continue
            if (state.get("next_review") or today) <= today:
                due.append(item)
        due.sort(key=lambda x: self.state(x["word"]).get("next_review", ""))
        buckets: dict[str, list[dict]] = {}
        for item in due:
            day = self.state(item["word"]).get("next_review", "")
            buckets.setdefault(day, []).append(item)
        result: list[dict] = []
        for day in sorted(buckets):
            group = buckets[day]
            rng.shuffle(group)
            result.extend(group)
        return result

    def new_words(self, limit: int = 20, rng: random.Random | None = None) -> list[dict]:
        """新词按层优先（高频核心 → 基础回顾 → 六级拓展），层内**随机**取，
        避免总是按 abcd 字母序出题、让人能靠位置猜。"""
        if limit <= 0:
            return []
        rng = rng or random
        result: list[dict] = []
        for tier in TIER_ORDER:
            pool = []
            for item in self.words:
                if item.get("tier") != tier:
                    continue
                state = self.state(item["word"])
                if state.get("seen") or state.get("reduced"):
                    continue
                pool.append(item)
            rng.shuffle(pool)
            for item in pool:
                result.append(item)
                if len(result) >= limit:
                    return result
        return result

    def wrong_words(self) -> list[dict]:
        """待强化错词：**最近答错**的排前面，其次按累计答错次数。"""
        items = [item for item in self.words if self.state(item["word"]).get("needs_review")]

        def sort_key(item: dict) -> tuple[str, int]:
            state = self.state(item["word"])
            return (state.get("last_wrong") or "", state.get("wrong_count", 0))

        return sorted(items, key=sort_key, reverse=True)

    def starred_words(self) -> list[dict]:
        return [item for item in self.words if self.store.is_starred(item["word"])]

    def daily_queue(self) -> list[dict]:
        """最近错词 → 更早的错词 → 到期旧词 → 打乱后的新词。

        复习部分（错词 + 到期旧词）受「每日复习上限」限制（默认 60），新词按
        「每日新词」单独配额，两者不叠成无上限的 100+ 题。
        """
        review_limit = int(self.store.settings.get("daily_review_limit", 60))
        # 当天已经学过的新词要从配额里扣掉，否则学完 20 个又会推 20 个新的
        new_limit = max(0, int(self.store.settings.get("daily_words", 20))
                        - int(self.store.activity_today().get("new_words", 0)))
        queue: list[dict] = []
        seen: set[str] = set()

        def push(items, cap: int | None = None) -> None:
            for item in items:
                if cap is not None and len(queue) >= cap:
                    return
                key = item["word"].lower()
                if key in seen:
                    continue
                seen.add(key)
                queue.append(item)

        push(self.wrong_words(), cap=review_limit)
        push(self.due_words(), cap=review_limit)
        push(self.new_words(new_limit))
        return queue

    # ---------------- 出题 ----------------
    def make_question(self, item: dict, mode: str | None = None, rng: random.Random | None = None) -> dict:
        rng = rng or random
        word = item["word"]
        mode = mode or self.next_mode(word)
        if mode == "context" and not item.get("example"):
            mode = "zh_en"
        if mode == "en_zh":
            prompt = word
            sub = f"{item.get('phonetic', '')}　{item.get('pos', '')}"
            correct = item.get("short_meaning") or item["meaning"]
            pool = [w for w in self._same_pos(word) if (w.get("short_meaning") or w.get("meaning")) != correct]
            distractors = self._pick(pool, "short_meaning", correct, rng)
            options = [correct] + distractors
        elif mode == "zh_en":
            prompt = (item.get("short_meaning") or item.get("meaning") or "").strip()
            if self._leaks_answer(prompt, word):
                # 释义里混进了目标单词（脏数据）会让题干直接等于答案，降级成英译汉
                return self.make_question(item, "en_zh", rng)
            sub = f"{item.get('pos', '')} · 选择对应的英文单词"
            correct = word
            distractors = self._pick(self._same_pos(word), "word", correct, rng)
            options = [correct] + distractors
        else:
            example = item.get("example") or ""
            blank = self._blank_out(example, word)
            if blank == example:
                mode = "zh_en"
                return self.make_question(item, "zh_en", rng)
            prompt = blank
            sub = "根据句意，选择最合适的单词填空"
            correct = word
            pool = [w for w in self._same_pos(word) if w.get("example")]
            if len(pool) < 3:
                pool = self._same_pos(word)
            distractors = self._pick(pool, "word", correct, rng)
            options = [correct] + distractors
        rng.shuffle(options)
        return {
            "word": word, "mode": mode, "mode_name": MODE_NAMES[mode],
            "prompt": prompt, "sub": sub, "options": options,
            "answer": options.index(correct), "correct": correct,
            "example": item.get("example", ""), "example_zh": item.get("example_zh", ""),
            "meaning": item["meaning"], "pos": item.get("pos", ""),
            "phonetic": item.get("phonetic", ""),
        }

    @staticmethod
    def _leaks_answer(prompt: str, word: str) -> bool:
        """题干里是否已经出现了目标单词（汉译英题不应该出现）。"""
        if not prompt:
            return True
        pattern = r"(?<![a-z])" + re.escape(word.lower()) + r"(?![a-z])"
        return re.search(pattern, prompt.lower()) is not None

    def _same_pos(self, word: str) -> list[dict]:
        base = self.item(word) or {}
        pos = set((base.get("pos") or "").replace("，", " ").split())
        pool = []
        for other in self.words:
            if other["word"].lower() == word.lower():
                continue
            other_pos = set((other.get("pos") or "").replace("，", " ").split())
            if not pos or not other_pos or pos & other_pos:
                pool.append(other)
        return pool

    @staticmethod
    def _blank_out(example: str, word: str) -> str:
        pattern = re.compile(r"\b" + re.escape(word) + r"\w*\b", re.I)
        return pattern.sub("______", example, count=1)

    def _pick(self, pool: list[dict], key: str, correct: str, rng: random.Random,
              count: int = 3) -> list[str]:
        """挑干扰项：同词性优先、长度接近正确答案，避免一眼能排除的选项。"""
        def value_of(item: dict) -> str:
            return (item.get(key) or item.get("meaning") or "").strip()

        correct = (correct or "").strip()
        candidates: list[str] = []
        seen = {correct}
        for item in pool:
            value = value_of(item)
            if not value or value in seen:
                continue
            if len(value) < 2 or len(value) > 26:      # 太短/太长都不适合做选项
                continue
            if correct and (value in correct or correct in value):
                continue                                  # 包含关系容易变成送分题
            seen.add(value)
            candidates.append(value)

        rng.shuffle(candidates)
        correct_len = len(correct)
        near = [value for value in candidates if abs(len(value) - correct_len) <= 8]
        far = [value for value in candidates if value not in near]
        picked = (near + far)[:count]

        if len(picked) < count:  # 同词性词太少时，从全词库补
            for item in self.words:
                value = value_of(item)
                if value and value not in picked and value != correct:
                    picked.append(value)
                if len(picked) >= count:
                    break
        return picked

    # ---------------- 记录答题 ----------------
    def record(self, word: str, mode: str, correct: bool, chosen: str,
               on_date: str | None = None) -> dict:
        today = on_date or date.today().isoformat()
        state = self.state(word)
        first = not state.get("seen")
        state["seen"] = state.get("seen", 0) + 1
        state["last_seen"] = today
        state["last_result"] = correct
        stats = state.setdefault("mode_stats", {}).setdefault(mode, {"correct": 0, "wrong": 0})
        stats["correct" if correct else "wrong"] += 1

        if correct:
            state["correct"] = state.get("correct", 0) + 1
            days = state.setdefault("correct_days", [])
            if today not in days:
                days.append(today)
            expected = MODE_STAGE[mode]
            state["stage"] = max(state.get("stage", 0), expected)
            state["successful_reviews"] = state.get("successful_reviews", 0) + 1
            # 答对即退出错词队列：之前只统计不改标记，导致旧错词答对十遍仍天天出现
            state["needs_review"] = False
            if mode == "context":
                state["context_passed"] = True
            mastered = (state.get("context_passed") and len(days) >= 3
                        and state.get("correct", 0) >= 4 and state.get("stage", 0) >= 3)
            if mastered:
                state["status"] = "已掌握"
                state["stage"] = 4
                state["needs_review"] = False
                interval = MASTERED_INTERVAL
            else:
                state["status"] = "待复习"
                interval = INTERVALS[min(state["successful_reviews"] - 1, len(INTERVALS) - 1)]
            state["next_review"] = (date.fromisoformat(today) + timedelta(days=interval)).isoformat()
        else:
            state["wrong_count"] = state.get("wrong_count", 0) + 1
            state["last_wrong_answer"] = chosen
            state["last_wrong"] = today
            state["needs_review"] = True
            state["status"] = "待巩固" if state.get("correct", 0) else "学习中"
            if mode == "context":
                state["stage"] = max(1, state.get("stage", 1) - 1)
                state["context_passed"] = False
            state["next_review"] = today
            history = self.store.data.setdefault("word_history", {}).setdefault(word, [])
            history.append({"date": today, "mode": mode, "chosen": chosen})
            self.store.data["word_history"][word] = history[-20:]

        self.store.set_word_state(word, state)
        self.store.touch("words")
        self.store.touch("new_words" if first else "reviews")
        self.store.save()
        return state

    def set_reduced(self, word: str, reduced: bool = True) -> None:
        state = self.state(word)
        state["reduced"] = reduced
        self.store.set_word_state(word, state)
        self.store.save()

    def toggle_star(self, word: str) -> bool:
        return self.store.toggle_star(word)

    # ---------------- 统计 ----------------
    def summary(self) -> dict:
        today = date.today().isoformat()
        states = [self.state(item["word"]) for item in self.words]
        return {
            "total": len(self.words),
            "mastered": sum(1 for s in states if s.get("status") == "已掌握"),
            "learning": sum(1 for s in states if s.get("status") in ("学习中", "待巩固")),
            "due": len(self.due_words(today)),
            "wrong": sum(1 for s in states if s.get("needs_review")),
            "new_today": self.store.activity_today().get("new_words", 0),
            "reviews_today": self.store.activity_today().get("reviews", 0),
        }
