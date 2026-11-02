# 第三方内容来源与许可

本仓库包含两类东西：**代码**（GPL-2.0，见 LICENSE）和**学习内容数据**（真题原文、答案、词表、解析、译文、范文）。
内容数据的来源、许可与免责说明如下，请在使用或再分发前阅读。

## 1. 真题原文

| 内容 | 来源 | 许可 | 说明 |
| --- | --- | --- | --- |
| 2023 年 6 月 / 12 月共 6 套（阅读部分） | [wamich/english-exem-md](https://github.com/wamich/english-exem-md) | GPL-2.0 | 由该仓库的 Markdown 真题解析、清洗后写入 `content/reading.json` |
| 2024–2025 年共 12 套（阅读部分） | [english-exam.lazynote.cn](https://english-exam.lazynote.cn/cet6/) | 站点未声明许可 | 由 `tools/scrape_site.py` 抓取原卷排版页面中的英文原文与答案 |

## 2. 答案

| 内容 | 来源 | 说明 |
| --- | --- | --- |
| 2023 年答案初稿 | [Drhm1224/cet6-all-in-one](https://github.com/Drhm1224/cet6-all-in-one)（`Answers.md`） | 该文件存在复制粘贴污染；本仓库已按公开答案页逐题核对，修正 43 处 |
| 2024–2025 年答案 | english-exam.lazynote.cn | 逐套独立作答复核，12 套 360 题全部一致 |

## 3. 作文题与翻译题

| 内容 | 来源 | 许可 |
| --- | --- | --- |
| 2022–2025 年作文 Directions（30 套） | [xzyj50609/cet6-translation-writing-corpus](https://github.com/xzyj50609/cet6-translation-writing-corpus) | 见该仓库 LICENSE |
| 2015–2025 年翻译原文（73 篇） | 同上 | 同上 |
| 2023 年作文 / 翻译原文 | wamich/english-exem-md | GPL-2.0 |

## 4. 词表

`content/vocabulary.json` 由大学英语四/六级大纲词表整理而来（约 2163 词，含音标、词性、释义、分层与部分例句），
原始整理过程见早期提交记录。词表本身属于公开的考试大纲词汇，如有权利人异议请联系删除。

## 5. 本项目生成的内容

以下内容由本项目整理撰写，随本仓库按 GPL-2.0 发布：

- `content/analyses/*.json`：逐题解析（原文定位、正确项依据、干扰项分析、重点词汇、长难句拆解）
- `content/writing.json` / `content/translation.json` 中的范文与参考译文（2023 年 6 套）
- `content/accumulation_seed.json`：积累本内置表达

**这些解析与译文是学习辅助材料，不是官方标准答案。**

## 6. 免责声明

- 全国大学英语四、六级考试（CET）真题的著作权归考试主办方所有。本仓库收录真题仅用于**个人学习与研究**，
  不得用于商业用途。
- 若权利人认为本仓库内容侵犯其权益，请提交 Issue，我们会在核实后删除相关内容。
- 本项目与全国大学英语四、六级考试委员会、任何培训机构均无关联。
