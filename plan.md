# Quant Intelligence Platform Plan

## 1. 项目目标

构建一个每天自动更新的量化信息集成平台，用来收集、清洗、总结和筛选量化相关内容。

核心目标：

- 每天自动从论文、论坛、代码仓库、博客等来源收集信息。
- 每条内容都生成结构化 summary，方便快速阅读。
- 自动分类、去重、打分，避免信息过载。
- 每天生成一份 Daily Quant Intelligence Report。
- 支持后续扩展成 dashboard、搜索系统、主题追踪和推送系统。

第一阶段先做情报引擎，不急着做复杂前端。先保证日报质量高、信息密度高、可持续更新。

## 2. MVP 范围

第一版需要实现：

- 自动采集数据。
- 统一数据 schema。
- 内容去重。
- 每条 item 生成 summary。
- 自动分类。
- 自动打分。
- 每个类别最多保留 5 条。
- 生成 Markdown 日报。
- 本地保存历史数据。

推荐 MVP 技术栈：

- Python
- SQLite 或 DuckDB
- feedparser
- requests
- BeautifulSoup
- arXiv API
- GitHub API
- Reddit RSS 或 Reddit API
- DeepSeek API、本地规则摘要或后续可替换 LLM provider
- cron、launchd 或 GitHub Actions 定时运行

## 3. 第一批数据源

### 论文源

- arXiv q-fin
- arXiv stat.ML 中和 finance、trading、portfolio、risk 相关论文
- arXiv cs.LG 中和 finance、trading、time series 相关论文
- Papers with Code 中 finance、time series、trading 相关项目

第二阶段再考虑：

- SSRN
- NBER
- academic finance working papers

这些来源的元数据和抓取稳定性更复杂，适合后置。

### 论坛源

- Reddit r/algotrading
- Reddit r/quant
- Quant StackExchange
- QuantConnect Forum
- Elite Trader
- Wilmott Forum

### 代码源

- GitHub search: quant
- GitHub search: backtesting
- GitHub search: alpha factor
- GitHub search: portfolio optimization
- GitHub search: market microstructure
- GitHub search: trading strategy
- GitHub trending 或 recently updated repos

### 博客和 RSS 源

- 量化研究博客
- market microstructure blogs
- ML for finance blogs
- hedge fund engineering blogs
- systematic trading research notes

## 4. 统一数据模型

每条内容统一成一个 item：

```text
id
source
source_type
title
url
authors
published_at
collected_at
raw_text
abstract
content_hash
category
tags
language
```

来源类型：

```text
paper
forum
github
blog
news
```

## 5. Summary 结构

每个收集到的 item 都必须生成 summary，方便快速扫读。

统一 summary 字段：

```text
one_line_summary
technical_summary
key_points
quant_relevance
possible_use_case
limitations
read_priority
```

字段说明：

- `one_line_summary`: 一句话讲清楚它是什么。
- `technical_summary`: 3 到 5 句话的技术摘要。
- `key_points`: 核心要点，通常 3 条。
- `quant_relevance`: 它和量化研究、交易、风控或工程的关系。
- `possible_use_case`: 是否可用于策略、因子、风控、执行、数据工程或研究工具。
- `limitations`: 明显限制、风险、争议或需要验证的地方。
- `read_priority`: High、Medium、Low。

所有前端和 Markdown report 必须统一展示成四段式：

```text
1. 这篇文章的太长不读
2. 核心价值，对我量化的工作能够提供什么样的帮助
3. 关键核心点 / 论文或帖子摘要
4. 原文链接
```

不同来源的 summary 侧重点：

论文：

- 研究问题
- 方法
- 数据
- 结果
- 可复现价值
- 量化应用可能性

论坛：

- 讨论主题
- 主流观点
- 争议点
- 实践经验
- 是否有可行动 insight

GitHub：

- 项目做什么
- 成熟度
- 维护活跃度
- 适合什么场景
- 是否值得试用

博客：

- 核心观点
- 技术含量
- 是否有可复现方法
- 是否有可行动策略想法

## 6. 分类体系

第一版分类：

```text
阿尔法 / 因子研究
统计套利
组合构建
风险管理
期权 / 波动率
市场微观结构
交易执行 / 交易成本
金融机器学习
量化大模型 / 智能体
加密资产量化
数据工程
回测 / 研究工具
```

每个 item 至少有一个主分类，也可以有多个 tags。

## 7. 打分机制

每条内容生成以下分数：

```text
relevance_score
novelty_score
academic_score
discussion_score
actionable_score
final_score
```

分数含义：

- `relevance_score`: 和量化主题的相关程度。
- `novelty_score`: 是否新颖，是否区别于已有内容。
- `academic_score`: 论文或技术内容的严肃程度与质量代理。
- `discussion_score`: 论坛讨论热度、评论量、互动质量。
- `actionable_score`: 是否值得进一步研究、复现、实现或跟踪。
- `final_score`: 用于日报排序的综合分。

初版可以用规则加 LLM 判断，后续再做可配置权重。

推荐配置：

```yaml
scoring:
  relevance_weight: 0.30
  novelty_weight: 0.20
  academic_weight: 0.15
  discussion_weight: 0.15
  actionable_weight: 0.20
```

## 8. 信息限流规则

为了避免日报信息过载，每个类别每天最多展示 5 条。

规则：

```text
for each category:
  sort items by final_score descending
  keep top 5 only
```

推荐 report 配置：

```yaml
report:
  max_items_per_category: 5
  max_total_items: 40
  executive_brief_items: 5
```

默认策略：

- 每个类别最多 5 条。
- 全局最多 40 条。
- Executive Brief 最多 5 条。
- 如果某个类别当天没有高质量内容，可以不展示该类别。
- 如果所有类别加起来超过全局上限，按 `final_score` 做二次截断。

这样日报保持高密度，不变成链接堆。

## 9. 去重与聚合

同一篇论文、讨论或工具可能出现在多个来源，需要做去重和聚合。

基础去重：

- URL 去重
- title 归一化后去重
- content hash 去重
- abstract hash 去重

进阶聚合：

```text
paper <-> forum discussion <-> GitHub implementation <-> blog commentary
```

目标是让 report 能表达：

```text
这篇论文今天在 Reddit 和 QuantConnect 都被讨论；
有人已经发布了 GitHub 实现；
主要争议是交易成本后 alpha 是否仍然成立。
```

这会是平台区别于普通 RSS 聚合器的核心价值。

## 10. 数据库设计

第一版用 SQLite 或 DuckDB。

### items

```text
id
source
source_type
title
url
authors
published_at
collected_at
raw_text
abstract
content_hash
category
tags
language
```

### summaries

```text
item_id
one_line_summary
technical_summary
key_points
quant_relevance
possible_use_case
limitations
read_priority
model_name
created_at
```

### scores

```text
item_id
relevance_score
novelty_score
academic_score
discussion_score
actionable_score
final_score
created_at
```

### reports

```text
report_date
report_path
generated_at
item_count
source_stats
```

## 11. Pipeline

每日 pipeline：

```text
fetch sources
normalize records
deduplicate
extract readable text
classify topic
generate per-item summary
score each item
apply per-category limit
apply global report limit
generate daily report
save database records
save report artifact
```

关键原则：

- 先抓取足够多，再通过分类和分数限流。
- 每条进入 report 的内容必须有 summary。
- 低质量内容可以入库，但不进入日报。
- report 生成逻辑必须可配置。

## 12. Daily Report 格式

日报建议结构：

```text
# Daily Quant Intelligence Report - YYYY-MM-DD

## Executive Brief
今天最重要的 3 到 5 条量化信息。

## Top Papers
每篇论文包含标题、summary、方法、量化用途、限制和链接。

## Forum Signals
高价值讨论，包含共识、争议和实践经验。

## Code & Tools
新发现的 GitHub 项目、backtest 框架、数据工具。

## Strategy Ideas
可能值得研究、复现或跟踪的策略和因子方向。

## Category Sections
按分类展示，每个类别最多 5 条。

## Watchlist
需要持续追踪的主题。

## Source Stats
今天各来源抓取数量、保留数量、去重数量。
```

每条 item 在 report 中的展示格式：

```text
### Title

- Source: arXiv / Reddit / GitHub / Blog
- Category: Machine Learning for Finance
- Priority: High
- Score: 8.7
- Link: https://...

Summary:
One-line summary.

Key Points:
- Point 1
- Point 2
- Point 3

Quant Relevance:
Why this matters for quant research or trading.

Possible Use Case:
How it may be used.

Limitations:
What needs caution or validation.
```

## 13. 推荐目录结构

```text
quant_intel/
  config/
    sources.yaml
    scoring.yaml
    report.yaml
  sources/
    arxiv_source.py
    reddit_source.py
    github_source.py
    rss_source.py
  pipeline/
    ingest.py
    normalize.py
    dedupe.py
    classify.py
    summarize.py
    score.py
  storage/
    db.py
    schema.sql
  reports/
    daily_report.py
  output/
    daily/
  run_daily.py
```

## 14. MVP 里程碑

### v0.1 项目骨架

目标：

- 建立目录结构。
- 建立配置文件。
- 建立数据库 schema。
- 建立 `run_daily.py` 入口。

产出：

- 可运行的空 pipeline。
- 本地数据库文件。
- 基础日志。

### v0.2 数据采集

目标：

- 接入 arXiv q-fin。
- 接入 Reddit RSS 或 API。
- 接入 GitHub search。
- 支持 RSS 博客源。

产出：

- 每天能抓取真实内容。
- 内容保存到 `items` 表。

### v0.3 Summary Engine

目标：

- 对每条 item 生成结构化 summary。
- 支持不同 source_type 的 summary prompt。
- 支持 `auto`、`deepseek`、`rule` 三种 summary provider。
- LLM key 只从环境变量或 `.env` 读取，不写入代码和配置。
- summary 保存到 `summaries` 表。

产出：

- 每条可读内容都有 summary。
- 没有 LLM token 时自动回退到规则摘要。

### v0.4 Scoring Engine

目标：

- 生成 relevance、novelty、academic、discussion、actionable 分数。
- 生成 final_score。
- 支持配置权重。

产出：

- 可排序的内容池。

### v0.5 Daily Report

目标：

- 每个类别最多展示 5 条。
- 全局最多展示 40 条。
- 生成 Markdown report。
- 保存 report 历史。

产出：

- `output/daily/YYYY-MM-DD.md`

### v0.6 自动化

目标：

- 每天自动运行。
- 失败重试。
- 输出日志。

产出：

- cron、launchd 或 GitHub Actions workflow。

## 15. 后续扩展

第二阶段可以加入：

- HTML report
- Streamlit dashboard
- FastAPI backend
- 搜索功能
- 收藏功能
- topic watchlist
- 邮件推送
- Telegram 或 Slack 推送
- paper、forum、repo、blog 的 entity linking
- 历史主题趋势
- 每周 recap report

第三阶段可以加入：

- topic clustering
- 信息系数式评估
- 用户反馈学习
- 个性化 watchlist
- strategy idea backlog
- 自动生成研究任务
- 自动生成复现 checklist

## 16. 第一阶段执行建议

第一步先实现：

```text
arXiv q-fin 抓取
GitHub quant repo 抓取
SQLite 存储
每条 item 的 summary
按类别最多 5 条生成 Markdown 日报
```

这样最快能看到真实日报，再根据日报质量调整：

- 数据源
- 分类体系
- summary 模板
- 打分权重
- 每类限流数量
- report 结构

第一阶段的判断标准不是功能多，而是每天生成的 report 是否真的值得读。
