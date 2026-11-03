# CET-6 Coach · AI 功能设计文档

> 状态：设计稿（未实现）
> 目标读者：本项目维护者（后续由维护者或 AI 助手实现）
> 关联需求：接入用户自带的 OpenAI 兼容 API，实现 AI 批改翻译、AI 讲解阅读题，并用 SQLite 保存对话历史，支持导出/导入迁移。

---

## 1. 背景与目标

现在的软件是纯本地工具：词汇、真题、解析都是内置的。接下来要加的是「有判断力的反馈」：

1. **翻译批改**：用户写完译文，AI 给分项得分、逐处错误和修改建议。
2. **阅读讲解**：用户对某道题有疑问时，可以追问「为什么 B 不对」「这句话怎么理解」。
3. **对话历史本地化**：所有请求与回答存本地 SQLite，可回看、可搜索、可导出迁移。

不做什么（明确边界）：

- **不做云端账号体系**：不注册、不登录、不搭服务器，key 由用户自己填。
- **不做「生成类似题」**：阅读 AI 只回答问题，不造题。
- **不替换内置解析**：内置逐题解析是核对过的；AI 是补充讲解，不是替代。
- **不自动上传学习记录**：只发送当次请求所需的原文/译文，不传词库进度、错题记录。

## 2. 已确认的产品决策

| 决策项 | 结论 |
| --- | --- |
| API Key 谁提供 | **用户自带**（软件不内置 key，不承担费用与泄露风险） |
| 接口协议 | **OpenAI 兼容**（`POST {base_url}/chat/completions`） |
| 默认服务商 | **DeepSeek**（`https://api.deepseek.com/v1`，模型 `deepseek-chat`），可切换 Qwen / Kimi / 其它兼容服务 |
| 模型选择 | 由用户填写；若服务支持 `GET {base_url}/models`，则拉取列表供选择 |
| AI 历史 | **存本地 SQLite**，**参与软件备份**，并支持**导出/导入**以便换电脑 |
| 阅读 AI 范围 | 只做问答讲解，不生成新题 |
| 备份格式 | **zip**（progress.json + ai.db + manifest），导入时用系统文件对话框选择文件 |
| 历史保留 | **最近 200 个会话**（备考周期通常不到 90 天，按条数更实用） |
| 阅读问答入口 | **右侧内嵌面板**（不另开窗口） |
| AI 精简解析 | 要，但控制在 **80–150 字**：先结论、再依据、干扰项一句带过，避免长篇烧 token |
| UI 改造 | 分批轻改（配色、图标、反馈、空状态），不立刻换框架 |

---

## 3. 总体架构

### 3.1 模块划分（在现有分层上新增）

```text
services/ai/
  __init__.py
  config.py          # AI 配置读写（base_url / model / key 引用）
  client.py          # OpenAI 兼容客户端：请求、超时、重试、错误归一化
  schemas.py         # 结果结构校验（不需要第三方库，手写校验即可）
  prompts.py         # 提示词模板 + 版本号
  translate_grade.py # 翻译批改
  reading_tutor.py   # 阅读问答
  history.py         # 对话历史的读写（调用 repositories/ai_store.py）

repositories/
  ai_store.py        # SQLite：会话、消息、AI 缓存、schema 迁移
  ai_backup.py       # AI 历史的导出/导入（JSON 文件）

views/
  ai_settings.py     # 设置页里的「AI 服务」卡片（也可并入 views/settings.py）
  ai_chat.py         # 阅读问答抽屉 / 独立页
  (翻译批改面板并入 views/translation.py)
```

原则不变：**views 只画界面，services 不含 tkinter，repositories 只管存取**。

### 3.2 请求流程（以翻译批改为例）

```text
用户点「AI 批改」
   ↓
views/translation.py 收集：题目 id、中文原文、参考译文、用户译文
   ↓
services/ai/translate_grade.py 组装 messages（含 rubric、few-shot、JSON 要求）
   ↓
services/ai/client.py 在【后台线程】发 HTTPS 请求（urllib，超时 60s，重试 1 次）
   ↓
返回 → schemas 校验 → 提取 errors 中引用的片段，校验确实是用户译文/原文的子串
   ↓
repositories/ai_store.py 写入 messages + ai_grading
   ↓
线程结束 → widget.after(0, 回调) 回到 Tk 主线程渲染面板
```

**关键点：Tkinter 主线程绝对不能阻塞在网络上**。所有请求都走 `threading.Thread`，结果通过 `after()` 回主线程。

---

## 4. 配置设计

### 4.1 设置项（存 `progress.json` 的 settings 里，密钥除外）

```json
"ai": {
  "enabled": true,
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "temperature": 0,
  "timeout": 60,
  "max_tokens": 1200,
  "provider_hint": "deepseek"
}
```

- 只存**非敏感**配置；`api_key` 不落在这个文件里。
- `provider_hint` 仅用于显示（下拉预设），不参与逻辑。

### 4.2 API Key 存储

按优先级三选一，实现时取第一条可用的：

1. Windows 凭据管理器（`ctypes` 调用 `CredWriteW` / `CredReadW`，服务名 `CET6Coach/ai-api-key`）
2. 本地加密文件：用 DPAPI（`CryptProtectData`）加密后存 `%APPDATA%\CET6Coach\ai_key.dat`
3. 环境变量 `CET6COACH_API_KEY`（只读，方便高级用户）

界面只显示掩码（`sk-****abcd`），带「替换 / 清除」按钮；`error.log` 与任何日志中**不得出现明文 key**。

### 4.3 连接测试

设置页提供「测试连接」按钮：

```text
请求：POST {base_url}/chat/completions
body：{"model": "<用户填的>", "messages": [{"role":"user","content":"ping"}], "max_tokens": 8}
```

- 200 → 「连接成功，模型可用」
- 401 → 「Key 无效或已过期」
- 404 → 「模型名不存在」
- 其它 → 显示状态码与归一化提示

---

## 5. AI 服务层设计

### 5.1 client.py

```python
class AIError(Exception):
    """所有 AI 相关错误统一成这一类，带 kind 字段。"""
    # kind: no_key / bad_key / rate_limit / model_not_found / timeout /
    #       network / bad_response / server_error

class AIClient:
    def __init__(self, settings, key_provider): ...
    def chat(self, messages, *, temperature=None, max_tokens=None,
             json_mode=True, timeout=None) -> str:
        """返回模型原始文本；失败抛 AIError。"""
    def list_models(self) -> list[str]:
        """GET {base_url}/models，失败返回空列表。"""
```

实现要点：

- 用标准库 `urllib.request`，不引入 `requests`（保持零依赖）
- `json_mode=True` 时先尝试 `response_format={"type":"json_object"}`；若返回 400 说明服务不支持，则**自动去掉该字段重试一次**
- 超时用 `timeout=` 参数；连接错误/5xx 重试 1 次（间隔 1.5s），4xx 不重试
- 响应解析：取 `choices[0].message.content`；兼容少数服务把内容放在 `choices[0].text`
- 记录 `usage`（prompt/completion tokens）到历史表，方便用户看花费

### 5.2 prompts.py

- 每个任务一个模板函数，模板带 **`PROMPT_VERSION`**（如 `translate_grade@1`），写进历史，方便以后对比效果
- 模板里固定：角色、评分维度、输出 JSON 结构、禁止编造、要求引用原文片段
- few-shot 示例放常量里（2 个示例足够，太多浪费 token）

### 5.3 输出结构与校验

**翻译批改**：

```json
{
  "score": 11,
  "full_score": 15,
  "dimensions": [
    {"name": "准确", "score": 4, "full": 5, "comment": "…"},
    {"name": "通顺", "score": 4, "full": 5, "comment": "…"},
    {"name": "完整", "score": 3, "full": 5, "comment": "…"}
  ],
  "errors": [
    {"student": "…", "suggest": "…", "reason": "…", "type": "时态"}
  ],
  "rewrite": "改进后的完整译文",
  "summary": "一句话总评"
}
```

**阅读问答**：自由文本（Markdown），但要求：

- 引用原文时用 `「…」` 包起来
- 程序提取引号内片段，校验是否为该篇段落/选项的子串；不是就标记「未能在原文中找到对应句」，避免误导

校验失败的处理：先重试一次（提示模型「上次输出不合法」），仍失败则展示原始文本 + 「解析失败，请重试」，**不写入历史**。

### 5.4 阅读问答的上下文

每次请求带：

1. 该题所属文章（段落编号）
2. 题干 + 4 个选项 + 用户选择 + 正确答案
3. 内置解析（`evidence_quote`、`explanation`、`distractors`）作为「已知参考」
4. 最近 2–3 轮对话

限制：文章过长时只带与题目相关的段落（`evidence_paragraph` 附近 2 段）+ 首段，控制 token。

---

## 6. 数据设计（SQLite）

### 6.1 位置与文件

```text
%APPDATA%\CET6Coach\ai.db      # 便携模式则在 <程序目录>\data\ai.db
```

与 `progress.json` 同目录，但独立文件：进度数据继续用 JSON，AI 数据用 SQLite，互不干扰。

### 6.2 表结构

```sql
PRAGMA user_version = 1;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS conversations (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,          -- translate_grade / reading_tutor / writing_grade
  title       TEXT,                   -- 列表里显示的名字，如「2023年12月 第2套 翻译批改」
  target_id   TEXT,                   -- 关联真题 id（如 2023-12-2-translation）
  model       TEXT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL,      -- user / assistant / system
  content         TEXT NOT NULL,
  prompt_tokens   INTEGER DEFAULT 0,
  completion_tokens INTEGER DEFAULT 0,
  prompt_version  TEXT,
  created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS ai_cache (
  key            TEXT PRIMARY KEY,    -- sha256(model + prompt_version + 输入摘要)
  payload        TEXT NOT NULL,
  model          TEXT,
  prompt_version TEXT,
  created_at     TEXT NOT NULL,
  expires_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON ai_cache(expires_at);

CREATE TABLE IF NOT EXISTS ai_grading (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  kind           TEXT NOT NULL,
  target_id      TEXT,
  input_digest   TEXT,
  result_json    TEXT NOT NULL,
  model          TEXT,
  prompt_version TEXT,
  created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grading_target ON ai_grading(kind, target_id, created_at);
```

可选：`messages` 建 FTS5 虚表用于全文搜索（若实现成本高，先做 `LIKE` 查询）。

### 6.3 清理策略

- 默认保留最近 **200 个会话**（设置项可改）；超出时删最旧的，连带消息与关联批改记录
- 缓存默认 30 天过期；每次启动时删一次过期缓存（`DELETE FROM ai_cache WHERE expires_at < now`）

---

## 7. 备份、导出与导入

### 7.1 参与备份

现有「设置与数据 → 备份学习记录」导出一个 JSON。扩展为**同时导出 AI 历史**：

- 方案 A（简单）：备份时把 `progress.json` 与 `ai.db` 打进一个 `.zip`
- 方案 B（兼容旧版）：备份仍是 JSON，但新增 `ai_history` 字段（把会话与消息序列化进去）

采用 **A**：`.zip` 内含 `progress.json` + `ai.db` + `manifest.json`（版本号、导出时间、文件校验和）。

**导入方式**：设置页点「导入备份」→ 弹出系统文件选择对话框（`tkinter.filedialog.askopenfilename`）→
用户选中 zip → 二次确认 → 导入。与现有的「导入备份」「导入单词 CSV」是同一套交互，不需要拖拽。

导入流程：识别 zip → 校验 manifest 与文件校验和 → 备份当前 `ai.db`/`progress.json` 为 `*.bak-时间戳` →
解压到临时目录 → 原子替换 → 提示「重启后生效」。

### 7.2 独立导出/导入（换电脑用）

设置页提供「导出 AI 历史」「导入 AI 历史」：

- 导出格式：单个 JSON 文件（便于查看与手动编辑）

```json
{
  "format": "cet6coach.ai_history",
  "version": 1,
  "exported_at": "2026-11-04T10:00:00",
  "conversations": [ ... ],
  "messages": [ ... ]
}
```

- 导入策略（重要）：
  - 默认**合并**：`conversations` 按 `(kind, target_id, created_at)` 去重；重名不冲突
  - 提供勾选项「清空现有 AI 历史后导入」
  - 导入前自动备份当前 `ai.db` 为 `ai.db.bak-时间戳`
  - 导入失败必须原子回滚（先写临时库，成功后再替换）

### 7.3 隐私说明

设置页明确写：「AI 历史保存在本机，备份/导出文件包含你的译文与对话，请妥善保管。」

---

## 8. 界面设计（轻改，分批做）

### 8.1 设置页新增「AI 服务」卡片

```text
AI 服务（可选）
  服务地址  [https://api.deepseek.com/v1        ]
  模型      [deepseek-chat            ] [拉取列表]
  API Key   [sk-****abcd]  [替换] [清除]
  [测试连接]        状态：未测试 / 连接成功 / 错误原因

  □ 启用 AI 批改（关闭后所有 AI 按钮隐藏）
  □ AI 历史参与备份
  [导出 AI 历史] [导入 AI 历史] [清空 AI 历史]
```

### 8.2 翻译页

- 右侧底部加「AI 批改」按钮（未配置 key 时点击提示去设置页）
- 批改中：按钮变「批改中…」并禁用，旁边显示转圈字符（`after` 动画）
- 批改完成：右侧下方出现结果卡片
  - 总分 + 三个维度进度条（Canvas）
  - 错误列表：学生译文片段（黄底）→ 建议（绿字）→ 原因
  - 「改进后的译文」可折叠
- 每次批改生成一条会话，可在「AI 历史」里回看

### 8.3 阅读页

- 每道题的解析区加「问 AI」按钮
- 点击后**在右侧内嵌**一个对话面板（`PanedWindow` 加一栏或右侧卡片整体切换），不另开窗口
- 输入框 + 发送按钮 + 对话列表（可滚动）；关闭面板恢复原题目区
- 顶部提示：「AI 讲解仅供参考；引用原文时会标注段落」

### 8.3.1 精简解析（省钱版）

现有解析是「原文定位 + 正确依据 + 每个干扰项分析」，信息全但长。AI 版做**压缩**，不是重写：

- 目标长度 **80–150 字**，最多 3 段：结论一句 → 原文依据一句（带段落号、引原文）→ 干扰项一句概括为什么错
- 只发给模型：题干、选项、现有解析（作为素材），要求「不许新增事实，只压缩」
- `max_tokens` 限制在 **400**；同一题只压缩一次，结果进缓存
- 若用户追问，再走对话接口展开，而不是一开始就给长文

### 8.4 AI 历史页（一级导航未来可加，或并入「复盘统计」）

- 左侧会话列表（按时间倒序、可按类型筛选）
- 右侧消息详情
- 顶栏搜索（先用 `LIKE`）

### 8.5 UI 轻改清单（与 AI 功能并行做）

1. 统一字号阶梯（标题 20/副标题 13/正文 10/说明 9）
2. 侧栏导航加图标（用字符或内置 PNG，避免额外依赖）
3. 按钮 hover / 按下反馈（`<Enter>` / `<Leave>` 改色）
4. 空状态卡片（无历史、未配置 key 时给引导）
5. Canvas 画环形进度、学习日历热力图
6. 加载动画（旋转字符或进度条）
7. 深色模式（色板集中，第二期做）

---

## 9. 错误与降级

| 场景 | 表现 |
| --- | --- |
| 未配置 key | AI 按钮置灰，点击弹出「去设置页填写 API Key」 |
| key 无效（401） | 提示「Key 无效或已过期」，不重试 |
| 额度/限流（402/429） | 「额度不足或请求过于频繁，稍后再试」 |
| 模型不存在（404） | 「模型名不存在，检查设置」 |
| 超时/断网 | 「网络不通，检查地址或代理」，可手动重试 |
| 返回不是合法 JSON | 自动重试 1 次；仍失败则显示原文 + 「解析失败」 |
| 引用片段不在原文 | 标记「未能核对引用」，仍展示但加警示 |

所有 AI 功能在未配置时**不报错、不阻塞**，原有功能完全可用。

---

## 10. 安全与隐私

- key 只存本机（凭据管理器/DPAPI），日志与备份不包含明文 key
- 只发送当次任务所需文本：原文、参考译文、用户译文、题干选项；**不发送**学习进度、错题统计
- 设置页首次启用时展示一次隐私提示，用户确认后写 `ai_consent=true`
- 提供「关闭 AI」总开关，关闭后不发起任何网络请求
- 导出文件包含用户内容，界面提示妥善保管

---

## 11. 测试策略

| 层 | 怎么测 |
| --- | --- |
| client | 本地 `http.server` 假服务：200/401/429/超时/非法 JSON 六种分支 |
| schemas | 合法/缺字段/类型错/分数越界的结构校验 |
| prompts | 快照测试：模板改动产生 diff，防止误改 |
| 引用校验 | 构造「引用不在原文」的假响应，断言被标记 |
| 历史 | 建库/写入/查询/清理/导出/导入往返（round-trip） |
| 备份 | 导出 zip → 换空目录 → 导入 → 会话数量一致 |
| 线程 | 断言请求期间主线程仍可响应（用 after 回调断言） |

全部测试不得真实联网；用 mock 或本地假服务。

---

## 12. 分阶段实施

| 阶段 | 内容 | 验收标准 |
| --- | --- | --- |
| **P0 基础设施** | 配置与 key 存储、client、设置页 AI 卡片、测试连接、SQLite 建库与迁移（详见 12.1） | 填 key 能测通；断网/错 key 有明确提示；不阻塞界面 |
| **P1 翻译批改** | prompts、结构化输出、校验、结果面板、历史落库 | 一篇译文能给出分项得分与错误列表；历史可回看 |
| **P2 历史与备份** | 历史页、导出/导入、备份 zip 扩展 | 换目录导入后历史完整；备份包含 AI 数据 |
| **P3 阅读问答** | 上下文拼装、多轮对话、引用校验、阅读页入口 | 能追问并保留上下文；引用能核对 |
| **P4 打磨** | 缓存、清理策略、成本显示、UI 轻改、错误文案统一 | 重复提问不重复计费；界面不再「素」 |

---


### 12.1 P0 详细设计（实施用）

P0 只做「地基」，不做任何 AI 业务功能。目标：**配置能存、key 能安全存、请求能发、错误能看懂、界面不卡**。

#### 12.1.1 配置项

存进 `progress.json` 的 `settings.ai`（与现有 settings 同级，走既有保存逻辑）：

| 键 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enabled` | bool | `false` | 总开关；关闭时不发任何请求，AI 按钮隐藏 |
| `base_url` | str | `https://api.deepseek.com/v1` | 末尾不带 `/`，请求时拼 `/chat/completions` |
| `model` | str | `deepseek-chat` | 可手填，或从 `/models` 拉取 |
| `temperature` | float | `0` | 批改类任务固定 0，保证稳定 |
| `timeout` | int | `60` | 秒 |
| `max_tokens` | int | `1200` | 单次响应上限 |
| `provider_hint` | str | `deepseek` | 仅用于界面显示预设 |
| `consent` | bool | `false` | 是否已确认过「内容会发送到第三方」的提示 |

校验规则：`base_url` 必须以 `http://` 或 `https://` 开头；`timeout` 取 10–180；`max_tokens` 取 128–8192；不符合时给字段级提示，不写库。

#### 12.1.2 API Key 存取

统一接口（`services/ai/keystore.py`）：

```text
KeyStore.get() -> str | None          # 读不到返回 None
KeyStore.set(key: str) -> None
KeyStore.clear() -> None
KeyStore.masked() -> str              # "sk-****abcd"，无 key 时返回空串
```

后端优先级（运行时自动选择，不暴露给用户）：

1. Windows 凭据管理器（`CredReadW` / `CredWriteW`，TargetName=`CET6Coach/ai-api-key`）
2. DPAPI 加密文件 `%APPDATA%\CET6Coach\ai_key.dat`（`CryptProtectData` / `CryptUnprotectData`）
3. 只读环境变量 `CET6COACH_API_KEY`（仅供高级用户/CI，界面显示「来自环境变量」）

硬性要求：

- 任何日志、备份、导出的文件**不得包含明文 key**
- 读写失败不能让程序崩溃：读失败 → 当作未配置；写失败 → 提示「无法保存密钥，请检查系统凭据服务」
- 切换 key 前先测试新 key，测试通过才覆盖旧 key

#### 12.1.3 设置页「AI 服务」卡片

字段：服务地址、模型（含「拉取列表」）、API Key（掩码 + 替换/清除）、测试连接按钮、状态文字、启用开关、历史参与备份开关。

状态机（P0 只做这一条链）：

```text
未配置 ──保存并测试──▶ 测试中 ──成功──▶ 可用
                          └──失败──▶ 显示错误原因（保留输入，可重试）
可用 ──清除 key──▶ 未配置
```

交互约束：

- 测试中：按钮禁用 + 显示「测试中…」（用 `after` 轮换字符，不用第三方动画库）
- 测试失败也允许保存（用户可能想先存下来回头弄），但 `enabled` 保持 false
- 「拉取列表」失败不阻塞手填
- 首次开启 `enabled` 时弹一次隐私提示，确认后写 `consent=true`

#### 12.1.4 AIClient 契约

```text
AIClient(settings, keystore)
  .chat(messages, *, temperature=None, max_tokens=None, json_mode=False) -> str
  .list_models() -> list[str]          # 失败返回 []
  .test() -> (ok: bool, detail: str)   # 供设置页调用
```

请求构造：

```text
POST {base_url}/chat/completions
Authorization: Bearer <key>
Content-Type: application/json
{"model": ..., "messages": [...], "temperature": ..., "max_tokens": ...}
# json_mode=True 时附加 "response_format": {"type": "json_object"}
```

**JSON 模式降级**：若返回 400 且响应体包含 `response_format` / `unsupported` / `invalid`，去掉该字段重试一次；仍失败则抛 `bad_response`。

错误归一化（统一异常 `AIError(kind, message, status)`）：

| kind | 触发 | 用户文案 |
| --- | --- | --- |
| `no_key` | 未配置 key | 请先在设置里填写 API Key |
| `bad_key` | 401 / 403 | API Key 无效或已过期 |
| `quota` | 402 / 429 | 额度不足或请求过于频繁，稍后再试 |
| `model_missing` | 404 且提示 model | 模型名不存在，检查设置 |
| `timeout` | 请求超时 | 请求超时，检查网络后重试 |
| `network` | 连接失败/DNS | 网络不通，检查服务地址或代理 |
| `bad_response` | 响应不是预期结构 | 服务返回异常，请重试 |
| `server` | 5xx | 服务端错误，稍后重试 |

重试策略：`timeout`/`network`/`server` 重试 1 次（间隔 1.5 秒）；4xx 一律不重试。

响应解析：优先 `choices[0].message.content`；兼容 `choices[0].text`；内容为空按 `bad_response` 处理。

日志：记录 `kind`、状态码、耗时、是否降级；**不记录 key、不记录完整请求体**。

#### 12.1.5 SQLite 层（`repositories/ai_store.py`）

建库位置与现有数据目录一致（支持 `%APPDATA%` 不可写时回退到程序目录 `data\`）。

初始化时执行：

```text
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;      -- 表结构见第 6 节
```

P0 只提供最小接口：

```text
AiStore(db_path)
  .ensure_schema()                     # 建表 + 版本迁移
  .create_conversation(kind, title, target_id, model) -> int
  .append_message(conv_id, role, content, prompt_version=None, usage=None) -> int
  .list_conversations(limit=50, offset=0) -> list[dict]
  .get_messages(conv_id) -> list[dict]
  .delete_conversation(conv_id)
  .integrity_ok() -> bool              # PRAGMA integrity_check
  .close()
```

约束：

- 所有写操作都是短事务，**不跨线程持有连接**（每次操作开/用/关，或使用线程本地连接）
- 建库失败（磁盘满/权限）→ 返回明确错误，不阻塞主程序启动
- 启动时 `integrity_ok()` 失败 → 自动重命名为 `ai.db.corrupt-时间戳` 后重建，并提示用户
- P0 不写业务数据，只保证「能建库、能写一条会话、能读回来」

#### 12.1.6 线程模型（这是 P0 最容易出错的地方）

规则：

1. **网络与 DB 写只在工作线程**；Tk 控件只在主线程碰
2. 统一封装 `run_in_background(task_fn, on_done, on_error)`：
   - 起 `threading.Thread(daemon=True)`
   - 完成后 `widget.after(0, lambda: on_done(result))`
   - 工作线程内 `try/except`，异常转成 `on_error(AIError)`
3. **防重复/防过期**：每次请求带自增 `seq`，回调时比对当前 `seq`，不一致就丢弃（避免用户连点导致旧结果覆盖新结果）
4. 请求期间禁用触发按钮；`after` 恢复
5. 无法真正取消 `urllib` 请求：丢弃结果即可，不做强制中断

#### 12.1.7 测试与验收

单元测试（不联网）：

- 错误映射：401/402/404/429/500/超时 → 对应 `kind`
- JSON 降级：第一次 400 + `response_format`，第二次 200 → 成功且记录了降级
- 脱敏：日志与导出内容不含 `sk-` 原文
- DB：建库 → 写会话 → 读回 → 删除；`user_version` 迁移；损坏库自动重建

手动验收（DoD）：

1. 不填 key 点测试 → 提示「请先填写 API Key」
2. 填错 key → 提示「Key 无效」（不崩溃、不卡界面）
3. 填对 key → 「连接成功」，重启软件后配置仍在
4. 断网测试 → 提示网络错误，界面仍可操作
5. 填一个不存在的模型 → 提示「模型名不存在」
6. 关闭 `enabled` → 不再发起任何请求

#### 12.1.8 P0 任务拆解（按顺序）

| # | 任务 | 产出 | 验收 |
| --- | --- | --- | --- |
| 1 | `repositories/ai_store.py` + 建表/迁移 + 单测 | 能建库、写读会话 | 单测通过；损坏库能自愈 |
| 2 | `services/ai/keystore.py` + 配置读写 | key 存取/掩码/清除 | 重启后仍能读；日志无明文 |
| 3 | `services/ai/client.py` + 错误归一化 + JSON 降级 | 假服务下 6 种分支 | 单测覆盖 401/429/超时/降级 |
| 4 | 设置页 AI 卡片（字段、测试连接、状态机） | 可操作界面 | 手动验收 1–6 通过 |
| 5 | `run_in_background` 线程封装 + 防重复 | 通用后台任务 | 连点不重复请求；界面不卡 |
| 6 | 联调 + 冒烟测试 + 文档更新 | P0 收尾 | 32+ 测试全绿；真实 key 手动跑通一次 |

预估：3–4 个工作日（不含真实服务商联调排错）。

#### 12.1.9 P0 明确不做

- 不做翻译批改、作文批改、阅读问答（P1/P3）
- 不做历史页 UI（P2）
- 不做缓存命中统计、成本统计
- 不做多 provider 自动切换、负载均衡

## 13. 风险与应对

| 风险 | 应对 |
| --- | --- |
| 不同「OpenAI 兼容」服务行为不一致 | 先探测 `response_format`，失败降级；错误归一化 |
| 批改分数不稳定 | 温度 0、固定 rubric、few-shot、分项打分 |
| 模型编造原文 | 要求引用 + 程序子串校验（复用现有做法） |
| token 成本高 | 缓存、限制上下文长度、可配 `max_tokens` |
| 用户 key 泄露 | 凭据管理器/DPAPI；界面掩码；日志脱敏 |
| SQLite 损坏 | 每次启动做 `PRAGMA integrity_check`；异常时自动备份并重建 |

---

## 14. 附录：提示词草案

### 翻译批改（`translate_grade@1`）

```text
你是六级翻译阅卷老师。请按六级评分标准批改学生译文。

【原文】{chinese}
【参考译文】{reference}
【学生译文】{student}

要求：
1. 总分 15 分，分别给出 准确/通顺/完整 三个维度（各 5 分）。
2. errors 中每条必须同时给出：学生译文中的原文片段（student）、建议表达（suggest）、原因（reason）、错误类型（type）。
3. student 字段必须是学生译文中逐字存在的片段，不允许改写。
4. 只能输出 JSON，不要解释、不要 Markdown 代码块。

输出结构：
{"score":0,"full_score":15,"dimensions":[{"name":"准确","score":0,"full":5,"comment":""}],
 "errors":[{"student":"","suggest":"","reason":"","type":""}],
 "rewrite":"","summary":""}
```

### 阅读问答（`reading_tutor@1`）

```text
你是六级阅读辅导老师。学生在做这道题时选了 {chosen}，正确答案是 {answer}。

【文章】{passage_with_paragraph_numbers}
【题干】{stem}
【选项】{options}
【现有解析】{analysis}

请回答学生的问题：{question}

要求：
1. 先给结论，再解释依据。
2. 引用原文时用「」括起来，并注明段落号。
3. 不要编造原文没有的内容；不确定就说不确定。
4. 不要生成新题。
```

---

## 15. 已确认与遗留

已确认（2026-11-03）：

1. 备份用 **zip**，导入时点按钮用系统文件对话框选文件
2. 历史保留 **最近 200 个会话**
3. 阅读问答 **右侧内嵌面板**
4. 精简解析 **要**，控制在 **80–150 字**

实现前仍需注意：

- 精简解析与完整解析并存时，界面上要标清楚哪个是内置核对版、哪个是 AI 压缩版
