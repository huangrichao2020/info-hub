#!/usr/bin/env python3
"""
每日机会扫描报告生成器
读取 daily-chance JSON 数据 → 输出 HTML 报告
"""
import json
import sys
from pathlib import Path
from datetime import datetime

GRADE_COLORS = {
    "S": {"bg": "rgba(255, 71, 87, 0.15)", "border": "#ff4757", "text": "#ff4757", "label": "重点讲解"},
    "A": {"bg": "rgba(255, 184, 0, 0.12)", "border": "#ffb800", "text": "#ffb800", "label": "简略分析"},
    "B": {"bg": "rgba(154, 163, 187, 0.08)", "border": "#4a5170", "text": "#9aa3bb", "label": "参考清单"},
}


def render_s_card(stock: dict) -> str:
    c = GRADE_COLORS["S"]
    signals_html = ""
    for sig in stock.get("signals", []):
        signals_html += f'<span class="signal">{sig}</span>'

    return f'''
    <div class="card s-card" style="background: {c['bg']}; border-color: {c['border']};">
      <div class="card-head">
        <span class="grade grade-s">S</span>
        <span class="ticker">{stock['code']}</span>
        <span class="name">{stock['name']}</span>
        <span class="meta">{stock['track']} · 卡脖子 {stock['choke_score']}/10</span>
      </div>
      <div class="logic"><strong>卡脖子定位：</strong>{stock['logic']}</div>
      <div class="reason"><strong>为什么是 S：</strong>{stock['reason']}</div>
      <div class="signals">{signals_html}</div>
      <div class="action">⚡ <strong>操作建议：</strong>{stock['action']}</div>
    </div>'''


def render_a_card(stock: dict) -> str:
    c = GRADE_COLORS["A"]
    return f'''
    <div class="card a-card" style="background: {c['bg']}; border-color: {c['border']};">
      <div class="card-head">
        <span class="grade grade-a">A</span>
        <span class="ticker">{stock['code']}</span>
        <span class="name">{stock['name']}</span>
        <span class="meta">{stock['track']} · {stock['choke_score']}/10</span>
      </div>
      <div class="reason">{stock['reason']}</div>
      {f'<div class="signals">{"".join("<span class=\'signal\'>" + s + "</span>" for s in stock.get("signals", []))}</div>' if stock.get('signals') else ''}
    </div>'''


def render_b_row(stock: dict) -> str:
    c = GRADE_COLORS["B"]
    signals = " · ".join(stock.get('signals', [])) or "—"
    return f'''
    <tr>
      <td><span class="ticker" style="font-size:11px;padding:2px 8px">{stock['code']}</span></td>
      <td><strong>{stock['name']}</strong></td>
      <td style="color:#9aa3bb;font-size:12px">{stock['track']}</td>
      <td style="color:#ffd700">{stock['choke_score']}/10</td>
      <td style="color:#9aa3bb;font-size:12px">{signals}</td>
    </tr>'''


def main():
    if len(sys.argv) < 2:
        print("Usage: python gen_daily_chance_report.py <data.json>")
        sys.exit(1)

    data_path = Path(sys.argv[1])
    with open(data_path) as f:
        result = json.load(f)

    d = result.get("data", result)
    date = d.get("date", datetime.now().strftime("%Y-%m-%d"))
    is_trade_time = d.get("is_trade_time", False)
    market = d.get("market", {})
    s_chances = d.get("S", [])
    a_chances = d.get("A", [])
    b_chances = d.get("B", [])
    stats = d.get("stats", {})

    # 主线展示
    main_lines = market.get("main_lines", [])[:5]
    main_lines_str = " · ".join(
        ml.get("name", str(ml)) if isinstance(ml, dict) else str(ml)
        for ml in main_lines
    ) or "（非交易时段无主线数据）"

    s_html = "\n".join(render_s_card(s) for s in s_chances)
    a_html = "\n".join(render_a_card(a) for a in a_chances)
    b_html = "\n".join(render_b_row(b) for b in b_chances)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>每日机会扫描 · {date} · info-hub</title>
<style>
  :root {{
    --bg: #0a0e1a; --bg-soft: #131829; --bg-card: #1a2138;
    --border: #2a3252; --accent: #00d4ff; --gold: #ffd700;
    --text: #e8ecf5; --text-soft: #9aa3bb;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.7; padding: 24px 16px 80px; }}
  .container {{ max-width: 920px; margin: 0 auto; }}
  .header {{ background: linear-gradient(135deg, #1a2138 0%, #131829 100%);
    border: 1px solid var(--border); border-radius: 16px; padding: 32px 28px;
    margin-bottom: 24px; position: relative; overflow: hidden; }}
  .header::before {{ content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #ff4757, #00d4ff, #ffd700); }}
  .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .header .meta {{ color: var(--text-soft); font-size: 14px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 20px; }}
  .stat {{ background: var(--bg-soft); padding: 14px; border-radius: 8px; border: 1px solid var(--border); }}
  .stat .num {{ font-size: 26px; font-weight: 700; }}
  .stat .label {{ font-size: 12px; color: var(--text-soft); margin-top: 4px; }}
  .section-title {{ font-size: 20px; font-weight: 700; margin: 24px 0 12px;
    display: flex; align-items: baseline; gap: 10px; }}
  .section-title .hint {{ font-size: 12px; color: var(--text-soft); font-weight: 400; }}
  .card {{ border: 1px solid var(--border); border-radius: 12px;
    padding: 20px; margin-bottom: 12px; }}
  .card-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }}
  .grade {{ padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 13px; }}
  .grade-s {{ background: #ff4757; color: #fff; }}
  .grade-a {{ background: #ffb800; color: #0a0e1a; }}
  .ticker {{ background: var(--accent); color: var(--bg); padding: 4px 10px;
    border-radius: 6px; font-size: 13px; font-weight: 700; }}
  .name {{ font-size: 18px; font-weight: 700; }}
  .meta {{ font-size: 12px; color: var(--text-soft); margin-left: auto; }}
  .logic, .reason, .action {{ font-size: 14px; margin-bottom: 8px; line-height: 1.7; }}
  .signals {{ display: flex; gap: 6px; margin: 8px 0; flex-wrap: wrap; }}
  .signal {{ background: rgba(0, 212, 255, 0.15); color: var(--accent);
    padding: 3px 8px; border-radius: 4px; font-size: 12px; border: 1px solid var(--accent); }}
  .action {{ background: rgba(0, 212, 255, 0.08); border-left: 3px solid var(--accent);
    padding: 10px 14px; border-radius: 6px; margin-top: 8px; }}
  .a-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
  .a-card .name {{ font-size: 15px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{ padding: 10px 8px; text-align: left; color: var(--text-soft); border-bottom: 1px solid var(--border); font-size: 12px; }}
  td {{ padding: 8px; border-bottom: 1px dashed var(--border); font-size: 13px; }}
  .footer {{ text-align: center; color: var(--text-soft); font-size: 12px;
    padding: 24px 16px; border-top: 1px solid var(--border); margin-top: 32px; }}
  .methodology {{ background: var(--bg-soft); border-radius: 8px; padding: 16px;
    margin-top: 16px; font-size: 13px; color: var(--text-soft); line-height: 1.8; }}
  .methodology strong {{ color: var(--accent); }}
  @media (max-width: 600px) {{
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
    .a-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>🎯 每日 S/A/B 机会扫描</h1>
    <div class="meta">
      <strong>{date}</strong> ·
      {'🟢 交易时段' if is_trade_time else '⚫ 非交易时段'} ·
      标的池 {stats.get('total_pool', 29)} 只 ·
      涨停数 {market.get('zt_count', 0)}
    </div>
    <div class="stats">
      <div class="stat"><div class="num" style="color:#ff4757">{stats.get('s_count', 0)}</div><div class="label">S 级重点</div></div>
      <div class="stat"><div class="num" style="color:#ffb800">{stats.get('a_count', 0)}</div><div class="label">A 级简略</div></div>
      <div class="stat"><div class="num" style="color:#9aa3bb">{stats.get('b_count', 0)}</div><div class="label">B 级参考</div></div>
      <div class="stat"><div class="num" style="color:#00d4ff">{len(main_lines)}</div><div class="label">主线方向</div></div>
    </div>
    <div class="meta" style="margin-top: 16px;">
      <strong>主线方向：</strong>{main_lines_str}
    </div>
  </div>

  <div class="section-title">🅢 S 级 · 重点讲解<span class="hint">每日 1-3 只 · 卡脖子定位 + 资金信号 + 介入建议</span></div>
  {s_html if s_html else '<div class="card"><div class="reason">今日无 S 级机会</div></div>'}

  <div class="section-title">🅐 A 级 · 简略分析<span class="hint">卡脖子定位 + 板块强势</span></div>
  <div class="a-grid">{a_html if a_html else '<div class="card"><div class="reason">今日无 A 级机会</div></div>'}</div>

  <div class="section-title">🅑 B 级 · 参考清单<span class="hint">板块异动或卡脖子参考</span></div>
  <div class="card">
    <table>
      <thead><tr><th>代码</th><th>名称</th><th>赛道</th><th>卡脖子</th><th>信号</th></tr></thead>
      <tbody>{b_html if b_html else '<tr><td colspan="5" style="text-align:center;color:#9aa3bb;padding:20px">无 B 级标的</td></tr>'}</tbody>
    </table>
  </div>

  <div class="methodology">
    <strong>方法论声明</strong> · 基于 Serenity 卡脖子框架 v2.0 + 当日市场信号综合评分。<br>
    <strong>S 级</strong> = 卡脖子评分 ≥ 8.5 + 主线/板块联动 OR 卡脖子 ≥ 9.0 顶级标的<br>
    <strong>A 级</strong> = 卡脖子评分 ≥ 7.5 + 板块强势<br>
    <strong>B 级</strong> = 卡脖子 ≥ 6.5 · 仅作板块联动观察<br>
    数据源: fetch_full_snapshot() + ChokePointAnalyzer · 归档：info-hub/股票研究/daily-chance/{date}/<br>
    ⚠️ 不构成投资建议 · 实时行情 / PE / 资金数据需独立核实
  </div>

  <div class="footer">
    Mavis 出品 · Serenity 卡脖子框架 · info-hub / 每日机会扫描<br>
    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 自动生成
  </div>

</div>
</body>
</html>'''

    out_path = data_path.parent / "report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 报告生成: {out_path}")
    print(f"   S 级: {len(s_chances)} | A 级: {len(a_chances)} | B 级: {len(b_chances)}")


if __name__ == "__main__":
    main()