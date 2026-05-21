from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from quant_intel.i18n import CATEGORY_ZH, PRIORITY_ZH, SOURCE_TYPE_ZH
from quant_intel.i18n import category_zh, priority_zh, source_type_zh
from quant_intel.models import utc_now_iso
from quant_intel.reports.reader_format import with_reader_format
from quant_intel.reports.sections import REPORT_SECTIONS
from quant_intel.reports.sections import row_section_keys, row_section_labels, section_counts


def build_home_dashboard(
    rows: list[dict[str, Any]],
    end_date: str,
    history_days: int,
    output_dir: Path,
    report_config: dict[str, int],
    source_stats: dict[str, int],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = [_with_display_labels(row) for row in rows]
    payload = {
        "end_date": end_date,
        "history_days": history_days,
        "generated_at": utc_now_iso(),
        "items": enriched,
        "source_stats": source_stats,
        "report_config": report_config,
        "day_counts": dict(Counter(_day(row) for row in enriched)),
        "section_counts": section_counts(enriched),
        "category_counts": dict(Counter(row["category"] for row in enriched)),
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
    }
    path = output_dir / "index.html"
    path.write_text(_render_home(payload), encoding="utf-8")
    return path


def _render_home(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>量化情报首页</title>
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
      --radius: 16px;
      --shadow: 0 1px 2px rgba(60, 64, 67, 0.16), 0 8px 24px rgba(60, 64, 67, 0.10);
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

    button, input, select {{ font: inherit; }}

    .topbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) minmax(300px, 760px);
      gap: 20px;
      align-items: center;
      padding: 16px 32px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(18px);
    }}

    .brand h1 {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin: 0;
      color: var(--ink);
      font-size: 25px;
      font-weight: 700;
      letter-spacing: -0.02em;
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

    .brand p {{
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .controls {{
      display: grid;
      grid-template-columns: 1fr 140px 160px 160px;
      gap: 10px;
    }}

    .control {{
      height: 44px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--ink);
      padding: 0 16px;
      outline: none;
    }}

    .control:focus {{
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.14);
    }}

    .layout {{
      display: grid;
      grid-template-columns: 280px minmax(440px, 1fr);
      gap: 22px;
      padding: 24px 32px 36px;
    }}

    .rail {{
      position: sticky;
      top: 92px;
      height: calc(100vh - 118px);
      overflow: auto;
    }}

    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 16px;
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
      color: var(--ink);
    }}

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
      font-weight: 800;
      letter-spacing: 0.02em;
    }}

    .nav-list {{
      display: grid;
      gap: 7px;
    }}

    .nav-button {{
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

    .nav-button:hover,
    .nav-button.active {{
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

    .feed-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      margin-bottom: 12px;
    }}

    .feed-head h2 {{
      margin: 0;
      font-size: 19px;
    }}

    .feed-head span {{
      color: var(--muted);
      font-size: 13px;
    }}

    .day-group {{
      margin-bottom: 22px;
    }}

    .day-title {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin: 0 0 14px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 10px;
    }}

    .day-title h3 {{
      margin: 0;
      font-size: 17px;
    }}

    .day-title a {{
      color: var(--blue);
      font-size: 13px;
      text-decoration: none;
      font-weight: 700;
    }}

    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 14px;
    }}

    .card {{
      position: relative;
      overflow: hidden;
      display: grid;
      gap: 12px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel);
      box-shadow: 0 1px 2px rgba(60, 64, 67, 0.10);
      padding: 18px;
      transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
    }}

    .card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 4px;
      background: linear-gradient(90deg, var(--blue), var(--red), var(--yellow), var(--green));
    }}

    .card:hover {{
      border-color: #c6dafc;
      box-shadow: var(--shadow);
      transform: translateY(-2px);
    }}

    .card-top {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
    }}

    .card h4 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.3;
    }}

    .score {{
      min-width: 52px;
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
      gap: 7px;
    }}

    .tag {{
      border: 1px solid transparent;
      border-radius: 999px;
      background: #f1f3f4;
      color: var(--muted);
      padding: 3px 8px;
      font-size: 12px;
    }}

    .tag:nth-child(1) {{ background: var(--blue-soft); color: #174ea6; }}
    .tag:nth-child(2) {{ background: var(--green-soft); color: #137333; }}
    .tag:nth-child(3) {{ background: var(--yellow-soft); color: #8a5a00; }}
    .tag:nth-child(4) {{ background: var(--red-soft); color: #b3261e; }}

    .summary {{
      margin: 0;
      color: #30342d;
      font-size: 14px;
      line-height: 1.48;
    }}

    .reader-format {{
      display: grid;
      gap: 8px;
    }}

    .reader-block {{
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}

    .reader-block:first-child {{
      border-top: 0;
      padding-top: 0;
    }}

    .reader-block h5 {{
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
      line-height: 1.48;
    }}

    .reader-block ol {{
      margin: 0;
      padding-left: 18px;
    }}

    .reader-reference {{
      color: var(--blue);
      text-decoration: none;
      font-weight: 800;
      font-size: 13px;
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

    .ref-row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}

    .ref-row a {{
      color: var(--green);
      text-decoration: none;
      font-weight: 800;
      font-size: 13px;
    }}

    .ref-row small {{
      overflow: hidden;
      color: var(--muted);
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .empty {{
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.72);
      color: var(--muted);
      padding: 28px;
    }}

    @media (max-width: 980px) {{
      .topbar,
      .layout {{
        grid-template-columns: 1fr;
      }}

      .rail {{
        position: static;
        height: auto;
      }}

      .controls {{
        grid-template-columns: 1fr 1fr;
      }}
    }}

    @media (max-width: 620px) {{
      .topbar,
      .layout {{
        padding: 14px;
      }}

      .controls,
      .metric-grid,
      .cards {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <h1>量化情报首页</h1>
      <p id="range-label"></p>
    </div>
    <div class="controls">
      <input class="control" id="search" type="search" placeholder="搜索标题、摘要、来源..." />
      <select class="control" id="day-select"></select>
      <select class="control" id="section-select"></select>
      <select class="control" id="category-select"></select>
    </div>
  </header>

  <main class="layout">
    <aside class="rail">
      <div class="metric-grid">
        <div class="metric"><b id="metric-items">0</b><span>总资讯</span></div>
        <div class="metric"><b id="metric-days">0</b><span>覆盖天数</span></div>
        <div class="metric"><b id="metric-high">0</b><span>高优先级</span></div>
        <div class="metric"><b id="metric-refs">0</b><span>原文链接</span></div>
      </div>

      <div class="section-label">日期</div>
      <div class="nav-list" id="day-list"></div>

      <div class="section-label">情报分区</div>
      <div class="nav-list" id="section-list"></div>

      <div class="section-label">分类</div>
      <div class="nav-list" id="category-list"></div>

      <div class="section-label">来源</div>
      <ul class="source-list" id="source-list"></ul>
    </aside>

    <section>
      <div class="feed-head">
        <h2 id="feed-title">最近资讯</h2>
        <span id="result-count"></span>
      </div>
      <div id="feed"></div>
    </section>
  </main>

  <script id="home-data" type="application/json">{data}</script>
  <script>
    const payload = JSON.parse(document.getElementById('home-data').textContent);
    const items = payload.items || [];
    const categoryLabels = payload.category_labels || {{}};
    const priorityLabels = payload.priority_labels || {{}};
    const sourceTypeLabels = payload.source_type_labels || {{}};
    const state = {{ query: '', day: 'All', section: 'All', category: 'All' }};
    const $ = (id) => document.getElementById(id);

    function init() {{
      $('range-label').textContent = `最近 ${{payload.history_days}} 天 - 每分类最多 ${{payload.report_config.max_items_per_category}} 篇 - 截止 ${{payload.end_date}} - 生成 ${{payload.generated_at}}`;
      $('metric-items').textContent = items.length;
      $('metric-days').textContent = Object.keys(payload.day_counts || {{}}).length;
      $('metric-high').textContent = items.filter((item) => priorityLabel(item.read_priority) === '高').length;
      $('metric-refs').textContent = items.filter((item) => item.reference_url).length;
      buildDayControls();
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
      $('day-select').addEventListener('change', (event) => {{
        state.day = event.target.value;
        render();
      }});
      $('section-select').addEventListener('change', (event) => {{
        state.section = event.target.value;
        render();
      }});
      $('category-select').addEventListener('change', (event) => {{
        state.category = event.target.value;
        render();
      }});
    }}

    function buildDayControls() {{
      const counts = payload.day_counts || {{}};
      const days = Object.keys(counts).sort().reverse();
      $('day-select').innerHTML = option('All', `全部日期 (${{items.length}})`) +
        days.map((day) => option(day, `${{day}} (${{counts[day]}})`)).join('');
      $('day-list').innerHTML = navButton('day', 'All', '全部', items.length) +
        days.map((day) => navButton('day', day, day, counts[day])).join('');
      bindNav('day');
    }}

    function buildSectionControls() {{
      const counts = payload.section_counts || {{}};
      const sections = payload.sections || [];
      $('section-select').innerHTML = option('All', `全部分区 (${{items.length}})`) +
        sections.filter((section) => counts[section.key])
          .map((section) => option(section.key, `${{section.label}} (${{counts[section.key]}})`))
          .join('');
      $('section-list').innerHTML = navButton('section', 'All', '全部', items.length) +
        sections.filter((section) => counts[section.key])
          .map((section) => navButton('section', section.key, section.label, counts[section.key]))
          .join('');
      bindNav('section');
    }}

    function buildCategoryControls() {{
      const counts = payload.category_counts || {{}};
      const categories = Object.keys(counts).sort();
      $('category-select').innerHTML = option('All', `全部分类 (${{items.length}})`) +
        categories.map((category) => option(category, `${{categoryLabel(category)}} (${{counts[category]}})`)).join('');
      $('category-list').innerHTML = navButton('category', 'All', '全部', items.length) +
        categories.map((category) => navButton('category', category, categoryLabel(category), counts[category])).join('');
      bindNav('category');
    }}

    function buildSourceList() {{
      const entries = Object.entries(payload.source_stats || {{}}).sort((a, b) => b[1] - a[1]);
      $('source-list').innerHTML = entries.length
        ? entries.map(([source, count]) => `<li><span>${{escapeHtml(source)}}</span><b>${{count}}</b></li>`).join('')
        : '<li><span>暂无来源</span><b>0</b></li>';
    }}

    function bindNav(kind) {{
      document.querySelectorAll(`[data-kind="${{kind}}"]`).forEach((button) => {{
        button.addEventListener('click', () => {{
          state[kind] = button.dataset.value;
          $(`${{kind}}-select`).value = state[kind];
          render();
        }});
      }});
    }}

    function render() {{
      const visible = items.filter(matchesFilters)
        .sort((a, b) => dayOf(b).localeCompare(dayOf(a)) || Number(b.final_score) - Number(a.final_score));
      $('feed-title').textContent = title();
      $('result-count').textContent = `展示 ${{visible.length}} / ${{items.length}} 条`;
      markActive();
      renderFeed(visible);
    }}

    function matchesFilters(item) {{
      if (state.day !== 'All' && dayOf(item) !== state.day) return false;
      if (state.section !== 'All' && !(item.report_sections || []).includes(state.section)) return false;
      if (state.category !== 'All' && item.category !== state.category) return false;
      if (!state.query) return true;
      const haystack = [
        item.title,
        item.display_title,
        item.source,
        item.source_type,
        sourceTypeLabel(item.source_type),
        item.category,
        categoryLabel(item.category),
        ...(item.report_section_labels || []),
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

    function renderFeed(visible) {{
      const feed = $('feed');
      if (!visible.length) {{
        feed.innerHTML = '<div class="empty">当前筛选条件下没有资讯。</div>';
        return;
      }}
      const grouped = groupByDay(visible);
      feed.innerHTML = Object.keys(grouped).sort().reverse().map((day) => `
        <section class="day-group">
          <div class="day-title">
            <h3>${{day}}</h3>
            <a href="${{day}}.html">打开当日看板</a>
          </div>
          <div class="cards">${{grouped[day].map(card).join('')}}</div>
        </section>
      `).join('');
    }}

    function card(item) {{
      return `
        <article class="card">
          <div class="card-top">
            <h4>${{escapeHtml(item.display_title || item.title)}}</h4>
            <div class="score">${{Number(item.final_score || 0).toFixed(1)}}</div>
          </div>
          <div class="meta">
            <span class="tag">${{escapeHtml(categoryLabel(item.category))}}</span>
            <span class="tag">${{escapeHtml((item.report_section_labels || [])[0] || '其他')}}</span>
            <span class="tag">${{escapeHtml(sourceTypeLabel(item.source_type))}}</span>
            <span class="tag">${{escapeHtml(priorityLabel(item.read_priority))}}</span>
          </div>
          ${{readerFormat(item)}}
        </article>
      `;
    }}

    function readerFormat(item) {{
      const points = itemKeyPoints(item);
      return `
        <div class="reader-format">
          <div class="reader-block">
            <h5>1. 这篇文章的太长不读</h5>
            <p>${{escapeHtml(item.tldr || item.one_line_summary || '')}}</p>
          </div>
          <div class="reader-block">
            <h5>2. 核心价值，对我量化的工作能够提供什么样的帮助</h5>
            <p>${{escapeHtml(item.core_value || '')}}</p>
          </div>
          <div class="reader-block">
            <h5>3. 关键核心点 / 论文或帖子摘要</h5>
            <ol>${{points.map((point) => `<li>${{escapeHtml(point)}}</li>`).join('')}}</ol>
          </div>
          <div class="reader-block">
            <h5>4. 原文链接</h5>
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

    function markActive() {{
      document.querySelectorAll('.nav-button').forEach((button) => {{
        button.classList.toggle('active', state[button.dataset.kind] === button.dataset.value);
      }});
    }}

    function title() {{
      const parts = [];
      if (state.day !== 'All') parts.push(state.day);
      if (state.section !== 'All') parts.push(sectionLabel(state.section));
      if (state.category !== 'All') parts.push(categoryLabel(state.category));
      return parts.length ? parts.join(' / ') : '最近资讯';
    }}

    function groupByDay(list) {{
      return list.reduce((acc, item) => {{
        const day = dayOf(item);
        acc[day] = acc[day] || [];
        acc[day].push(item);
        return acc;
      }}, {{}});
    }}

    function dayOf(item) {{
      return String(item.collected_at || '').slice(0, 10) || 'unknown';
    }}

    function navButton(kind, value, label, count) {{
      return `
        <button class="nav-button" type="button" data-kind="${{escapeAttr(kind)}}" data-value="${{escapeAttr(value)}}">
          <span>${{escapeHtml(label)}}</span>
          <span class="count">${{count}}</span>
        </button>
      `;
    }}

    function option(value, label) {{
      return `<option value="${{escapeAttr(value)}}">${{escapeHtml(label)}}</option>`;
    }}

    function categoryLabel(category) {{
      return categoryLabels[category] || category;
    }}

    function priorityLabel(priority) {{
      return priorityLabels[priority] || priority;
    }}

    function sourceTypeLabel(sourceType) {{
      return sourceTypeLabels[sourceType] || sourceType;
    }}

    function sectionLabel(key) {{
      const section = (payload.sections || []).find((item) => item.key === key);
      return section ? section.label : '其他';
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
    enriched = with_reader_format(row)
    enriched["report_sections"] = row_section_keys(row)
    enriched["report_section_labels"] = row_section_labels(row)
    enriched["category_label"] = category_zh(str(row.get("category", "")))
    enriched["priority_label"] = priority_zh(str(row.get("read_priority", "")))
    enriched["source_type_label"] = source_type_zh(str(row.get("source_type", "")))
    return enriched


def _day(row: dict[str, Any]) -> str:
    return str(row.get("collected_at", ""))[:10] or "unknown"
