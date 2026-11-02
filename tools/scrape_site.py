"""从公开真题页面抓取 2024–2025 年六级真题阅读（原文 + 答案），生成结构化 JSON。

来源：english-exam.lazynote.cn（按原卷排版，页内含中文对照与解析；本脚本只取英文原文与答案）。

用法（需要能访问外网，沙箱下要放宽权限）：
    python tools/scrape_site.py 2024-06-1 2024-12-2 ...
    python tools/scrape_site.py --range 2024-06 2024-12 2025-06 2025-12
"""
from __future__ import annotations

import html as html_lib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "content" / "raw" / "scrape"
OUT = ROOT / "content" / "exams_scraped.json"
BASE = "https://english-exam.lazynote.cn/cet6/sections/{exam}/{section}/"
SECTIONS = {"cloze": "part3-section-a", "matching": "part3-section-b",
            "careful-1": "part3-section-c-1", "careful-2": "part3-section-c-2"}
FALLBACKS = {"careful-1": ("part3-section-c-1", "part3-section-c")}
CJK = re.compile(r"[\u4e00-\u9fff]")

# 源页已知残缺：按原卷/页面解析说明补全（勿随意添加，只在有据可依时登记）
REPAIRS = {
    ("2024-06-1", 47, "B"): (
        "The more people who witness an event, the less likely anyone will venture to help.",
        "源页该选项后半句缺失，已按页面解析中给出的原意补全（venture to help）"),
}


def fetch(exam: str, key: str) -> str:
    path = CACHE / f"{exam}-{key}.html"
    cached = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    if "exam-paper-surface" not in cached:
        path.parent.mkdir(parents=True, exist_ok=True)
        last = ""
        for section in FALLBACKS.get(key, (SECTIONS[key],)):
            result = subprocess.run(
                ["curl.exe", "-sS", "-m", "60", "-L", "-o", str(path), "-w", "%{http_code}",
                 BASE.format(exam=exam, section=section)], capture_output=True, text=True)
            last = (result.stdout or "").strip()
            if last == "200" and "exam-paper-surface" in path.read_text(encoding="utf-8", errors="ignore"):
                break
            time.sleep(0.3)
        else:
            raise RuntimeError(f"{exam} {key} 抓取失败：{last}")
    return path.read_text(encoding="utf-8", errors="ignore")


def lines_of(raw: str) -> list[str]:
    body = raw[raw.find("exam-paper-surface"):]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = html_lib.unescape(body)
    return [line.strip() for line in body.split("\n") if line.strip()]


def is_english(text: str) -> bool:
    return bool(text) and not CJK.search(text)


def mostly_english(text: str) -> bool:
    """英文正文里可能夹着 (看管者) 这类中文词注，不能因为出现中文就整行丢弃。"""
    if not text:
        return False
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese / max(1, len(text)) < 0.2


def after_directions(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.startswith("Part III"):
            continue
    for index, line in enumerate(lines):
        if "Answer Sheet" in line:
            return index + 1
    return 0


def parse_cloze(raw: str) -> dict:
    lines = lines_of(raw)
    start = after_directions(lines)
    bank_at = None
    for index in range(start, len(lines) - 1):
        if re.fullmatch(r"[A-O]\)?", lines[index]) and is_english(lines[index + 1]):
            bank_at = index
            break
    if bank_at is None:
        raise ValueError("找不到选项词库")
    passage_parts: list[str] = []
    for line in lines[start:bank_at]:
        if re.fullmatch(r"2[6-9]|3[0-5]", line):
            passage_parts.append("{" + line + "}")
        elif not mostly_english(line) or "Directions" in line:
            continue
        elif any(marker in line for marker in ("Answer Sheet", "single line through", "more than once",
                                              "each item on", "真题卷", "Part III", "bank following")):
            continue
        else:
            passage_parts.append(line)
    bank = []
    index = bank_at
    while index < len(lines) - 1:
        letter_match = re.fullmatch(r"([A-O])\)?", lines[index])
        if not letter_match:
            break
        word = lines[index + 1].strip()
        if not is_english(word):
            break
        bank.append({"letter": letter_match.group(1), "word": word})
        index += 2
    answers = {}
    for index in range(bank_at, len(lines) - 1):
        if lines[index].startswith("【答案】"):
            candidate = lines[index + 1]
            match = re.match(r"([A-O])\)\s*(.+)", candidate)
            if match:
                answers[len(answers) + 26] = {"letter": match.group(1), "word": match.group(2).strip()}
    passage = " ".join(passage_parts)
    passage = re.sub(r"\s+", " ", passage).strip()
    blanks = []
    for num in range(26, 36):
        info = answers.get(num, {})
        blanks.append({"num": num, "answer": info.get("letter", ""),
                       "word": info.get("word", "")})
    return {"passage": passage, "wordbank": bank, "blanks": blanks}


def parse_matching(raw: str) -> dict:
    lines = lines_of(raw)
    start = after_directions(lines) + 1
    title = ""
    for index in range(start, min(start + 6, len(lines))):
        if is_english(lines[index]) and not re.match(r"^[A-O]\)", lines[index]):
            title = lines[index]
            start = index + 1
            break
    paragraphs: list[dict] = []
    statements: list[dict] = []
    index = start
    current: dict | None = None
    while index < len(lines):
        line = lines[index]
        paragraph = re.fullmatch(r"([A-Z])\)", line)
        if paragraph:
            current = {"label": paragraph.group(1), "text": ""}
            paragraphs.append(current)
            index += 1
            continue
        statement = re.match(r"^(\d{2})\.$", line)
        if statement and 36 <= int(statement.group(1)) <= 45:
            current = None
            if index + 1 < len(lines):
                statements.append({"num": int(statement.group(1)),
                                   "statement": lines[index + 1], "answer": ""})
            index += 2
            continue
        if line.startswith("【答案】") and statements:
            if index + 1 < len(lines):
                candidate = lines[index + 1].strip()
                if re.fullmatch(r"[A-Z]", candidate):
                    statements[-1]["answer"] = candidate
            index += 2
            continue
        if current is not None and mostly_english(line) and line not in ("【答案】",):
            if current["text"]:
                current["text"] += " " + line
            else:
                current["text"] = line
        index += 1
    return {"title": title, "paragraphs": paragraphs, "statements": statements}


def parse_careful(raw: str) -> dict:
    lines = lines_of(raw)
    start = after_directions(lines)
    paragraphs: list[str] = []
    questions: list[dict] = []
    in_questions = False
    index = start
    while index < len(lines):
        line = lines[index]
        if line in ("题目与逐题解析", "Questions & Analysis") or line.startswith("题目与"):
            in_questions = True
            index += 1
            continue
        if not in_questions:
            if re.fullmatch(r"P\d+", line):
                texts = []
                cursor = index + 1
                while cursor < len(lines) and mostly_english(lines[cursor]):
                    texts.append(lines[cursor])
                    cursor += 1
                if texts:
                    paragraphs.append(" ".join(texts))
                index = cursor
                continue
            index += 1
            continue
        question = re.fullmatch(r"(\d{2})\.", line)
        if question and 46 <= int(question.group(1)) <= 60:
            num = int(question.group(1))
            stem = lines[index + 1] if index + 1 < len(lines) else ""
            options = []
            cursor = index + 2
            while cursor + 1 < len(lines) and len(options) < 4:
                if re.fullmatch(r"[A-D]\)", lines[cursor]) and mostly_english(lines[cursor + 1]):
                    options.append(lines[cursor + 1])
                    cursor += 2
                else:
                    break
            answer = ""
            probe = cursor
            while probe < len(lines) - 1 and probe < cursor + 12:
                if lines[probe].startswith("【答案】") and re.fullmatch(r"[A-D]", lines[probe + 1]):
                    answer = lines[probe + 1]
                    break
                probe += 1
            questions.append({"num": num, "stem": stem, "options": options, "answer": answer})
            index = cursor
            continue
        index += 1
    return {"paragraphs": paragraphs, "questions": questions}


def build(exam: str) -> dict:
    year, month, set_no = exam.split("-")
    year, month, set_no = int(year), int(month), int(set_no)
    cloze = parse_cloze(fetch(exam, "cloze"))
    matching = parse_matching(fetch(exam, "matching"))
    careful = []
    for i in (1, 2):
        parsed = parse_careful(fetch(exam, f"careful-{i}"))
        careful.append({"id": f"{exam}-careful-{i}", "title": f"Passage {'One' if i == 1 else 'Two'}",
                        "paragraphs": parsed["paragraphs"], "questions": parsed["questions"]})
    return {
        "id": exam, "year": year, "month": month, "set": set_no,
        "label": f"{year}年{month}月 · 第{set_no}套",
        "title": f"{year}年{month}月六级真题（第{set_no}套）",
        "source": "english-exam.lazynote.cn（原卷排版）",
        "cloze": {"id": f"{exam}-cloze", "title": f"{year}年{month}月 选词填空",
                  "passage": cloze["passage"], "wordbank": cloze["wordbank"], "blanks": cloze["blanks"]},
        "matching": {"id": f"{exam}-matching", "title": matching["title"] or f"{year}年{month}月 段落匹配",
                     "paragraphs": matching["paragraphs"], "statements": matching["statements"],
                     "complete": True, "issue": ""},
        "careful": careful,
    }


def validate(exam: dict) -> list[str]:
    problems = []
    cloze = exam["cloze"]
    if len(cloze["wordbank"]) != 15:
        problems.append(f"词库 {len(cloze['wordbank'])} 个")
    if sorted(int(n) for n in re.findall(r"\{(\d+)\}", cloze["passage"])) != list(range(26, 36)):
        problems.append("空格标记不完整")
    if any(not blank["answer"] for blank in cloze["blanks"]):
        problems.append("选词填空缺答案")
    matching = exam["matching"]
    labels = {p["label"] for p in matching["paragraphs"]}
    if len(matching["statements"]) != 10:
        problems.append(f"段落匹配语句 {len(matching['statements'])} 条")
    for statement in matching["statements"]:
        if statement["answer"] not in labels:
            problems.append(f"第 {statement['num']} 句答案 {statement['answer']} 不在段落中")
    notes = []
    for passage in exam["careful"]:
        for question in passage["questions"]:
            for index, option in enumerate(question["options"]):
                letter = "ABCD"[index]
                repair = REPAIRS.get((exam["id"], question["num"], letter))
                if repair and option.rstrip().endswith(("to", "of", "the", "a", "and", "but")):
                    question["options"][index] = repair[0]
                    notes.append(f"第 {question['num']} 题 {letter} 选项：{repair[1]}")
    if notes:
        exam["data_notes"] = notes
    for passage in exam["careful"]:
        if len(passage["questions"]) != 5:
            problems.append(f"{passage['title']} 题目 {len(passage['questions'])} 道")
        for question in passage["questions"]:
            if len(question["options"]) != 4:
                problems.append(f"第 {question['num']} 题选项 {len(question['options'])} 个")
            if question["answer"] not in ("A", "B", "C", "D"):
                problems.append(f"第 {question['num']} 题缺答案")
        if len(passage["paragraphs"]) < 3:
            problems.append(f"{passage['title']} 段落 {len(passage['paragraphs'])} 段")
    return problems


def main() -> None:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if "--range" in sys.argv:
        expanded = []
        for prefix in args:
            expanded.extend(f"{prefix}-{set_no}" for set_no in (1, 2, 3))
        args = expanded
    if not args:
        print("用法：python tools/scrape_site.py 2024-06-1 2024-12-2 或 --range 2024-06 2025-06")
        return
    exams = []
    if OUT.exists():
        exams = json.loads(OUT.read_text(encoding="utf-8"))
    known = {exam["id"] for exam in exams}
    for exam_id in args:
        if exam_id in known:
            print(f"{exam_id}: 已存在，跳过")
            continue
        try:
            exam = build(exam_id)
        except Exception as exc:  # noqa: BLE001
            print(f"{exam_id}: 抓取/解析失败 {exc}")
            continue
        problems = validate(exam)
        if problems:
            print(f"{exam_id}: 有问题，暂不写入 → {problems}")
            continue
        exams.append(exam)
        print(f"{exam_id}: OK（选词 {len(exam['cloze']['blanks'])} 空 / 匹配 "
              f"{len(exam['matching']['statements'])} 句 / 仔细 "
              f"{sum(len(p['questions']) for p in exam['careful'])} 题）")
    exams.sort(key=lambda item: (item["year"], item["month"], item["set"]))
    OUT.write_text(json.dumps(exams, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"共 {len(exams)} 套 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
