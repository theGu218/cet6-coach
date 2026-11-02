"""用外部公开答案页交叉核对内置真题答案（english-exam.lazynote.cn）。

关键点：外部页面的选项顺序与我们的原文可能不同，所以不能直接比字母——
先把外部页面的题号→选项文本解析出来，再按“正确答案对应的选项文本”反查我们的选项。

用法：
    python tools/verify_answers.py            # 只核对，输出报告与 content/raw/probe/answers_<exam>.json
    python tools/verify_answers.py --apply    # 写入 content/raw/exam_fixes.json（build_exams.py 会应用）
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
READING = ROOT / "content" / "reading.json"
PROBE = ROOT / "content" / "raw" / "probe"
FIXES = ROOT / "content" / "raw" / "exam_fixes.json"
BASE = "https://english-exam.lazynote.cn/cet6/sections/{exam}/{section}/"

SECTIONS = ("part3-section-c-1", "part3-section-c-2")


def fetch(url: str, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size < 5000:
        result = subprocess.run(
            ["curl.exe", "-sS", "-m", "60", "-L", "-o", str(target), "-w", "%{http_code}", url],
            capture_output=True, text=True)
        code = (result.stdout or "").strip()
        if code != "200":
            raise RuntimeError(f"抓取失败 {url}：{code}")
        time.sleep(0.4)
    return target.read_text(encoding="utf-8", errors="ignore")


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(text: str) -> str:
    text = html_lib.unescape(text).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_page(html: str) -> dict[int, dict]:
    """返回 {题号: {"options": {A: text}, "answer": "A", "answer_text": "..."}}"""
    questions: dict[int, dict] = {}
    for block in re.finditer(r'<div id="qp-(\d{2})"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S):
        num = int(block.group(1))
        body = block.group(2)
        options = {letter: strip_tags(text) for letter, text in
                   re.findall(r'data-pdh-letter="([A-D])"[^>]*>(.*?)</span>', body, re.S)}
        if options:
            questions[num] = {"options": options}
    # FAQ 里的“正确答案 A）”与题号
    for match in re.finditer(r"第\s*(\d{2})\s*题", html):
        num = int(match.group(1))
        window = html[match.end(): match.end() + 900]
        found = re.search(r"正确答案\s*([A-D])", window)
        if not found or num not in questions:
            continue
        letter = found.group(1)
        questions[num]["answer"] = letter
        questions[num]["answer_text"] = questions[num]["options"].get(letter, "")
    return questions


def map_answer(external: dict, our_options: list[str]) -> str:
    """把外部答案按“选项文本”映射成我们的字母。"""
    answer_text = external.get("answer_text") or ""
    target = normalize(answer_text)
    if not target:
        return ""
    for index, option in enumerate(our_options):
        if normalize(option) == target:
            return "ABCD"[index]
    for index, option in enumerate(our_options):
        candidate = normalize(option)
        if candidate and (candidate in target or target in candidate) and abs(len(candidate) - len(target)) <= 12:
            return "ABCD"[index]
    return ""


def main() -> None:
    apply = "--apply" in sys.argv
    exams = json.loads(READING.read_text(encoding="utf-8"))
    fixes: dict = {}
    for exam in exams:
        exam_id = exam["id"]
        report = {}
        diffs = []
        for index, section in enumerate(SECTIONS, 1):
            url = BASE.format(exam=exam_id, section=section)
            try:
                html = fetch(url, PROBE / f"{exam_id}-{section}.html")
            except RuntimeError as exc:
                print(f"  ! {exam_id} {section}: {exc}")
                continue
            parsed = parse_page(html)
            passage = exam["careful"][index - 1]
            for question in passage["questions"]:
                external = parsed.get(question["num"], {})
                if not external.get("answer"):
                    continue
                derived = map_answer(external, question["options"])
                report[question["num"]] = {
                    "external_letter": external["answer"],
                    "external_text": external.get("answer_text", ""),
                    "derived_letter": derived,
                    "ours": question["answer"],
                }
                if derived and derived != question["answer"]:
                    diffs.append((index, question["num"], question["answer"], derived))
        (PROBE / f"answers_{exam_id}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{exam_id}: 核对 {len(report)} 题，差异 {len(diffs)}")
        for passage_index, num, ours, derived in diffs:
            print(f"   第{passage_index}篇 {num}: 内置 {ours} → 外部（按文本换算）{derived}")
            fixes.setdefault(exam_id, {}).setdefault(f"careful-{passage_index}", {})[str(num)] = derived

    if apply and fixes:
        FIXES.write_text(json.dumps(fixes, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已写入 {FIXES.relative_to(ROOT)}")
    elif fixes:
        print("加 --apply 写入修正文件，然后重跑 tools/build_exams.py")


if __name__ == "__main__":
    main()
