# CET-6 Coach 交接文档

> 给下一位接手的 AI 会话或开发者：读这一份就能继续，**不需要翻历史对话**。
> 项目最后提交：见 `git log --oneline -1`（版本 2.1.3）；本文档最后更新：2026-11-21。

---

## 1. 一句话现状

Windows 桌面版六级复习软件（Python + Tkinter，零第三方运行时依赖），**已完成重构、打包、发布**：
2163 词间隔复习、18 套真题阅读（全部配逐题解析）、积累本、30 套作文、73 套翻译、复盘统计。
AI 功能（用户自带 API、翻译批改、阅读问答）**只有设计文档，代码未开始**。

## 2. 位置与环境

| 项 | 值 |
| --- | --- |
| 项目目录 | `D:\deepseek_harness\CET6Coach` |
| 仓库 | https://github.com/theGu218/cet6-coach （GPL-2.0） |
| Python | 3.10+（本机 3.14），tkinter 内置 |
| 第三方依赖 | **无**（标准库 + tkinter；`PIL` 只用于测试截图脚本，不进运行时） |
| 测试 | `python -m unittest discover -s tests`（当前 32 个全绿） |
| 打包 | `python -m PyInstaller --noconfirm --clean CET6Coach_portable.spec` |

## 3. 版本与发布

- 当前版本 **2.1.3**（`main.py` 的 `VERSION`、`version_info.txt` 同步）
- 最近提交（新→旧）：阅读选项/列表滚动条 UI 修复（2.1.3）→ `ad2b9f3` 交接文档 → `cd893ae` AI 设计文档 → `fb5b6af` 阅读页布局/计时
- GitHub Releases：v2.1.0 / v2.1.1 / **v2.1.3 已发布**（2026-11-21，附件 `CET6Coach-portable-v2.1.3.zip`，12.7 MB）；v2.1.2 由维护者手动发布
- 分发方式：**只发便携版（onedir）**。单文件版 spec 保留但不分发——它在受限环境会报 `Could not create temporary directory!`

## 4. 已完成的能力

| 模块 | 状态 | 数据量 |
| --- | --- | --- |
| 今日复习 | 完成 | 按优先级：错词 → 到期旧词 → 新词 → 阅读 → 积累本 |
| 核心词汇 | 完成 | 2163 词（高频核心 310 / 基础回顾 857 / 六级拓展 996）；三阶段检测；1/2/4/7/15/30 天间隔 |
| 真题阅读 | 完成 | 18 套（2023 六套 + 2024–2025 十二套），180 道仔细阅读 + 180 空 + 180 句匹配，全部配解析 |
| 积累本 | 完成 | 内置 30 条 + 自建/收藏/搜索/隐藏答案复习 |
| 写作 | 完成 | 30 套真题，**6 套有范文**，其余待补 |
| 翻译 | 完成 | 73 套真题，**6 套有参考译文**，其余待补 |
| 复盘统计 | 完成 | 分题型正确率、错因分布、词汇状态、最近交卷 |
| 界面细节 | 完成 | 阅读选项自绘 22px 圆环（未选灰空心/选中实心/对绿错红）、列表统一垂直滚动条（滚轮 6 行）、窄窗口文字换行自适应 |
| 设置与数据 | 完成 | 目标设置、CSV/JSON 导入、备份恢复重置、schema 迁移 |
| AI 功能 | **仅设计** | 见 `docs/ai-design.md`（P0 细化在 12.1 节） |

## 5. 代码地图

```text
main.py                应用壳：Tk 根窗口、侧栏、8 页路由、菜单、状态栏、启动崩溃兜底
ui.py                  设计令牌（颜色/字体/宽度）+ 通用组件（卡片/标签/滚动容器/倒计时）
views/                 8 个页面，只画界面和事件
  base.py              BaseView：show() → clear() + build()
  home.py              今日复习（任务清单 + 本周柱状图）
  vocabulary.py        词汇（三阶段检测/错词本/生词本/词汇表）
  reading.py           真题阅读（选词/匹配/仔细 + 学习/考试模式 + 错题重练）★最复杂
  accumulation.py      积累本
  writing.py           写作（限时/草稿/范文/收藏表达）
  translation.py       翻译（限时/草稿/参考译文/要点）
  stats.py             复盘统计
  settings.py          设置：目标、导入、备份、重置
services/              业务规则（不 import tkinter，可单测）
  vocabulary_service.py  复习算法/出题/干扰项/掌握判定
  reading_service.py     判分/错题/错误原因/重练/推荐
  stats_service.py       统计口径/弱项建议
  accumulation_service.py 积累本检索与复习
repositories/
  store.py             进度持久化：schema v3、迁移、原子写、数据目录回退
content/               内容数据 + 加载层
  __init__.py          加载 + 解析合并（analyses/*.json 挂到题目上）
  vocabulary.json / reading.json / exams_scraped.json
  writing.json / translation.json / accumulation_seed.json
  analyses/*.json      18 套逐题解析
tools/                 离线内容流水线（不参与运行时）
  build_exams.py       真题 Markdown → reading.json（含答案修正应用）
  scrape_site.py       抓取 2024–2025 真题原文与答案
  verify_answers.py    用外部答案页按「选项文本」核对答案
  build_writing_translation.py  作文/翻译题库
  fix_vocabulary.py    词库去重与释义清洗
  analysis_spec.md     给子代理的解析生成规范
tests/                 32 个测试（存储/词汇/阅读/内容完整性/界面冒烟）
```

## 6. 内容与数据

- **词库**：2163 词；`short_meaning` 已清洗（无 `&`、音标、`||` 习语、序号）
- **答案**：2023 答案文件有污染，已按公开答案页逐题核对修正 **43 处**（仔细 23 / 选词 10 / 匹配 10），修正记录在 `content/raw/exam_fixes.json`，题目里保留 `original_answer`
- **2024–2025**：12 套 360 题独立作答复核全部一致
- **解析**：`content/analyses/<exam>.json`，结构为 `cloze/matching/careful`，含原文定位、干扰项分析、译文、词汇、长难句；加载时合并进题目
- **来源与许可**：见 `THIRD_PARTY.md`（wamich GPL-2.0、lazynote 站点、Drhm1224 答案、xzyj 语料）

## 7. 数据、备份与迁移

- 默认：`%APPDATA%\CET6Coach\progress.json`
- **便携模式**：程序目录下存在 `data\progress.json` 时优先用它（换版本不丢记录）
- `%APPDATA%` 不可写时自动降级：`<程序目录>\data` → `%USERPROFILE%\CET6Coach`
- 旧记录（v1/v2）自动迁移到 schema v3，迁移前备份 `progress_v{N}_backup.json`
- 备份/恢复在「设置与数据」；**AI 历史规划使用 zip**（见设计文档）

## 8. 关键决策与理由（改之前先看这里）

1. **Tkinter 而不是 Web/Qt**：零依赖、打包小、够用；代价是圆角/阴影/动画做不了
2. **JSON 存进度**：体积小、人可读、备份简单；AI 历史将来单独用 SQLite
3. **便携版 onedir 分发**：单文件版要解压到 `%TEMP%`，受限环境必挂（已踩过）
4. **答案修正而非直接改源文件**：`exam_fixes.json` 留痕，数据可追溯
5. **解析生成要求「原文逐字子串」**：程序校验，防 AI 编造
6. **AI 的 key 用户自带**：不内置、不承担费用与泄露风险
7. **AI 历史 200 条会话**：备考周期一般不到 90 天，按条数更实用
8. **备份用 zip + 系统文件对话框导入**：不做拖拽
9. **阅读问答右侧内嵌**，不另开窗口
10. **AI 精简解析 80–150 字**：结论 + 依据 + 干扰项一句，控制成本

## 9. 已知限制与踩过的坑

| 问题 | 现状/处理 |
| --- | --- |
| 2023-12-1 的段落匹配曾「缺 L 段」 | 实为答案错位，已按站点答案更正为 A–K |
| 2025 两套的匹配文章比答案多 1–2 段 | 站点原文更完整，保留，不影响作答 |
| `articulate` 源词表缺字 | 已修（清楚明白地表达） |
| 同一文件里残留旧字段会覆盖新数据 | 已修（旧键仅在新字段缺失时使用；保存时清理） |
| Tk 主线程做网络请求会假死 | AI 功能必须用后台线程 + `after`（设计文档 12.1.6） |
| PyInstaller 单文件版受限环境启动失败 | 只分发 onedir 便携版 |
| 高 DPI 下列表/字体缩放 | 已按 DPI 放大窗口；字体仍固定 pt |
| 词库释义曾混入 `&`/音标 | 已清洗，并有测试防回归 |

## 10. 怎么验证没改坏

```powershell
cd D:\deepseek_harness\CET6Coach
python -m unittest discover -s tests          # 应 32 个全绿
python main.py                                # 源码运行
python -m PyInstaller --noconfirm --clean CET6Coach_portable.spec   # 打包
```

EXE 自检（不弹窗跑 4 秒自动关闭）：

```powershell
$env:CET6COACH_AUTOCLOSE='4'; & .\dist\CET6Coach-portable\CET6Coach.exe; "exit=$LASTEXITCODE"
```

## 11. 下一步建议（按优先级）

1. **补齐 2024–2025 的作文范文与翻译参考译文**（当前 6/30、6/73）——学习价值最大
2. **考试日期倒排计划**（输入考试日 → 每日词量与剩余套数）——考生最实用
3. **AI P0**：按 `docs/ai-design.md` 12.1 的 6 步做（配置/Key/客户端/设置页/线程/SQLite）
4. **CI + ruff**：`.github/workflows/ci.yml` 跑测试与打包
5. **UI 轻改清单**（设计文档 8.5）：字号阶梯、图标、按钮反馈、空状态、环形进度、深色模式
6. 其它：单实例锁、错题导出 CSV、字体缩放设置

## 12. 给新会话的启动提示词

把下面这段直接粘给新会话：

```text
继续维护 CET6Coach（D:\deepseek_harness\CET6Coach，Python+Tkinter 桌面软件）。
先读 docs/HANDOFF.md 和 docs/ai-design.md，再 git log --oneline -5 看最近改动。
当前版本 2.1.2，32 个测试全绿，GitHub 仓库 theGu218/cet6-coach。

本次要做的：<在这里写具体任务>

约束：
- 不引入第三方运行时依赖；界面用 tkinter；业务在 services/，持久化在 repositories/，views 只画界面
- 不重新生成已核对过的真题解析；新增解析必须用「原文逐字子串」校验
- 分阶段做，每完成一块跑测试并给我看结果；改动前先说明方案
```

## 13. 不要做的事

- 不要把 API Key 写进 `progress.json` 或任何提交文件
- 不要提交 `dist/`、`build/`、`content/raw/`、`design/screens/`（已在 `.gitignore`）
- 不要用单文件版 spec 发布
- 不要盲目重新生成 18 套解析（会引入不可控错误，且费钱）
- 不要给题目文件编造答案；答案变更必须走 `exam_fixes.json` 并留 `original_answer`
- 不要把「真题原文」标成官方标准答案；对外统一口径：解析由本项目整理，仅供参考

## 14. 推送（GitHub）

本机可用 SSH（`~/.ssh/config` 里 github.com → ssh.github.com:443）。必要时显式指定：

```powershell
$env:GIT_SSH_COMMAND='ssh -o BatchMode=yes -o UserKnownHostsFile="C:/Users/顾c/.ssh/known_hosts" -o StrictHostKeyChecking=accept-new -o IdentityFile="C:/Users/顾c/.ssh/id_ed25519"'
git push origin main
```

提交身份已配置为 `theGu218 <a1615163115@163.com>`。
