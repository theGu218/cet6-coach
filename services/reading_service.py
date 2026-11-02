"""真题阅读业务规则（重构设计方案 §6）。

- 学习模式：逐题提交、立即看解析；
- 考试模式：整组计时，交卷后统一评分；
- 错题记错误原因，按题型 / 原因统计正确率，为推荐提供依据；
- 支持错题重练。
"""
from __future__ import annotations

import random
from datetime import datetime

KINDS = ("cloze", "matching", "careful")
KIND_NAMES = {"cloze": "选词填空", "matching": "段落匹配", "careful": "仔细阅读"}
ERROR_REASONS = ("词汇不懂", "句子不懂", "定位错误", "逻辑误判", "粗心")


class ReadingService:
    def __init__(self, exams: list[dict], store):
        self.exams = exams
        self.by_id = {exam["id"]: exam for exam in exams}
        self.store = store

    # ---------------- 取题 ----------------
    def exam(self, exam_id: str) -> dict:
        return self.by_id[exam_id]

    def grouped(self) -> dict[int, list[dict]]:
        groups: dict[int, list[dict]] = {}
        for exam in sorted(self.exams, key=lambda e: (e["year"], e["month"], e["set"]), reverse=True):
            groups.setdefault(exam["year"], []).append(exam)
        return groups

    def status(self, exam_id: str) -> dict:
        record = self.store.data["reading"].get(exam_id, {})
        done = [kind for kind in KINDS if record.get(kind, {}).get("total")]
        return {"done": done, "attempts": record.get("attempts", 0), "last": record.get("last", "")}

    def recommend(self) -> dict | None:
        """优先推荐没做过的最近真题；都做过则推荐正确率最低的。"""
        ordered = sorted(self.exams, key=lambda e: (e["year"], e["month"], e["set"]), reverse=True)
        for exam in ordered:
            record = self.store.data["reading"].get(exam["id"], {})
            if len([k for k in KINDS if record.get(k, {}).get("total")]) < 3:
                return exam
        best = None
        for exam in ordered:
            accuracy = self.exam_accuracy(exam["id"])
            if best is None or accuracy < best[0]:
                best = (accuracy, exam)
        return best[1] if best else None

    def exam_accuracy(self, exam_id: str) -> int:
        record = self.store.data["reading"].get(exam_id, {})
        score = total = 0
        for kind in KINDS:
            item = record.get(kind, {})
            score += item.get("correct", 0)
            total += item.get("total", 0)
        return round(score / total * 100) if total else -1

    # ---------------- 判分 ----------------
    def grade_cloze(self, exam_id: str, answers: dict) -> list[dict]:
        exam = self.exam(exam_id)
        results = []
        for blank in exam["cloze"]["blanks"]:
            key = str(blank["num"])
            chosen = (answers.get(key) or answers.get(blank["num"]) or "").strip().upper()
            correct = chosen == blank["answer"]
            results.append({
                "key": f"{exam_id}-cloze-{key}", "qid": key, "num": blank["num"],
                "kind": "cloze", "prompt": f"第 {blank['num']} 空",
                "answer": blank["answer"], "chosen": chosen or "未作答", "correct": correct,
                "word": blank.get("word", ""),
                "explanation": blank.get("explanation", ""),
                "evidence": blank.get("evidence", ""),
                "distractors": blank.get("distractors", {}),
                "verified": blank.get("verified", None),
            })
        return results

    def grade_matching(self, exam_id: str, answers: dict) -> list[dict]:
        exam = self.exam(exam_id)
        results = []
        for statement in exam["matching"]["statements"]:
            key = str(statement["num"])
            chosen = (answers.get(key) or answers.get(statement["num"]) or "").strip().upper()
            correct = chosen == statement["answer"]
            results.append({
                "key": f"{exam_id}-matching-{key}", "qid": key, "num": statement["num"],
                "kind": "matching", "prompt": statement["statement"],
                "answer": statement["answer"], "chosen": chosen or "未作答", "correct": correct,
                "explanation": statement.get("explanation", ""),
                "evidence": statement.get("evidence", ""),
            })
        return results

    def grade_careful(self, exam_id: str, passage_id: str, answers: dict) -> list[dict]:
        exam = self.exam(exam_id)
        passage = next((p for p in exam["careful"] if p["id"] == passage_id), None)
        if passage is None:
            return []
        results = []
        for question in passage["questions"]:
            key = str(question["num"])
            chosen = (answers.get(key) or answers.get(question["num"]) or "").strip().upper()
            correct = chosen == question["answer"]
            results.append({
                "key": f"{exam_id}-careful-{key}", "qid": key, "num": question["num"],
                "kind": "careful", "passage": passage["title"],
                "prompt": question["stem"], "options": question["options"],
                "answer": question["answer"], "chosen": chosen or "未作答", "correct": correct,
                "explanation": question.get("explanation", ""),
                "evidence": question.get("evidence_quote", ""),
                "evidence_paragraph": question.get("evidence_paragraph", 0),
                "distractors": question.get("distractors", {}),
                "verified": question.get("verified", None),
            })
        return results

    @staticmethod
    def option_letter(index: int) -> str:
        return "ABCD"[index] if 0 <= index < 4 else ""

    # ---------------- 记录 ----------------
    def record(self, exam_id: str, kind: str, results: list[dict], seconds: int,
               mode: str = "learning", sub_id: str = "") -> None:
        exam = self.exam(exam_id)
        score = sum(1 for item in results if item["correct"])
        total = len(results)
        record = self.store.reading_record(exam_id)
        bucket = record.setdefault(kind, {})
        bucket["correct"] = score
        bucket["total"] = total
        bucket["seconds"] = seconds
        bucket["mode"] = mode
        bucket["finished"] = datetime.now().isoformat(timespec="seconds")
        bucket["answers"] = {item["qid"]: item["chosen"] for item in results}
        if kind == "careful" and sub_id:
            record.setdefault("careful_detail", {})[sub_id] = {
                "correct": score, "total": total, "finished": bucket["finished"],
            }
        record["attempts"] = record.get("attempts", 0) + 1
        record["last"] = bucket["finished"]
        for item in results:
            self.store.record_answer(item["key"], item["prompt"], item["answer"], item["chosen"],
                                     item["correct"], KIND_NAMES[kind],
                                     exam_id=exam_id, qid=item.get("qid", ""))
        title = f"{exam['label']} {KIND_NAMES[kind]}" + (f" {sub_id.split('-')[-1]}" if sub_id else "")
        self.store.add_session(KIND_NAMES[kind], score, total, seconds, title,
                               exam_id=exam_id, kind=kind)
        self.store.save()

    def add_error_tag(self, key: str, reason: str) -> None:
        self.store.set_error_tag(key, reason)

    # ---------------- 错题 ----------------
    def wrong_questions(self, kind: str = "") -> list[dict]:
        items = [item for item in self.store.data["wrong_questions"].values()
                 if item.get("category") in (KIND_NAMES.values() if not kind else (KIND_NAMES[kind],))]
        return sorted(items, key=lambda x: x.get("updated", ""), reverse=True)

    def wrong_bank(self) -> list[dict]:
        """按题型分组的错题，附带错误原因标签。"""
        bank = []
        for item in self.store.data["wrong_questions"].values():
            if item.get("category") not in KIND_NAMES.values():
                continue
            bank.append({**item, "reason": self.store.error_tag(item["question_id"]),
                         "exam_id": item.get("exam_id", ""), "qid": item.get("qid", "")})
        return sorted(bank, key=lambda x: x.get("updated", ""), reverse=True)

    # ---------------- 统计 ----------------
    def accuracy_by_kind(self) -> dict:
        bucket: dict[str, list[int]] = {name: [0, 0] for name in KIND_NAMES.values()}
        for session in self.store.data["sessions"]:
            category = session.get("category")
            if category in bucket:
                bucket[category][0] += session.get("score", 0)
                bucket[category][1] += session.get("total", 0)
        return {name: (round(score / total * 100) if total else 0, total)
                for name, (score, total) in bucket.items()}

    def accuracy_by_reason(self) -> dict:
        counts: dict[str, int] = {reason: 0 for reason in ERROR_REASONS}
        for item in self.store.data["wrong_questions"].values():
            reason = self.store.error_tag(item["question_id"])
            if reason in counts:
                counts[reason] += 1
        return counts

    def retry_queue(self, kind: str = "") -> list[dict]:
        """错题重练：把错题还原成可重做的题目。"""
        queue = []
        for item in self.wrong_bank():
            if kind and item["category"] != KIND_NAMES[kind]:
                continue
            exam = self.by_id.get(item.get("exam_id") or "")
            if not exam:
                continue
            qid = str(item.get("qid"))
            if item["category"] == "仔细阅读":
                for passage in exam["careful"]:
                    for question in passage["questions"]:
                        if str(question["num"]) == qid:
                            queue.append({"kind": "careful", "exam_id": exam["id"], "passage_id": passage["id"],
                                          "num": question["num"], "stem": question["stem"],
                                          "options": question["options"], "answer": question["answer"],
                                          "explanation": question.get("explanation", ""),
                                          "evidence": question.get("evidence_quote", ""),
                                          "chosen": item["chosen"], "wrong_count": item.get("wrong_count", 1)})
            elif item["category"] == "选词填空":
                for blank in exam["cloze"]["blanks"]:
                    if str(blank["num"]) == qid:
                        queue.append({"kind": "cloze", "exam_id": exam["id"], "num": blank["num"],
                                      "stem": f"第 {blank['num']} 空", "answer": blank["answer"],
                                      "word": blank.get("word", ""),
                                      "explanation": blank.get("explanation", ""),
                                      "evidence": blank.get("evidence", ""),
                                      "chosen": item["chosen"], "wrong_count": item.get("wrong_count", 1)})
            else:
                for statement in exam["matching"]["statements"]:
                    if str(statement["num"]) == qid:
                        queue.append({"kind": "matching", "exam_id": exam["id"], "num": statement["num"],
                                      "stem": statement["statement"], "answer": statement["answer"],
                                      "explanation": statement.get("explanation", ""),
                                      "evidence": statement.get("evidence", ""),
                                      "chosen": item["chosen"], "wrong_count": item.get("wrong_count", 1)})
        return queue

    def pick_recommend(self) -> dict | None:
        return self.recommend()

    def random_exam(self) -> dict:
        return random.choice(self.exams)
