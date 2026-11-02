# 真题学习解析生成规范（子代理用）

目标：为 **一套**六级真题生成完整学习解析，写成严格合法的 JSON 文件。

## 输入

`content/exams_scraped.json`（2024–2025 套）或 `content/reading.json`（2023 套）里，找到指定 `id` 的对象：

- `cloze`: `{passage（英文，空格用 {26}…{35} 标记）, wordbank（15 个 A)–O)，含 letter/word）, blanks（26..35，含 answer 字母与 word）}`
- `matching`: `{title, paragraphs（A)–R) 段落）, statements（36..45，含 statement 与 answer 段落字母）}`
- `careful`: `[两篇 {id, title, paragraphs[], questions[]（含 num/stem/options[4]/answer 字母）}]`

## 输出

`content/analyses/<id>.json`，UTF-8，纯 JSON（不要 Markdown 代码块），顶层键严格为 `exam` / `cloze` / `matching` / `careful`：

```json
{
 "exam": "<id>",
 "cloze": {"blanks": {"26": {"answer": "N", "my_answer": "N", "verified": true,
     "explanation": "中文：词性+语义+搭配",
     "evidence": "含该空的原文整句（英文逐字，保留 {26}）",
     "distractors": {"B": "中文：具体错误类型", "C": "…"}}, "…26..35…"},
     "passage_zh": "全文参考译文（中文通顺整段）"},
 "matching": {"statements": {"36": {"answer": "C", "my_answer": "C", "verified": true,
     "explanation": "中文：信息来自 C 段的对应关系（同义改写）",
     "evidence": "C 段原句（英文逐字）"}, "…36..45…"},
     "article_zh": "全文参考译文（中文，保留 A) B) 段落标记）"},
 "careful": {"<第一篇 id>": {"passage_zh": "…",
     "questions": {"46": {"answer": "D", "my_answer": "D", "verified": true,
       "evidence_paragraph": 2,
       "evidence_quote": "原文逐字句子",
       "explanation": "中文：正确项为什么对",
       "distractors": {"A": "…", "B": "…", "C": "…"}}, "…"},
     "vocabulary": [{"word": "…", "meaning": "中文释义", "note": "可选搭配"}],
     "long_sentence": {"sentence": "英文长句（逐字）", "analysis": "中文主干+从句拆解"}},
   "<第二篇 id>": {"…同上…"}}
}
```

## 硬性要求

1. **先独立作答**：不要直接相信文件里的 `answer`。独立判断后与 `answer` 比对：
   - 一致 → `verified: true`，`my_answer` 与 `answer` 相同；
   - 不一致 → `verified: false`，`my_answer` 写你的判断，`conflict_reason` 用中文写清依据（引用原文）。`answer` 字段保留文件原值。
2. **全覆盖**：选词填空 26–35、段落匹配 36–45、仔细阅读两篇各 5 题，一题都不能少。
3. **逐字**：`evidence` / `evidence_quote` / `long_sentence.sentence` 必须是原文逐字子串（可截取，字符顺序完全一致）。写完用脚本校验。
4. **干扰项**：写具体错误类型（词性/时态词形/搭配不成立/褒贬方向/主体偷换/张冠李戴/以偏概全/无中生有/范围过窄等），禁止“无关”“不符原文”这类空话。
5. 每篇 `vocabulary` 给 6–8 词，`long_sentence` 每篇 1 句；中文简体，英文原样。
6. 不编造原文没有的内容。

## 自检

```powershell
python -X utf8 -c "import json;d=json.load(open('content/analyses/<id>.json',encoding='utf-8'));print(len(d['cloze']['blanks']),len(d['matching']['statements']),sum(len(p['questions']) for p in d['careful'].values()))"
```

应输出 `10 10 10`。另外建议写一个小脚本断言每条 evidence 都是对应原文的子串。

## 汇报

完成后用 send_message 汇报：文件路径、题量、`verified:false` 的题号清单（含你与文件答案的差异与一句理由）。
