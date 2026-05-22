# samson 量化情报台

每天自动收集量化相关论文、知乎/社交导入、QuantML 图谱线索和大型论坛讨论，生成结构化中文摘要、分类分数，并输出一份不过载的中文每日量化情报报告。

## 当前版本

已实现最小可用版本骨架：

- arXiv 论文源
- QuantML 金融 AI 文献图谱源
- 知乎本地 JSON 导入源
- 大型论坛和问答站点 RSS 源
- GitHub 搜索源保留但默认关闭
- 本地数据库存储
- 规则分类
- 规则摘要，并可选接入 DeepSeek 生成高质量中文摘要
- 可配置打分
- 每个分类限制展示数量
- Markdown 每日报告
- 中文静态网页看板，支持搜索、分类筛选、排序和详情视图
- 两条老板视角主线：`深度学习量化未来` 和 `AI 量化工具`
- 所有资讯统一四段式阅读格式：太长不读、核心价值、关键核心点、原文链接
- 离线样例模式，方便本地冒烟测试

## 快速运行

先跑离线样例，确认整条流水线正常：

```bash
python run_daily.py --sample
```

使用 DeepSeek 生成更像研究助理写出来的中文摘要：

```bash
python run_daily.py --summary-provider deepseek
```

没有配置 DeepSeek key 时，系统会自动回退到规则摘要，不会中断日报生成。

输出：

```text
data/quant_intel.sqlite
output/daily/YYYY-MM-DD.md
output/daily/YYYY-MM-DD.html
output/daily/index.html
```

跑真实数据源：

```bash
python run_daily.py
```

如果网络源失败，运行器会打印提示并继续处理其他来源。

网页看板可以直接用浏览器打开，也可以用本地服务访问。

启动本地网站：

```bash
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory output/daily
```

浏览器访问：

```text
http://127.0.0.1:8000/
```

首页 `index.html` 会展示今天和过去几天的资讯流；默认最近 7 天。每条资讯都会显示原文链接，并且两条主线每条最多展示 5 篇。

每条资讯统一展示：

```text
1. 这篇文章的太长不读
2. 核心价值，对我量化的工作能够提供什么样的帮助
3. 关键核心点 / 论文或帖子摘要
4. 原文链接
```

调整首页历史窗口：

```bash
python run_daily.py --history-days 14
```

## 配置

数据源：

```text
config/sources.json
```

打分权重：

```text
config/scoring.json
```

日报限制：

```text
config/report.json
```

默认限制：

- 每条主线最多 5 条
- 全局最多 60 条
- Executive Brief 最多 5 条

## 测试

```bash
python -m unittest discover -s tests
```

## 目录

```text
quant_intel/
  sources/
  pipeline/
  storage/
  reports/
config/
tests/
run_daily.py
plan.md
```

## 下一步

- 增加更强的去重和跨来源聚合。
- 增加历史 report 浏览和趋势图。

## 大模型密钥

当前版本不需要大模型密钥，也能完成采集、分类、打分、分区拆分和中文界面。

如果要把英文论文、QuantML 图谱线索、知乎导入和论坛内容自动总结成高质量中文摘要，可以配置 DeepSeek。建议用环境变量或 `.env`，不要写进代码：

```bash
export DEEPSEEK_API_KEY="..."
export DEEPSEEK_MODEL="deepseek-chat"
```

也可以把同样的变量放进项目根目录的 `.env`。`.env` 已经被 `.gitignore` 忽略，避免误提交。

运行模式：

```bash
python run_daily.py --summary-provider auto
python run_daily.py --summary-provider deepseek
python run_daily.py --summary-provider rule
```

- `auto`: 有 `DEEPSEEK_API_KEY` 时使用 DeepSeek，否则使用规则摘要。
- `deepseek`: 优先使用 DeepSeek；如果 key 缺失或调用失败，会打印提示并回退。
- `rule`: 强制使用本地规则摘要，不消耗额度。

安全提醒：如果 API key 曾经出现在聊天、截图或日志里，建议在 DeepSeek 后台 rotate，然后使用新的 key。

## 主力数据源

当前默认主力来源：

- `arXiv`: q-fin、金融机器学习、深度学习、强化学习、组合优化和市场微观结构论文。
- `知乎`: 通过本地 JSON 注入，避免依赖不稳定的网页抓取。
- `QuantML`: 抓取 `https://www.quantml.cn/` 上的金融 AI 文献图谱线索。
- `大型论坛`: Reddit `r/algotrading`、Reddit `r/quant`、Quant StackExchange、QuantNet Quant Matters。

默认报告和首页只展示这四类主力来源。GitHub 搜索源仍在代码里，但 `config/sources.json` 默认关闭；后面如果要补工具生态，可以再打开。

## 知乎数据

把知乎数据写到：

```text
data/social_items.json
```

格式参考：

```text
examples/social_items.example.json
```

每条内容需要包含 `source`、`source_type`、`title`、`url`、`published_at`、`text`。知乎内容的 `source_type` 用 `zhihu`。
