# Lore Agent

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![MCP Ready](https://img.shields.io/badge/MCP-Ready-brightgreen.svg)

[English](README.md)

> 通用大模型在专业领域常常不够准、也不够新。Lore Agent 通过“在线研究补充 + 本地知识沉淀”形成可持续的知识飞轮，让 AI 在你的领域越用越强，也为你提供、维护人类学习的知识库。通过 MCP 无缝接入 Claude Code 与 VS Code Copilot。

## 核心机制：研究 → 沉淀 → 越用越强

大模型的训练数据是静态的。当你需要它回答专业领域或最新进展时，它只能靠通用知识猜。

Lore Agent 给它加了一个**知识飞轮**：

```
你的提问
    │
    ▼
在线研究（AI agent 搜索 + SearXNG + 学术 API）
    │
    ▼
结构化合成（带引用来源、置信度、不确定性标注）
    │
    ▼
本地沉淀（Markdown 知识卡片 + BM25 索引）
    │
    ▼
下次提问时，AI 先查本地 ──命中?──► 直接用，快且准
    │ 未命中
    ▼
再次在线研究 → 沉淀 → 索引更新 ──► 知识库持续增长
```

每一轮使用都在积累。有不会的问题，AI直接在线搜索，并沉淀到本地，既给AI看、提供完整的设计指导、代码编写方案，也形成人类可读的知识库，让你快速学习领会相关内容。

知识卡片有完整的生命周期管理：**draft → reviewed → trusted → stale → deprecated**。过时的知识会被标记，新研究会覆盖旧结论。

## 与同类项目对比

| | Lore Agent | Prompt-based Wiki (如 llm-wiki-agent) |
|---|---|---|
| **研究能力** | AI agent 搜索 + SearXNG 元搜索 + OpenAlex / Semantic Scholar 学术 API + 本地 BM25 / embedding，证据归一化合并 | 依赖 LLM 自身能力，无独立搜索管线 |
| **知识生命周期** | draft → reviewed → trusted → stale → deprecated | 无——文件就是文件 |
| **知识飞轮** | 研究 → 沉淀 → 复用 → 越用越强 | 单向：LLM 写，人读 |
| **答案质量** | 结构化 JSON：claims + 证据 ID + 不确定性 | 原始文本 |
| **图谱与互联** | `[[wiki-links]]`、反向链接、vis.js 图谱 | 基于文件夹，无交叉引用 |

## 更多特色

- **多视角研究** — 可从学术、技术、应用、对立、历史五个视角并行研究同一问题，避免单一来源偏差
- **Obsidian 兼容** — 知识卡片是标准 Markdown + YAML frontmatter + `[[wiki-links]]`，可直接用 Obsidian 浏览管理
- **知识治理 CLI** — 校验 frontmatter、检测孤立卡片和断链、发现重复、管理卡片状态流转
- **Provider 容错** — 各搜索源独立容错，外网不可用时仅用本地检索

## 快速开始

```bash
# 克隆并安装
git clone https://github.com/zfy465914233/lore-agent.git
cd lore-agent
pip install -r requirements.txt

# 构建知识索引
python scripts/local_index.py --output indexes/local/index.json

# （可选）启动 SearXNG 用于在线研究
docker compose up -d
```

通过 MCP 接入 Claude Code 和 VS Code Copilot——配置已预置，启动即用：

- **Claude Code**：`.mcp.json` 已配好，`cd` 到项目目录启动即可
- **VS Code Copilot**：`.vscode/mcp.json` 已配好，打开项目启用 agent 模式即可

### 嵌入到已有项目

```bash
cp -r lore-agent/ your-project/lore-agent/
cd your-project && python lore-agent/setup_mcp.py
```

自动生成配置。知识库在**你的项目里**，不在 lore-agent 内部。

## MCP 工具

AI agent 通过 6 个 MCP 工具与知识库交互：

| 工具 | 说明 |
|------|------|
| `query_knowledge` | 搜索本地知识库 |
| `save_research` | 保存研究结果为知识卡片（支持 Mermaid 图表、来源图片） |
| `list_knowledge` | 浏览所有知识卡片 |
| `capture_answer` | 快速捕获问答为草稿卡片 |
| `ingest_source` | 摄入 URL 或文本到知识库 |
| `build_graph` | 生成交互式知识图谱（vis.js） |

## 项目结构

```
lore-agent/
├── mcp_server.py              # MCP 服务器（6 个工具）
├── setup_mcp.py               # 嵌入已有项目
├── docker-compose.yml         # SearXNG
├── requirements.txt
├── schemas/                   # 答案 + 证据 JSON schema
├── scripts/                   # 检索、研究、合成、治理、图谱
├── knowledge/                 # 知识卡片（Markdown + YAML frontmatter）
├── indexes/                   # 生成的索引（gitignored）
└── tests/                     # 192 个测试，约 5 秒
```

## 基准测试

```bash
python scripts/run_eval.py --dry-run
```

| 指标 | 得分 |
|------|------|
| 路由准确率 | 100% (8/8) |
| 检索命中率 | 100% (8/8) |
| 最低引用达标 | 100% (8/8) |
| 错误数 | 0 |

## 许可证

MIT — 见 [LICENSE](LICENSE)。
