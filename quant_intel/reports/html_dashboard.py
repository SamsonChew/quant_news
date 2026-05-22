from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_intel.i18n import CATEGORY_ZH, PRIORITY_ZH, SOURCE_TYPE_ZH
from quant_intel.i18n import category_zh, priority_zh, source_type_zh
from quant_intel.models import utc_now_iso
from quant_intel.reports.daily_report import select_report_rows
from quant_intel.reports.reader_format import with_reader_format
from quant_intel.reports.sections import REPORT_SECTIONS
from quant_intel.reports.sections import row_section_keys, row_section_labels, section_counts


def build_html_dashboard(
    rows: list[dict[str, Any]],
    report_date: str,
    output_dir: Path,
    report_config: dict[str, int],
    source_stats: dict[str, int],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = select_report_rows(rows, report_config)
    localized = [_with_display_labels(row) for row in selected]
    payload = {
        "report_date": report_date,
        "generated_at": utc_now_iso(),
        "items": localized,
        "source_stats": source_stats,
        "category_counts": dict(Counter(row["category"] for row in localized)),
        "section_counts": section_counts(localized),
        "sections": [
            {
                "key": section.key,
                "label": section.label,
                "description": section.description,
            }
            for section in REPORT_SECTIONS
        ],
        "category_labels": CATEGORY_ZH,
        "priority_labels": PRIORITY_ZH,
        "source_type_labels": SOURCE_TYPE_ZH,
        "report_config": report_config,
    }
    html = _render_dashboard(payload)
    path = output_dir / f"{report_date}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _render_dashboard(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>每日量化情报 - {payload['report_date']}</title>
  <style>
    :root {{
      --bg: #ffffff;
      --panel: #ffffff;
      --ink: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --blue: #1a73e8;
      --red: #ea4335;
      --yellow: #fbbc04;
      --green: #34a853;
      --blue-soft: #e8f0fe;
      --green-soft: #e6f4ea;
      --yellow-soft: #fef7e0;
      --red-soft: #fce8e6;
      --shadow: 0 1px 2px rgba(60, 64, 67, 0.16), 0 8px 24px rgba(60, 64, 67, 0.10);
      --radius: 16px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(66, 133, 244, 0.07), transparent 30%),
        radial-gradient(circle at top right, rgba(251, 188, 4, 0.08), transparent 26%),
        var(--bg);
      color: var(--ink);
      font-family: "Google Sans", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}

    button,
    input,
    select {{
      font: inherit;
    }}

    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }}

    .topbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) minmax(280px, 620px);
      gap: 24px;
      align-items: center;
      padding: 16px 32px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(18px);
    }}

    .brand {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      min-width: 0;
    }}

    .brand h1 {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.02em;
      white-space: nowrap;
    }}

    .brand h1::before {{
      content: "";
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background:
        conic-gradient(from 0deg, var(--blue) 0 25%, var(--red) 0 50%, var(--yellow) 0 75%, var(--green) 0 100%);
      box-shadow: inset 0 0 0 7px #fff;
    }}

    .date-pill {{
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}

    .controls {{
      display: grid;
      grid-template-columns: 1fr 170px 170px 150px;
      gap: 10px;
    }}

    .control {{
      height: 42px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--ink);
      padding: 0 12px;
      outline: none;
    }}

    .control:focus {{
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.14);
    }}

    .layout {{
      display: grid;
      grid-template-columns: 260px minmax(420px, 1fr) 420px;
      gap: 22px;
      padding: 24px 32px 36px;
    }}

    .rail,
    .detail {{
      position: sticky;
      top: 86px;
      height: calc(100vh - 112px);
      overflow: auto;
    }}

    .rail,
    .detail,
    .feed {{
      min-width: 0;
    }}

    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 18px;
    }}

    .metric {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      padding: 12px;
      box-shadow: 0 1px 2px rgba(60, 64, 67, 0.08);
    }}

    .metric:nth-child(1) {{ border-top: 3px solid var(--blue); }}
    .metric:nth-child(2) {{ border-top: 3px solid var(--red); }}
    .metric:nth-child(3) {{ border-top: 3px solid var(--yellow); }}
    .metric:nth-child(4) {{ border-top: 3px solid var(--green); }}

    .metric b {{
      display: block;
      font-size: 22px;
      line-height: 1;
    }}

    .metric span {{
      display: block;
      margin-top: 7px;
      color: var(--muted);
      font-size: 12px;
    }}

    .section-label {{
      margin: 18px 0 8px;
      color: var(--blue);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}

    .category-list {{
      display: grid;
      gap: 7px;
    }}

    .category-button {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      width: 100%;
      min-height: 38px;
      border: 1px solid transparent;
      border-radius: 999px;
      background: transparent;
      color: var(--ink);
      padding: 8px 10px;
      text-align: left;
      cursor: pointer;
    }}

    .category-button:hover,
    .category-button.active {{
      border-color: transparent;
      background: var(--blue-soft);
      color: #174ea6;
    }}

    .count {{
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }}

    .source-list {{
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}

    .source-list li {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
    }}

    .feed-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 12px;
    }}

    .feed-header h2 {{
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }}

    .result-count {{
      color: var(--muted);
      font-size: 13px;
    }}

    .items {{
      display: grid;
      gap: 10px;
    }}

    .item {{
      position: relative;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: 0 1px 2px rgba(60, 64, 67, 0.10);
      padding: 18px;
      cursor: pointer;
      transition: border-color 140ms ease, transform 140ms ease, box-shadow 140ms ease;
    }}

    .item::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 4px;
      background: linear-gradient(90deg, var(--blue), var(--red), var(--yellow), var(--green));
    }}

    .item:hover,
    .item.active {{
      border-color: #c6dafc;
      box-shadow: var(--shadow);
      transform: translateY(-2px);
    }}

    .item-top {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 14px;
      align-items: start;
    }}

    .item h3 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.28;
    }}

    .score {{
      min-width: 54px;
      border-radius: 999px;
      background: var(--blue-soft);
      color: #174ea6;
      padding: 6px 8px;
      text-align: center;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
    }}

    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0;
      color: var(--muted);
      font-size: 12px;
    }}

    .tag {{
      border: 1px solid transparent;
      border-radius: 999px;
      background: #f1f3f4;
      padding: 3px 8px;
    }}

    .tag:nth-child(1) {{ background: var(--blue-soft); color: #174ea6; }}
    .tag:nth-child(2) {{ background: var(--green-soft); color: #137333; }}
    .tag:nth-child(3) {{ background: var(--yellow-soft); color: #8a5a00; }}
    .tag:nth-child(4) {{ background: var(--red-soft); color: #b3261e; }}

    .summary {{
      margin: 0;
      color: #30342d;
      font-size: 14px;
      line-height: 1.45;
    }}

    .reference-link {{
      display: inline-flex;
      width: fit-content;
      border-top: 1px solid var(--line);
      color: var(--blue);
      padding-top: 9px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 800;
    }}

    .reader-format {{
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }}

    .reader-format.compact {{
      gap: 8px;
    }}

    .reader-block {{
      border-top: 1px solid var(--line);
      padding-top: 9px;
    }}

    .reader-block:first-child {{
      border-top: 0;
      padding-top: 0;
    }}

    .reader-block h4 {{
      margin: 0 0 5px;
      color: var(--blue);
      font-size: 12px;
      font-weight: 700;
    }}

    .reader-block p,
    .reader-block li {{
      margin: 0;
      color: #30342d;
      font-size: 13px;
      line-height: 1.5;
    }}

    .reader-block ol {{
      margin: 0;
      padding-left: 18px;
    }}

    .reader-reference {{
      color: var(--blue);
      text-decoration: none;
      font-size: 13px;
      font-weight: 800;
      overflow-wrap: anywhere;
    }}

    .reference-url {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}

    .detail {{
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 18px;
    }}

    .detail h2 {{
      margin: 0 0 12px;
      font-size: 20px;
      line-height: 1.2;
    }}

    .detail-block {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }}

    .detail-block h3 {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.02em;
    }}

    .detail-block p,
    .detail-block li {{
      color: #30342d;
      font-size: 14px;
      line-height: 1.55;
    }}

    .detail-block ul {{
      margin: 0;
      padding-left: 18px;
    }}

    .breakdown {{
      display: grid;
      gap: 8px;
    }}

    .bar {{
      display: grid;
      grid-template-columns: 118px 1fr 40px;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }}

    .bar-track {{
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: #e7eadf;
    }}

    .bar-fill {{
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--blue), var(--green), var(--yellow), var(--red));
    }}

    .open-link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      margin-top: 16px;
      border: 1px solid var(--blue);
      border-radius: var(--radius);
      color: var(--blue);
      text-decoration: none;
      padding: 0 12px;
      font-weight: 700;
    }}

    .empty {{
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      padding: 28px;
      color: var(--muted);
      background: var(--panel);
    }}

    @media (max-width: 1180px) {{
      .layout {{
        grid-template-columns: 220px 1fr;
      }}

      .detail {{
        position: static;
        grid-column: 1 / -1;
        height: auto;
      }}
    }}

    @media (max-width: 820px) {{
      .topbar {{
        grid-template-columns: 1fr;
        padding: 14px;
      }}

      .brand {{
        display: grid;
        gap: 4px;
      }}

      .brand h1 {{
        white-space: normal;
        font-size: 21px;
      }}

      .controls {{
        grid-template-columns: 1fr;
      }}

      .layout {{
        grid-template-columns: 1fr;
        padding: 14px;
      }}

      .rail,
      .detail {{
        position: static;
        height: auto;
      }}

      .metric-grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>量化情报台</h1>
        <span class="date-pill" id="report-date"></span>
      </div>
      <div class="controls">
        <input class="control" id="search" type="search" placeholder="搜索标题、摘要、分类..." />
        <select class="control" id="section-select"></select>
        <select class="control" id="category-select"></select>
        <select class="control" id="sort-select">
          <option value="score">按评分排序</option>
          <option value="priority">按优先级排序</option>
          <option value="source">按来源排序</option>
        </select>
      </div>
    </header>

    <main class="layout">
      <aside class="rail">
        <div class="metric-grid">
          <div class="metric"><b id="metric-items">0</b><span>报告条目</span></div>
          <div class="metric"><b id="metric-categories">0</b><span>分类数量</span></div>
          <div class="metric"><b id="metric-high">0</b><span>高优先级</span></div>
          <div class="metric"><b id="metric-avg">0.0</b><span>平均评分</span></div>
        </div>

        <div class="section-label">两条主线</div>
        <div class="category-list" id="section-list"></div>

        <div class="section-label">细分标签</div>
        <div class="category-list" id="category-list"></div>

        <div class="section-label">主力来源</div>
        <ul class="source-list" id="source-list"></ul>
      </aside>

      <section class="feed">
        <div class="feed-header">
          <h2 id="feed-title">今日情报</h2>
          <span class="result-count" id="result-count"></span>
        </div>
        <div class="items" id="items"></div>
      </section>

      <aside class="detail" id="detail"></aside>
    </main>
  </div>

  <script id="dashboard-data" type="application/json">{data}</script>
  <script>
    const payload = JSON.parse(document.getElementById('dashboard-data').textContent);
    const items = payload.items || [];
    const categoryLabels = payload.category_labels || {{}};
    const priorityLabels = payload.priority_labels || {{}};
    const sourceTypeLabels = payload.source_type_labels || {{}};
    const state = {{
      query: '',
      section: 'All',
      category: 'All',
      sort: 'score',
      activeId: items[0]?.id || null,
    }};

    const priorityRank = {{ High: 3, Medium: 2, Low: 1, '高': 3, '中': 2, '低': 1 }};
    const $ = (id) => document.getElementById(id);

    function init() {{
      $('report-date').textContent = payload.report_date + ' - 主力源：arXiv / 知乎 / QuantML / 大型论坛 - 生成时间 ' + payload.generated_at;
      $('metric-items').textContent = items.length;
      $('metric-categories').textContent = new Set(items.map((item) => item.category)).size;
      $('metric-high').textContent = items.filter((item) => priorityLabel(item.read_priority) === '高').length;
      $('metric-avg').textContent = averageScore(items).toFixed(1);

      buildSectionControls();
      buildCategoryControls();
      buildSourceList();
      bindControls();
      render();
    }}

    function bindControls() {{
      $('search').addEventListener('input', (event) => {{
        state.query = event.target.value.trim().toLowerCase();
        render();
      }});
      $('category-select').addEventListener('change', (event) => {{
        state.category = event.target.value;
        render();
      }});
      $('section-select').addEventListener('change', (event) => {{
        state.section = event.target.value;
        render();
      }});
      $('sort-select').addEventListener('change', (event) => {{
        state.sort = event.target.value;
        render();
      }});
    }}

    function buildCategoryControls() {{
      const counts = countBy(items, 'category');
      const categories = Object.keys(counts).sort();
      const select = $('category-select');
      select.innerHTML = option('All', `全部细分标签 (${{items.length}})`) +
        categories.map((category) => option(category, `${{categoryLabel(category)}} (${{counts[category]}})`)).join('');

      const list = $('category-list');
      list.innerHTML = categoryButton('All', items.length) +
        categories.map((category) => categoryButton(category, counts[category])).join('');

      list.querySelectorAll('button').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.category = button.dataset.category;
          select.value = state.category;
          render();
        }});
      }});
    }}

    function buildSectionControls() {{
      const counts = payload.section_counts || {{}};
      const sections = payload.sections || [];
      const select = $('section-select');
      select.innerHTML = option('All', `全部主线 (${{items.length}})`) +
        sections
          .filter((section) => counts[section.key])
          .map((section) => option(section.key, `${{section.label}} (${{counts[section.key]}})`))
          .join('');

      const list = $('section-list');
      list.innerHTML = sectionButton('All', '全部', items.length) +
        sections
          .filter((section) => counts[section.key])
          .map((section) => sectionButton(section.key, section.label, counts[section.key]))
          .join('');

      list.querySelectorAll('button').forEach((button) => {{
        button.addEventListener('click', () => {{
          state.section = button.dataset.section;
          select.value = state.section;
          render();
        }});
      }});
    }}

    function buildSourceList() {{
      const stats = payload.source_stats || {{}};
      const entries = Object.entries(stats)
        .filter(([source]) => !source.startsWith('fetched:'))
        .sort((a, b) => b[1] - a[1]);
      $('source-list').innerHTML = entries.length
        ? entries.map(([source, count]) => `<li><span>${{escapeHtml(source)}}</span><b>${{count}}</b></li>`).join('')
        : '<li><span>暂无来源统计</span><b>0</b></li>';
    }}

    function render() {{
      let visible = items.filter(matchesFilters);
      visible = sortItems(visible);
      if (!visible.some((item) => item.id === state.activeId)) {{
        state.activeId = visible[0]?.id || null;
      }}

      $('feed-title').textContent = feedTitle();
      $('result-count').textContent = `展示 ${{visible.length}} 条 - 两条主线每条最多 ${{payload.report_config.max_items_per_category}} 条`;
      renderSectionActive();
      renderCategoryActive();
      renderItems(visible);
      renderDetail(visible.find((item) => item.id === state.activeId) || visible[0]);
    }}

    function matchesFilters(item) {{
      const sectionMatch = state.section === 'All' || (item.report_sections || []).includes(state.section);
      if (!sectionMatch) return false;
      const categoryMatch = state.category === 'All' || item.category === state.category;
      if (!categoryMatch) return false;
      if (!state.query) return true;
      const haystack = [
        item.title,
        item.display_title,
        item.source,
        item.source_type,
        item.category,
        categoryLabel(item.category),
        sectionLabel(item.report_sections?.[0]),
        sourceTypeLabel(item.source_type),
        priorityLabel(item.read_priority),
        item.one_line_summary,
        item.technical_summary,
        item.quant_relevance,
        item.possible_use_case,
        item.tldr,
        item.core_value,
        ...(item.key_points_list || []),
        item.reference_url,
      ].join(' ').toLowerCase();
      return haystack.includes(state.query);
    }}

    function sortItems(list) {{
      return [...list].sort((a, b) => {{
        if (state.sort === 'priority') {{
          return (priorityRank[b.read_priority] || 0) - (priorityRank[a.read_priority] || 0)
            || b.final_score - a.final_score;
        }}
        if (state.sort === 'source') {{
          return a.source.localeCompare(b.source) || b.final_score - a.final_score;
        }}
        return b.final_score - a.final_score;
      }});
    }}

    function renderCategoryActive() {{
      document.querySelectorAll('.category-button').forEach((button) => {{
        button.classList.toggle('active', button.dataset.category === state.category);
      }});
    }}

    function renderSectionActive() {{
      document.querySelectorAll('.section-button').forEach((button) => {{
        button.classList.toggle('active', button.dataset.section === state.section);
      }});
    }}

    function renderItems(visible) {{
      const container = $('items');
      if (!visible.length) {{
        container.innerHTML = '<div class="empty">当前筛选条件下没有匹配内容。</div>';
        return;
      }}
      container.innerHTML = visible.map((item) => `
        <article class="item ${{item.id === state.activeId ? 'active' : ''}}" data-id="${{escapeAttr(item.id)}}">
          <div class="item-top">
            <h3>${{escapeHtml(item.display_title || item.title)}}</h3>
            <div class="score">${{Number(item.final_score).toFixed(1)}}</div>
          </div>
          <div class="meta">
            <span class="tag">${{escapeHtml(sectionLabel(item.report_sections?.[0]))}}</span>
            <span class="tag">${{escapeHtml(categoryLabel(item.category))}}</span>
            <span class="tag">${{escapeHtml(item.source)}}</span>
            <span class="tag">${{escapeHtml(priorityLabel(item.read_priority))}}</span>
          </div>
          ${{readerFormat(item, true)}}
        </article>
      `).join('');

      container.querySelectorAll('.item').forEach((node) => {{
        node.addEventListener('click', () => {{
          state.activeId = node.dataset.id;
          render();
        }});
      }});
    }}

    function renderDetail(item) {{
      const detail = $('detail');
      if (!item) {{
        detail.innerHTML = '<div class="empty">选择一条内容查看详情。</div>';
        return;
      }}

      detail.innerHTML = `
        <h2>${{escapeHtml(item.display_title || item.title)}}</h2>
        <div class="meta">
          <span class="tag">${{escapeHtml(categoryLabel(item.category))}}</span>
          <span class="tag">${{escapeHtml(sourceTypeLabel(item.source_type))}}</span>
          <span class="tag">${{escapeHtml(priorityLabel(item.read_priority))}}</span>
        </div>

        ${{readerFormat(item, false)}}

        <div class="detail-block">
          <h3>评分拆解</h3>
          <div class="breakdown">
            ${{bar('相关性', item.relevance_score)}}
            ${{bar('新颖度', item.novelty_score)}}
            ${{bar('学术性', item.academic_score)}}
            ${{bar('讨论度', item.discussion_score)}}
            ${{bar('可行动性', item.actionable_score)}}
          </div>
        </div>

      `;
    }}

    function readerFormat(item, compact) {{
      const points = itemKeyPoints(item);
      return `
        <div class="reader-format ${{compact ? 'compact' : ''}}">
          <div class="reader-block">
            <h4>1. 这篇文章的太长不读</h4>
            <p>${{escapeHtml(item.tldr || item.one_line_summary || '')}}</p>
          </div>
          <div class="reader-block">
            <h4>2. 核心价值，对我量化的工作能够提供什么样的帮助</h4>
            <p>${{escapeHtml(item.core_value || '')}}</p>
          </div>
          <div class="reader-block">
            <h4>3. 关键核心点 / 论文或帖子摘要</h4>
            <ol>${{points.map((point) => `<li>${{escapeHtml(point)}}</li>`).join('')}}</ol>
          </div>
          <div class="reader-block">
            <h4>4. 原文链接</h4>
            ${{referenceHtml(item)}}
          </div>
        </div>
      `;
    }}

    function itemKeyPoints(item) {{
      const points = Array.isArray(item.key_points_list)
        ? item.key_points_list
        : (Array.isArray(item.key_points) ? item.key_points : []);
      const clean = points.filter(Boolean).slice(0, 3);
      return clean.length ? clean : ['需要打开原文进一步确认方法、数据和适用边界。'];
    }}

    function referenceHtml(item) {{
      const url = item.reference_url || '';
      if (!url) return '<p>暂无可打开链接</p>';
      return `
        <a class="reader-reference" href="${{escapeAttr(url)}}" target="_blank" rel="noopener noreferrer">打开原文</a>
        <small class="reference-url">${{escapeHtml(url)}}</small>
      `;
    }}

    function bar(label, value) {{
      const score = Number(value || 0);
      const width = Math.max(0, Math.min(100, score * 10));
      return `
        <div class="bar">
          <span>${{label}}</span>
          <div class="bar-track"><div class="bar-fill" style="width: ${{width}}%"></div></div>
          <b>${{score.toFixed(1)}}</b>
        </div>
      `;
    }}

    function countBy(list, key) {{
      return list.reduce((acc, item) => {{
        acc[item[key]] = (acc[item[key]] || 0) + 1;
        return acc;
      }}, {{}});
    }}

    function averageScore(list) {{
      if (!list.length) return 0;
      return list.reduce((sum, item) => sum + Number(item.final_score || 0), 0) / list.length;
    }}

    function option(value, label) {{
      return `<option value="${{escapeAttr(value)}}">${{escapeHtml(label)}}</option>`;
    }}

    function sectionButton(section, label, count) {{
      return `
        <button class="category-button section-button" type="button" data-section="${{escapeAttr(section)}}">
          <span>${{escapeHtml(label)}}</span>
          <span class="count">${{count}}</span>
        </button>
      `;
    }}

    function categoryButton(category, count) {{
      return `
        <button class="category-button" type="button" data-category="${{escapeAttr(category)}}">
          <span>${{escapeHtml(category === 'All' ? '全部' : categoryLabel(category))}}</span>
          <span class="count">${{count}}</span>
        </button>
      `;
    }}

    function categoryLabel(category) {{
      return categoryLabels[category] || category;
    }}

    function sectionLabel(sectionKey) {{
      const section = (payload.sections || []).find((item) => item.key === sectionKey);
      return section ? section.label : '其他';
    }}

    function feedTitle() {{
      const parts = [];
      if (state.section !== 'All') parts.push(sectionLabel(state.section));
      if (state.category !== 'All') parts.push(categoryLabel(state.category));
      return parts.length ? parts.join(' / ') : '今日情报';
    }}

    function priorityLabel(priority) {{
      return priorityLabels[priority] || priority;
    }}

    function sourceTypeLabel(sourceType) {{
      return sourceTypeLabels[sourceType] || sourceType;
    }}

    function escapeHtml(value) {{
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }}

    function escapeAttr(value) {{
      return escapeHtml(value).replaceAll('`', '&#096;');
    }}

    init();
  </script>
</body>
</html>
"""


def _with_display_labels(row: dict[str, Any]) -> dict[str, Any]:
    localized = with_reader_format(row)
    localized["report_sections"] = row_section_keys(row)
    localized["report_section_labels"] = row_section_labels(row)
    localized["category_label"] = category_zh(str(row.get("category", "")))
    localized["priority_label"] = priority_zh(str(row.get("read_priority", "")))
    localized["source_type_label"] = source_type_zh(str(row.get("source_type", "")))
    return localized
