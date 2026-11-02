"""学习记录的持久化层。

设计要点（对应重构设计方案 §10）：
- 保持用户数据目录 %APPDATA%\\CET6Coach 不变；
- 新增 schema 版本，升级前自动备份旧文件；
- 先继续使用 JSON（原子写入），需要时再迁移 SQLite。

数据分三块：
- 词汇：每个词的复习状态（阶段、间隔、错词历史、下次复习日期）
- 阅读：每套真题的作答记录、错题与错误原因标签
- 其他：作文 / 翻译草稿、积累本、学习活动、设置
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

APP_NAME = "CET6Coach"
SCHEMA = 3


def resource_path(name: str) -> Path:
    """打包成 EXE 后，资源在 _MEIPASS 下。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / name


def _candidates() -> list[Path]:
    """数据目录候选：优先 %APPDATA%，不可写时退回程序目录（便携/受限环境）。

    有些环境（受控文件夹、受限权限、从沙箱界面启动）会拒绝写 %APPDATA%，
    这时直接崩在启动阶段是最糟的结果——宁可换个目录，也要让软件能用。
    """
    roots = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / APP_NAME)
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    roots.append(base / "data")
    roots.append(Path.home() / "CET6Coach")
    return roots


_DATA_DIR: Path | None = None


def dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def user_data_dir() -> Path:
    global _DATA_DIR
    if _DATA_DIR is not None:
        return _DATA_DIR
    for candidate in _candidates():
        if dir_writable(candidate):
            _DATA_DIR = candidate
            return candidate
    _DATA_DIR = _candidates()[0]
    return _DATA_DIR


def today_str() -> str:
    return date.today().isoformat()


def now_str() -> str:
    return datetime.now().isoformat(timespec="seconds")


EMPTY_WORD_STATE = {
    "status": "未学",          # 未学 / 学习中 / 待复习 / 已掌握
    "stage": 0,                # 0 未学 1 认识词义 2 主动回忆 3 语境运用 4 已掌握
    "seen": 0,
    "correct": 0,
    "wrong_count": 0,
    "correct_days": [],
    "successful_reviews": 0,
    "mode_stats": {},
    "next_review": "",
    "last_seen": "",
    "last_result": None,
    "last_wrong_answer": "",
    "context_passed": False,
    "needs_review": False,
    "reduced": False,
}


def _normalize_word(state: dict | None) -> dict:
    """把老版本（level / needs_review / 无 stage）的词汇状态补齐成 v3。"""
    merged = dict(EMPTY_WORD_STATE)
    merged.update({k: v for k, v in (state or {}).items() if v is not None})
    if "level" in (state or {}):
        level = int(state.get("level") or 0)
        merged["stage"] = {0: 0, 1: 1, 2: 2}.get(level, 3 if level < 5 else 4)
        merged["status"] = merged.get("status") if merged.get("status") not in (None, "", "未学") else (
            "已掌握" if level >= 5 else ("待复习" if level >= 3 else ("学习中" if level else "未学")))
        merged["successful_reviews"] = max(int(merged.get("successful_reviews") or 0), level)
        del merged["level"]
    if merged["needs_review"] and merged["status"] == "未学":
        merged["status"] = "学习中"
    return merged


class ProgressStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else user_data_dir() / "progress.json"
        self.migrated_from = 0
        self.backup_failed = False
        self.save_failed = False
        self.read_path = self.path
        # 目标目录可能是“退而求其次”的可写目录；旧记录仍读 %APPDATA% 里的那份
        appdata = os.environ.get("APPDATA")
        if path is None and appdata:
            legacy = Path(appdata) / APP_NAME / "progress.json"
            if legacy != self.path and legacy.exists():
                self.read_path = legacy
        self.data = self._load()

    # ---------------- 载入 / 保存 ----------------
    def _defaults(self) -> dict:
        return {
            "schema": SCHEMA,
            "settings": {
                "user_name": "同学",
                "daily_words": 20,
                "study_minutes": 75,
                "reading_minutes": 35,
                "new_word_mode": "三阶段",
            },
            "words": {},
            "starred": [],
            "wrong_questions": {},
            "word_history": {},
            "sessions": [],
            "writings": {},
            "translations": {},
            "activity": {},
            "accumulation": [],
            "reading": {},
            "error_tags": {},
            "imported_words": [],
            "imported_exams": [],
            "meta": {"created": now_str()},
        }

    def _load(self) -> dict:
        data = self._defaults()
        source = getattr(self, "read_path", self.path)
        if not source.exists():
            return data
        try:
            raw = source.read_text(encoding="utf-8")
        except OSError:
            return data
        try:
            saved = json.loads(raw)
        except ValueError:
            # 文件损坏：保留现场，避免覆盖用户数据
            if source == self.path:
                broken = self.path.with_name(f"progress_broken_{datetime.now():%Y%m%d%H%M%S}.json")
                try:
                    self.path.replace(broken)
                except OSError:
                    pass
            return data
        version = int(saved.get("schema") or saved.get("version") or 1)
        if version < SCHEMA:
            self.migrated_from = version
            backup = source.with_name(f"progress_v{version}_backup.json")
            if not backup.exists():
                try:
                    backup.write_text(raw, encoding="utf-8")
                except OSError:
                    # 受限环境：放弃备份但不阻断启动（旧文件仍在原处，不会被覆盖）
                    self.backup_failed = True
        for key, value in saved.items():
            if key in ("version", "schema"):
                continue
            if key == "settings" and isinstance(value, dict):
                data["settings"].update(value)
            else:
                data[key] = value
        # v1/v2 → v3 字段改名
        if "word_status" in saved:
            data["words"] = saved["word_status"]
        if "starred_words" in saved:
            data["starred"] = saved["starred_words"]
        if "reading_error_tags" in saved:
            data["error_tags"] = saved["reading_error_tags"]
        if "reading_completed" in saved and not saved.get("reading"):
            data["reading"] = saved["reading_completed"]
        data["schema"] = SCHEMA
        data["words"] = {word: _normalize_word(state) for word, state in (data.get("words") or {}).items()}
        data["meta"] = {**data.get("meta", {}), "created": data.get("meta", {}).get("created", now_str())}
        if self.migrated_from:
            data["meta"]["migrated_from"] = self.migrated_from
            data["meta"]["migrated_at"] = now_str()
        return data

    def save(self) -> None:
        """保存；失败时自动换一个可写目录重试，仍失败则只标记不中断使用。"""
        payload = json.dumps(self.data, ensure_ascii=False, indent=1)
        for attempt in (0, 1):
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix(".tmp")
                temp.write_text(payload, encoding="utf-8")
                temp.replace(self.path)
                self.save_failed = False
                return
            except OSError:
                if attempt:
                    break
                for candidate in _candidates():
                    if dir_writable(candidate):
                        self.path = candidate / self.path.name
                        break
        self.save_failed = True

    # ---------------- 设置与活动 ----------------
    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def update_settings(self, **kwargs) -> None:
        self.data["settings"].update(kwargs)
        self.save()

    def activity_today(self) -> dict:
        return self.data["activity"].setdefault(
            today_str(), {"minutes": 0, "words": 0, "questions": 0, "new_words": 0, "reviews": 0})

    def touch(self, field: str, amount: int = 1) -> None:
        bucket = self.activity_today()
        bucket[field] = bucket.get(field, 0) + amount

    def activity_series(self, days: int = 7) -> list[dict]:
        out = []
        for i in range(days - 1, -1, -1):
            day = date.today() - timedelta(days=i)
            bucket = self.data["activity"].get(day.isoformat(), {})
            out.append({
                "date": day.isoformat(),
                "label": "一二三四五六日"[day.weekday()],
                "minutes": bucket.get("minutes", 0),
                "words": bucket.get("words", 0),
                "questions": bucket.get("questions", 0),
                "value": bucket.get("minutes", 0) + bucket.get("words", 0) + bucket.get("questions", 0),
            })
        return out

    def streak(self) -> int:
        streak = 0
        day = date.today()
        while True:
            if day.isoformat() in self.data["activity"]:
                streak += 1
            elif day == date.today():
                pass
            else:
                break
            day -= timedelta(days=1)
            if streak > 3650:
                break
        return streak

    def minutes_today(self) -> int:
        return self.activity_today().get("minutes", 0)

    def total_minutes(self) -> int:
        return sum(item.get("minutes", 0) for item in self.data["activity"].values())

    # ---------------- 词汇 ----------------
    def word_state(self, word: str) -> dict:
        return dict(_normalize_word(self.data["words"].get(word)))

    def set_word_state(self, word: str, state: dict) -> None:
        self.data["words"][word] = _normalize_word(state)

    def word_states(self) -> dict:
        return self.data["words"]

    def toggle_star(self, word: str) -> bool:
        starred = self.data.setdefault("starred", [])
        if word in starred:
            starred.remove(word)
            self.save()
            return False
        starred.append(word)
        self.save()
        return True

    def is_starred(self, word: str) -> bool:
        return word in self.data.get("starred", [])

    # ---------------- 阅读 ----------------
    def reading_record(self, exam_id: str) -> dict:
        return self.data["reading"].setdefault(
            exam_id, {"attempts": 0, "last": "", "cloze": {}, "matching": {}, "careful": {}, "best": {}})

    def save_reading_record(self, exam_id: str, record: dict) -> None:
        self.data["reading"][exam_id] = record
        self.save()

    def record_answer(self, question_key: str, prompt: str, answer: str, chosen: str,
                      correct: bool, category: str, *, exam_id: str = "", qid: str = "") -> None:
        wrong = self.data["wrong_questions"]
        if correct:
            wrong.pop(question_key, None)
        else:
            old = wrong.get(question_key, {})
            wrong[question_key] = {
                "question_id": question_key, "exam_id": exam_id, "qid": qid,
                "prompt": prompt, "answer": answer, "chosen": chosen, "category": category,
                "wrong_count": old.get("wrong_count", 0) + 1, "updated": now_str(),
            }
        self.touch("questions")
        self.save()

    def set_error_tag(self, question_key: str, tag: str) -> None:
        self.data["error_tags"][question_key] = tag
        self.save()

    def error_tag(self, question_key: str) -> str:
        return self.data["error_tags"].get(question_key, "")

    def add_session(self, category: str, score: int, total: int, seconds: int, title: str,
                    exam_id: str = "", kind: str = "") -> None:
        self.data["sessions"].append({
            "category": category, "score": score, "total": total, "seconds": seconds,
            "title": title, "date": now_str(), "exam_id": exam_id, "kind": kind,
        })
        self.data["sessions"] = self.data["sessions"][-800:]
        self.touch("minutes", max(1, round(seconds / 60)))
        self.save()

    def sessions(self, limit: int = 0) -> list[dict]:
        items = list(reversed(self.data["sessions"]))
        return items[:limit] if limit else items

    # ---------------- 作文 / 翻译 / 积累本 ----------------
    def composition(self, kind: str, item_id: str) -> dict:
        bucket = self.data["writings"] if kind == "writing" else self.data["translations"]
        return bucket.get(item_id, {})

    def save_composition(self, kind: str, item_id: str, text: str) -> None:
        bucket = self.data["writings"] if kind == "writing" else self.data["translations"]
        bucket[item_id] = {"text": text, "updated": now_str(), "words": len(text.split())}
        self.touch("minutes", 5)
        self.save()

    def accumulation(self) -> list[dict]:
        return self.data["accumulation"]

    def add_accumulation(self, item: dict) -> str:
        item = dict(item)
        item.setdefault("id", f"note-{datetime.now():%Y%m%d%H%M%S%f}")
        item.setdefault("created", today_str())
        item.setdefault("category", "我的笔记")
        item.setdefault("starred", False)
        item.setdefault("source", "手动添加")
        self.data["accumulation"].append(item)
        self.save()
        return item["id"]

    def update_accumulation(self, item_id: str, **fields) -> None:
        for item in self.data["accumulation"]:
            if item.get("id") == item_id:
                item.update(fields)
                break
        self.save()

    def remove_accumulation(self, item_id: str) -> None:
        self.data["accumulation"] = [x for x in self.data["accumulation"] if x.get("id") != item_id]
        self.save()

    # ---------------- 统计 ----------------
    def stats(self) -> dict:
        words = self.data["words"]
        mastered = sum(1 for state in words.values() if state.get("status") == "已掌握")
        learning = sum(1 for state in words.values() if state.get("status") in ("学习中", "待复习"))
        due = sum(1 for state in words.values()
                  if state.get("seen") and state.get("next_review", "") <= today_str()
                  and state.get("status") != "已掌握")
        wrong_words = sum(1 for state in words.values() if state.get("needs_review"))
        sessions = self.data["sessions"]
        scored = [s for s in sessions if s.get("total")]
        average = round(sum(s["score"] / s["total"] for s in scored) / len(scored) * 100) if scored else 0
        return {
            "mastered": mastered,
            "learning": learning,
            "due": due,
            "wrong_words": wrong_words,
            "wrong": len(self.data["wrong_questions"]),
            "sessions": len(sessions),
            "average": average,
            "streak": self.streak(),
            "minutes_today": self.minutes_today(),
            "total_minutes": self.total_minutes(),
            "words_today": self.activity_today().get("words", 0),
        }

    # ---------------- 备份 / 重置 ----------------
    def export_backup(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")

    def import_backup(self, path: str | Path) -> None:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if "words" not in payload and "word_status" not in payload:
            raise ValueError("这不是 CET6Coach 的学习记录备份文件。")
        self.data = self._load_from_payload(payload)

    def _load_from_payload(self, payload: dict) -> dict:
        data = self._defaults()
        for key, value in payload.items():
            if key in ("version", "schema"):
                continue
            if key == "settings" and isinstance(value, dict):
                data["settings"].update(value)
            else:
                data[key] = value
        if "word_status" in payload:
            data["words"] = payload["word_status"]
        if "starred_words" in payload:
            data["starred"] = payload["starred_words"]
        data["schema"] = SCHEMA
        data["words"] = {w: _normalize_word(s) for w, s in (data.get("words") or {}).items()}
        return data

    def reset(self, keep_imported: bool = True) -> None:
        imported_words = self.data.get("imported_words", []) if keep_imported else []
        imported_exams = self.data.get("imported_exams", []) if keep_imported else []
        settings = dict(self.data.get("settings", {}))
        self.data = self._defaults()
        self.data["settings"].update(settings)
        self.data["imported_words"] = imported_words
        self.data["imported_exams"] = imported_exams
        self.save()
