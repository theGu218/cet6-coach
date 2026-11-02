"""把 Markdown 版六级真题解析成结构化 JSON。

输入：
  content/raw/english-exem-md/CET6/<年.月>/cet6-YYYY-MM-N.md   原文（wamich/english-exem-md, GPL-2.0）
  content/answers_source.md                                   官方答案（Drhm1224/cet6-all-in-one, Answers.md）

输出：
  content/reading.json  阅读三题型（选词填空 / 段落匹配 / 仔细阅读）结构化数据

解析结果只包含真题原文与答案；逐题解析、译文由后续流程补充。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "raw" / "english-exem-md" / "CET6"
ANSWERS = ROOT / "content" / "answers_source.md"
FIXES = ROOT / "content" / "raw" / "exam_fixes.json"
OUT = ROOT / "content" / "reading.json"

BOLD = re.compile(r"^\*\*(.+?)\*\*$")


def norm(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"<u>&emsp;(\d+)&emsp;</u>", r"{\1}", text)
    text = re.sub(r"&emsp;", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_part(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        raise ValueError(f"找不到 {heading}")
    rest = text[start:]
    nxt = rest.find("\n## ", 1)
    return rest if nxt < 0 else rest[:nxt]


def split_section(part: str, letter: str) -> str:
    marker = re.search(rf"^###\s*Section\s*\**{letter}\**\s*$", part, re.M)
    if not marker:
        raise ValueError(f"找不到 Section {letter}")
    rest = part[marker.end():]
    nxt = re.search(r"\n(?:##\s|###\s*Section)", rest)
    return rest[: nxt.start()] if nxt else rest


def drop_directions(block: str) -> str:
    lines = [line for line in block.split("\n")]
    out = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Directions"):
            skipping = not stripped.endswith("_")
            if stripped.endswith("_"):
                skipping = False
            continue
        if skipping:
            if stripped.endswith("_"):
                skipping = False
            continue
        if stripped.startswith("**Questions ") or stripped.startswith("**Directions"):
            continue
        out.append(line)
    return "\n".join(out).strip()


def parse_cloze(section: str) -> dict:
    body = drop_directions(section)
    table_at = body.find("\n|")
    if table_at < 0:
        raise ValueError("选词填空找不到词库表格")
    passage = norm(body[:table_at])
    table = body[table_at:]
    bank: list[dict] = []
    for line in table.split("\n"):
        if not line.strip().startswith("|"):
            continue
        for cell in line.split("|"):
            cell = cell.strip()
            match = re.match(r"^([A-O])\)\s*(.+)$", cell)
            if match:
                bank.append({"letter": match.group(1), "word": match.group(2).strip()})
    numbers = sorted(int(n) for n in re.findall(r"\{(\d+)\}", passage))
    bank.sort(key=lambda entry: entry["letter"])
    return {"passage": passage, "wordbank": bank, "blank_numbers": numbers}


def parse_matching(section: str) -> dict:
    body = drop_directions(section)
    lines = body.split("\n")
    title = ""
    paragraphs: list[dict] = []
    statements: list[dict] = []
    current = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        bold = BOLD.match(stripped)
        if bold and not paragraphs and not statements:
            title = bold.group(1).strip()
            continue
        para = re.match(r"^([A-O])\)\s*(.*)$", stripped)
        if para:
            current = {"label": para.group(1), "text": para.group(2).strip()}
            paragraphs.append(current)
            continue
        state = re.match(r"^(\d{2})\.\s+(.*)$", stripped)
        if state and 36 <= int(state.group(1)) <= 45:
            statements.append({"num": int(state.group(1)), "statement": state.group(2).strip()})
            current = None
            continue
        if current is not None:
            current["text"] = (current["text"] + " " + stripped).strip()
        elif statements:
            statements[-1]["statement"] = (statements[-1]["statement"] + " " + stripped).strip()
    return {"title": title, "paragraphs": paragraphs, "statements": statements}


def parse_careful(section: str) -> list[dict]:
    body = drop_directions(section)
    chunks = re.split(r"\n####\s*Passage (One|Two)\s*\n", "\n" + body)
    passages: list[dict] = []
    for i in range(1, len(chunks), 2):
        name = chunks[i]
        content = chunks[i + 1]
        lines = content.split("\n")
        paragraphs: list[str] = []
        questions: list[dict] = []
        current_q = None
        current_para: list[str] = []

        def flush_para() -> None:
            nonlocal current_para
            text = norm(" ".join(current_para))
            if text:
                paragraphs.append(text)
            current_para = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_q is None:
                    flush_para()
                continue
            q = re.match(r"^(\d{2})\.\s+(.*)$", stripped)
            if q and 46 <= int(q.group(1)) <= 60:
                flush_para()
                current_q = {"num": int(q.group(1)), "stem": q.group(2).strip(), "options": []}
                questions.append(current_q)
                continue
            opt = re.match(r"^([A-D])\)\s*(.*)$", stripped)
            if opt and current_q is not None:
                current_q["options"].append(opt.group(2).strip())
                continue
            if current_q is not None:
                if current_q["options"]:
                    current_q["options"][-1] = (current_q["options"][-1] + " " + stripped).strip()
                else:
                    current_q["stem"] = (current_q["stem"] + " " + stripped).strip()
                continue
            current_para.append(stripped)
        flush_para()
        passages.append({"title": f"Passage {name}", "passage_name": name,
                         "paragraphs": paragraphs, "questions": questions})
    return passages


def parse_answers() -> dict:
    text = ANSWERS.read_text(encoding="utf-8")
    blocks = re.split(r"\n## ", text)
    result: dict[str, dict] = {}
    for block in blocks:
        head = block.split("\n", 1)[0].strip()
        match = re.match(r"^(\d{4})-(\d{2})（第(一|二|三)套）", head)
        if not match:
            continue
        year, month, cn = match.groups()
        set_no = {"一": 1, "二": 2, "三": 3}[cn]
        key = f"{year}-{int(month):02d}-{set_no}"
        data = {"cloze": {}, "matching": {}, "careful": {"Passage One": {}, "Passage Two": {}}}
        for line in block.split("\n"):
            item = re.match(r"^(\d{2})\.\s*([A-O])(?:\)\s*(.+))?$", line.strip())
            if not item:
                item = re.match(r"^(\d{2})\.\s*([A-O])$", line.strip())
                if not item:
                    continue
            num = int(item.group(1))
            letter = item.group(2)
            word = (item.group(3) or "").strip()
            if 26 <= num <= 35:
                data["cloze"][num] = {"letter": letter, "word": word}
            elif 36 <= num <= 45:
                data["matching"][num] = letter
            else:
                data["careful"]["Passage One" if num <= 50 else "Passage Two"][num] = letter
        result[key] = data
    return result


def build() -> None:
    answers = parse_answers()
    fixes = json.loads(FIXES.read_text(encoding="utf-8")) if FIXES.exists() else {}
    exams: list[dict] = []
    problems: list[str] = []
    for path in sorted(RAW.glob("*/cet6-*.md")):
        match = re.search(r"cet6-(\d{4})-(\d{2})-(\d)\.md$", path.name)
        if not match:
            continue
        year, month, set_no = int(match.group(1)), int(match.group(2)), int(match.group(3))
        key = f"{year}-{month:02d}-{set_no}"
        text = norm(path.read_text(encoding="utf-8"))
        try:
            part = split_part(text, "## Part III")
            cloze = parse_cloze(split_section(part, "A"))
            matching = parse_matching(split_section(part, "B"))
            careful = parse_careful(split_section(part, "C"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{key}: 解析失败 {exc}")
            continue

        answer = answers.get(key, {})
        corrected = 0
        if len(cloze["wordbank"]) != 15:
            problems.append(f"{key}: 词库 {len(cloze['wordbank'])} 个（应为 15）")
        if sorted(cloze["blank_numbers"]) != list(range(26, 36)):
            problems.append(f"{key}: 空格编号异常 {cloze['blank_numbers']}")
        if len(matching["paragraphs"]) < 10:
            problems.append(f"{key}: 段落匹配仅 {len(matching['paragraphs'])} 段")
        if len(matching["statements"]) != 10:
            problems.append(f"{key}: 匹配语句 {len(matching['statements'])} 条（应为 10）")
        for passage in careful:
            if len(passage["questions"]) != 5:
                problems.append(f"{key} {passage['title']}: 题目 {len(passage['questions'])} 道（应为 5）")
            for q in passage["questions"]:
                if len(q["options"]) != 4:
                    problems.append(f"{key} Q{q['num']}: 选项 {len(q['options'])} 个（应为 4）")

        bank_letters = {item["letter"]: item["word"] for item in cloze["wordbank"]}
        cloze_blanks = []
        for num in range(26, 36):
            info = answer.get("cloze", {}).get(num, {})
            original = info.get("letter", "")
            fixed = fixes.get(key, {}).get("cloze", {}).get(str(num))
            letter = fixed or original
            if letter and letter not in bank_letters:
                problems.append(f"{key} 第 {num} 空答案 {letter} 不在词库中")
            entry = {
                "num": num,
                "answer": letter,
                "word": bank_letters.get(letter, info.get("word", "")),
                "answer_source": "已核对修正" if fixed else "答案文件",
            }
            if fixed and fixed != original:
                entry["original_answer"] = original
                corrected += 1
            cloze_blanks.append(entry)
        statements = []
        for statement in matching["statements"]:
            original = answer.get("matching", {}).get(statement["num"], "")
            fixed = fixes.get(key, {}).get("matching", {}).get(str(statement["num"]))
            entry = {
                "num": statement["num"], "statement": statement["statement"],
                "answer": fixed or original,
                "answer_source": "已核对修正" if fixed else "答案文件",
            }
            if fixed and fixed != original:
                entry["original_answer"] = original
                corrected += 1
            statements.append(entry)
        paragraph_labels = {paragraph["label"] for paragraph in matching["paragraphs"]}
        broken = sorted({item["answer"] for item in statements if item["answer"] not in paragraph_labels})
        matching_complete = not broken
        matching_issue = ""
        if broken:
            matching_issue = (f"原文缺少第 {'、'.join(broken)} 段（来源文本不完整），"
                              f"本套段落匹配暂不提供练习")
            problems.append(f"{key}: 段落匹配缺少段落 {broken}，标记为不完整")
        for passage_index, passage in enumerate(careful, 1):
            for q in passage["questions"]:
                fixed = fixes.get(key, {}).get(f"careful-{passage_index}", {}).get(str(q["num"]))
                original = (answer.get("careful", {})
                            .get(f"Passage {passage['passage_name']}", {})
                            .get(q["num"], ""))
                q["answer"] = fixed or original
                q["answer_source"] = "已核对修正" if fixed else "答案文件"
                if fixed and fixed != original:
                    q["original_answer"] = original
                    corrected += 1

        exams.append({
            "id": key,
            "year": year,
            "month": month,
            "set": set_no,
            "label": f"{year}年{month}月 · 第{set_no}套",
            "title": f"{year}年{month}月六级真题（第{set_no}套）",
            "source": "wamich/english-exem-md；答案解析来自 Drhm1224/cet6-all-in-one，"
                      "并已按外部公开答案逐题复核",
            "answer_note": (f"本套 {corrected} 道题的答案文件有误，已按外部公开答案核对修正"
                            if corrected else "答案已复核"),
            "cloze": {"id": f"{key}-cloze", "title": f"{year}年{month}月 选词填空",
                      "passage": cloze["passage"], "wordbank": cloze["wordbank"], "blanks": cloze_blanks},
            "matching": {"id": f"{key}-matching", "title": matching["title"] or f"{year}年{month}月 段落匹配",
                         "paragraphs": matching["paragraphs"], "statements": statements,
                         "complete": matching_complete, "issue": matching_issue},
            "careful": [{"id": f"{key}-careful-{i + 1}", "title": passage["title"],
                         "paragraphs": passage["paragraphs"], "questions": passage["questions"]}
                        for i, passage in enumerate(careful)],
        })

    OUT.write_text(json.dumps(exams, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写入 {OUT.relative_to(ROOT)}：{len(exams)} 套真题")
    total_q = sum(len(p["questions"]) for e in exams for p in e["careful"])
    total_blank = sum(len(e["cloze"]["blanks"]) for e in exams)
    total_match = sum(len(e["matching"]["statements"]) for e in exams)
    print(f"  仔细阅读 {total_q} 题 · 选词填空 {total_blank} 空 · 段落匹配 {total_match} 句")
    if problems:
        print("问题：")
        for problem in problems:
            print("  -", problem)


if __name__ == "__main__":
    build()
