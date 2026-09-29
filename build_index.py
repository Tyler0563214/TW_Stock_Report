#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TW_Stock_Report 索引產生器
掃描 repo 內所有 .html 報告，從 <title> 取出真實公司名稱，
產生可搜尋、分組、依日期排序的 index.html。

用法：  python build_index.py
新增報告後重新執行即可更新索引。
"""

import os
import re
import html
from datetime import datetime, date

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "index.html")
SKIP = {"index.html", "build_index.py"}

# 市場類報告的檔名前綴 -> (分類標籤, 排序權重)
MARKET_KINDS = {
    "premarket":  ("早盤戰情室", 1),
    "intraday":   ("盤中戰況",   2),
    "postmarket": ("盤後分析",   3),
    "eod":        ("盤後總結",   4),
}

# 從標題中要剝掉的報告類型字樣（用於萃取公司名）
NOISE = re.compile(
    r"深度研究報告|深度分析報告|投資研究報告|持倉決策報告|深度報告|研究報告|分析報告"
    r"|持倉決策|持倉分析|深度分析|投資研究|選片建議|選片"
    r"|第\s*\d+\s*次(?:報告)?|首次(?:深度)?(?:報告)?"
    r"|更新版?|零重複版|[vV]\d+|深度|報告"
)

# 判定「這是一份個股研究報告」的標題關鍵字
REPORT_HINT = re.compile(r"研究報告|分析報告|深度報告|投資研究|深度分析|持倉決策")

# 分隔符與雜訊符號（含各種破折號 / 全形符號）
SEPS = re.compile(r"[|｜—–─━‐‑‒―\-_·,、:：/]+")


def get_title(path):
    """讀出檔案前 8KB 內的 <title>。"""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(8192)
    except OSError:
        return ""
    m = re.search(r"<title>(.*?)</title>", head, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse_date(s):
    """YYYYMMDD 或 YYYY-MM-DD / YYYY/MM/DD -> date"""
    s = re.sub(r"[-/]", "", s)
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def clean_name(title, code):
    """從標題萃取公司名稱。"""
    name = title
    # 移除代碼（含括號形式）
    name = re.sub(r"[（(]\s*" + code + r"\s*[)）]", " ", name)
    name = re.sub(r"\b" + code + r"\b", " ", name)
    # 移除日期
    name = re.sub(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", " ", name)
    name = re.sub(r"\d{8}", " ", name)
    # 移除報告類型字樣與分隔符（先剝字樣，再清符號，最後去頭尾殘渣）
    name = NOISE.sub(" ", name)
    name = SEPS.sub(" ", name)
    name = re.sub(r"[（()）]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(" -_·—–─")
    # 還原 -KY / -DR 等台股掛牌後綴（前一步清符號時會被拆開）
    name = re.sub(r"\s+(KY|DR)$", r"-\1", name)
    return name or code


def main():
    stocks = {}   # code -> {"name": str, "reports": [ {...} ]}
    market = []   # 市場類
    other = []    # 其他

    for fn in sorted(os.listdir(REPO)):
        if not fn.lower().endswith(".html") or fn in SKIP:
            continue
        path = os.path.join(REPO, fn)
        title = get_title(path)
        stem = fn[:-5]

        # --- 市場類報告 ---
        mk = re.match(r"(premarket|intraday|postmarket|eod)[-_]?(\d{8})", stem, re.I)
        if mk:
            label, weight = MARKET_KINDS[mk.group(1).lower()]
            market.append({
                "file": fn, "title": title, "label": label,
                "weight": weight, "date": parse_date(mk.group(2)),
            })
            continue

        # --- 個股報告：抓 4 位數代碼 + 可選 8 位數日期 ---
        # 需符合 {代碼}_report_{日期} 命名，或標題本身看得出是研究報告，
        # 避免把恰好含 4 位數字的非報告檔（如選片建議）誤歸為個股。
        cm = re.search(r"(?<!\d)(\d{4})(?!\d)", stem)
        dm = re.search(r"(?<!\d)(\d{8})(?!\d)", stem)
        is_report = bool(re.match(r"^\d{4}_report_\d{8}$", stem)) or bool(
            REPORT_HINT.search(title))
        if cm and is_report:
            code = cm.group(1)
            d = parse_date(dm.group(1)) if dm else None
            mtime = date.fromtimestamp(os.path.getmtime(path))
            entry = {
                "file": fn, "title": title,
                "date": d or mtime,
                "dated": d is not None,   # False = 檔名無日期，用檔案時間推估
            }
            s = stocks.setdefault(code, {"name": None, "reports": []})
            s["reports"].append(entry)
            # 公司名以「有日期且最新」的報告標題為準
            cand = clean_name(title, code) if title else None
            if cand and (s["name"] is None or (d and entry["date"] >= max(
                    r["date"] for r in s["reports"]))):
                s["name"] = cand
            continue

        other.append({"file": fn, "title": title,
                      "date": date.fromtimestamp(os.path.getmtime(path))})

    # 排序：每檔個股報告新到舊；個股依「最新報告日期」新到舊
    for s in stocks.values():
        s["reports"].sort(key=lambda r: (r["date"], r["file"]), reverse=True)
        if not s["name"]:
            s["name"] = "—"
    order = sorted(stocks.items(),
                   key=lambda kv: (kv[1]["reports"][0]["date"], kv[0]),
                   reverse=True)

    market.sort(key=lambda r: (r["date"] or date.min, -r["weight"]), reverse=True)
    other.sort(key=lambda r: r["date"], reverse=True)

    total = sum(len(s["reports"]) for _, s in order) + len(market) + len(other)
    latest = max([r["date"] for _, s in order for r in s["reports"]]
                 + [r["date"] for r in market if r["date"]] or [date.today()])

    # ---------- 組 HTML ----------
    E = html.escape
    parts = []

    for code, s in order:
        reps = s["reports"]
        newest = reps[0]
        rows = []
        for i, r in enumerate(reps):
            badge = '<span class="badge-new">最新</span>' if i == 0 else ""
            est = ' <span class="est" title="檔名無日期，以檔案時間推估">≈</span>' if not r["dated"] else ""
            nth = f'<span class="nth">第{len(reps) - i}份</span>' if len(reps) > 1 else ""
            rows.append(
                f'<li><a href="{E(r["file"])}">'
                f'<time>{r["date"].isoformat()}</time>{est}'
                f'<span class="rtitle">{E(r["title"] or r["file"])}</span>'
                f'{nth}{badge}</a></li>'
            )
        parts.append(
            f'<article class="stock" data-search="{E((s["name"] + " " + code).lower())}">'
            f'<header><h3>{E(s["name"])}</h3>'
            f'<span class="code">{code}</span>'
            f'<span class="count">{len(reps)} 份</span>'
            f'<span class="last">最新 {newest["date"].isoformat()}</span></header>'
            f'<ul class="reports">{"".join(rows)}</ul></article>'
        )
    stock_html = "\n".join(parts)

    mrows = []
    for r in market:
        d = r["date"].isoformat() if r["date"] else "—"
        mrows.append(
            f'<li data-search="{E((r["label"] + " " + d).lower())}">'
            f'<a href="{E(r["file"])}"><time>{d}</time>'
            f'<span class="mlabel">{E(r["label"])}</span>'
            f'<span class="rtitle">{E(r["title"] or r["file"])}</span></a></li>'
        )
    market_html = "".join(mrows)

    orows = []
    for r in other:
        orows.append(
            f'<li data-search="{E((r["title"] + " " + r["file"]).lower())}">'
            f'<a href="{E(r["file"])}"><time>{r["date"].isoformat()}</time>'
            f'<span class="rtitle">{E(r["title"] or r["file"])}</span></a></li>'
        )
    other_html = "".join(orows)
    other_block = ""
    if orows:
        other_block = f"""
  <section id="sec-other" data-group="other">
    <h2 class="sec-head">其他文件 <span class="sec-count">{len(other)}</span></h2>
    <div class="card"><ul class="reports flat">{other_html}</ul></div>
  </section>"""

    page = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>台股研究報告索引 | TW Stock Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  :root{{
    --bg:#eef2f7;--card:#fff;--text:#16212e;--muted:#64748b;--faint:#94a3b8;
    --border:#dde4ec;--accent:#1e3a5f;--accent2:#2d6a9f;--hl:#0d9488;
    --mono:'SF Mono',Menlo,Consolas,'Courier New',monospace;
  }}
  body{{background:var(--bg);color:var(--text);
    font-family:'Helvetica Neue',-apple-system,'Segoe UI','Microsoft JhengHei',Arial,sans-serif;
    font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}}
  time,.code,.count{{font-variant-numeric:tabular-nums}}

  /* header */
  .masthead{{background:linear-gradient(135deg,#0f1d2e 0%,#1e3a5f 55%,#2d6a9f 100%);
    color:#fff;padding:38px 24px 30px}}
  .mh-inner{{max-width:940px;margin:0 auto}}
  .mh-eyebrow{{font-size:11px;letter-spacing:2.5px;text-transform:uppercase;opacity:.62;margin-bottom:8px}}
  .mh-title{{font-size:29px;font-weight:800;letter-spacing:-.5px}}
  .mh-sub{{font-size:14px;opacity:.78;margin-top:6px}}
  .mh-stats{{display:flex;gap:26px;flex-wrap:wrap;margin-top:20px}}
  .stat .n{{font-size:23px;font-weight:800;line-height:1}}
  .stat .l{{font-size:11px;opacity:.65;letter-spacing:1px;margin-top:3px}}

  /* toolbar */
  .toolbar{{position:sticky;top:0;z-index:20;background:rgba(238,242,247,.94);
    backdrop-filter:blur(8px);border-bottom:1px solid var(--border);padding:12px 24px}}
  .tb-inner{{max-width:940px;margin:0 auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
  #q{{flex:1;min-width:200px;padding:9px 13px;border:1px solid var(--border);border-radius:9px;
    font-size:14px;background:#fff;color:var(--text);font-family:inherit}}
  #q:focus{{outline:2px solid var(--accent2);outline-offset:1px;border-color:var(--accent2)}}
  .tabs{{display:flex;gap:4px;background:#e2e8f0;border-radius:9px;padding:3px}}
  .tab{{border:0;background:transparent;color:var(--muted);font:600 13px inherit;
    padding:6px 13px;border-radius:7px;cursor:pointer;font-family:inherit}}
  .tab[aria-selected="true"]{{background:#fff;color:var(--accent);box-shadow:0 1px 3px rgba(0,0,0,.1)}}
  .tab:focus-visible{{outline:2px solid var(--accent2);outline-offset:1px}}

  /* layout */
  .wrap{{max-width:940px;margin:0 auto;padding:22px 24px 64px}}
  .sec-head{{font-size:13px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;
    color:var(--muted);margin:26px 0 12px;display:flex;align-items:center;gap:9px}}
  .sec-head::before{{content:'';width:3px;height:14px;background:var(--accent);border-radius:2px}}
  .sec-count{{background:#dde4ec;color:var(--muted);border-radius:20px;
    padding:1px 9px;font-size:11px;letter-spacing:0}}
  section:first-of-type .sec-head{{margin-top:6px}}

  /* stock cards */
  .grid{{display:grid;gap:11px}}
  .stock,.card{{background:var(--card);border-radius:12px;border:1px solid var(--border);
    box-shadow:0 1px 3px rgba(16,33,46,.05);overflow:hidden}}
  .stock header{{display:flex;align-items:center;gap:10px;padding:13px 16px;
    border-bottom:1px solid var(--border);background:#f8fafc;flex-wrap:wrap}}
  .stock h3{{font-size:16px;font-weight:800;letter-spacing:-.2px}}
  .code{{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--accent2);
    background:#e6effa;border:1px solid #c9ddf2;border-radius:6px;padding:1px 7px}}
  .count{{font-size:12px;color:var(--muted);margin-left:auto}}
  .last{{font-size:11px;color:var(--faint);font-family:var(--mono)}}

  .reports{{list-style:none}}
  .reports li + li{{border-top:1px solid #eef2f7}}
  .reports a{{display:flex;align-items:center;gap:11px;padding:9px 16px;
    text-decoration:none;color:var(--text);transition:background .12s}}
  .reports a:hover{{background:#f3f8fd}}
  .reports a:focus-visible{{outline:2px solid var(--accent2);outline-offset:-2px}}
  .reports time{{font-family:var(--mono);font-size:12px;color:var(--muted);flex-shrink:0;min-width:80px}}
  .rtitle{{font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
  .nth{{font-size:10.5px;color:var(--faint);flex-shrink:0}}
  .badge-new{{font-size:10px;font-weight:800;letter-spacing:.5px;color:#0d9488;
    background:#ccfbf1;border:1px solid #99f6e4;border-radius:20px;padding:1px 7px;flex-shrink:0}}
  .est{{color:var(--faint);font-size:11px;cursor:help;flex-shrink:0;margin-left:-7px}}
  .mlabel{{font-size:11px;font-weight:700;color:var(--accent2);background:#e6effa;
    border-radius:5px;padding:1px 7px;flex-shrink:0;min-width:74px;text-align:center}}
  .reports.flat li:first-child a{{padding-top:12px}}
  .reports.flat li:last-child a{{padding-bottom:12px}}

  .empty{{display:none;text-align:center;color:var(--muted);padding:44px 20px;font-size:14px}}
  .empty.on{{display:block}}
  .hidden{{display:none !important}}

  footer{{max-width:940px;margin:0 auto;padding:0 24px 40px;font-size:11.5px;color:var(--faint);line-height:1.7}}
  footer code{{font-family:var(--mono);background:#e2e8f0;border-radius:4px;padding:1px 5px;color:var(--muted)}}

  @media(max-width:560px){{
    .mh-title{{font-size:23px}}
    .reports a{{flex-wrap:wrap;gap:6px 10px}}
    .rtitle{{white-space:normal;flex-basis:100%}}
    .count{{margin-left:0}}
  }}
</style>
</head>
<body>

<div class="masthead">
  <div class="mh-inner">
    <div class="mh-eyebrow">TW Stock Report</div>
    <h1 class="mh-title">台股研究報告索引</h1>
    <div class="mh-sub">多角色團隊深度分析 · 基本面 / 籌碼面 / 技術面 / 風控評分 / 三段式策略</div>
    <div class="mh-stats">
      <div class="stat"><div class="n">{total}</div><div class="l">報告總數</div></div>
      <div class="stat"><div class="n">{len(order)}</div><div class="l">個股檔數</div></div>
      <div class="stat"><div class="n">{len(market)}</div><div class="l">大盤報告</div></div>
      <div class="stat"><div class="n">{latest.isoformat()}</div><div class="l">最新更新</div></div>
    </div>
  </div>
</div>

<div class="toolbar">
  <div class="tb-inner">
    <input id="q" type="search" placeholder="搜尋公司名稱或代號，例如：智邦、2345、天虹…"
           autocomplete="off" aria-label="搜尋報告">
    <div class="tabs" role="tablist">
      <button class="tab" role="tab" data-filter="all" aria-selected="true">全部</button>
      <button class="tab" role="tab" data-filter="stock" aria-selected="false">個股</button>
      <button class="tab" role="tab" data-filter="market" aria-selected="false">大盤</button>
    </div>
  </div>
</div>

<div class="wrap">
  <section id="sec-stock" data-group="stock">
    <h2 class="sec-head">個股深度報告 <span class="sec-count">{len(order)} 檔</span></h2>
    <div class="grid">
{stock_html}
    </div>
  </section>

  <section id="sec-market" data-group="market">
    <h2 class="sec-head">大盤 / 盤勢報告 <span class="sec-count">{len(market)}</span></h2>
    <div class="card"><ul class="reports flat">{market_html}</ul></div>
  </section>
{other_block}
  <div class="empty" id="empty">找不到符合的報告，換個關鍵字試試。</div>
</div>

<footer>
  資料來源：富果 Fugle API（即時報價）· FinMind（K線 / 月營收 / 財報 / 融資融券）· 台灣證交所 T86（三大法人）· WebSearch（法人評等與產業資訊）<br>
  ⚠️ 所有報告僅供研究與資訊參考，<strong>不構成投資建議</strong>。投資有風險，請自行判斷並承擔盈虧。<br>
  標註 <span class="est">≈</span> 者檔名無日期，日期以檔案修改時間推估。索引由 <code>build_index.py</code> 自動產生 —
  新增報告後執行 <code>python build_index.py</code> 即可更新。
</footer>

<script>
(function(){{
  var q = document.getElementById('q');
  var empty = document.getElementById('empty');
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('section[data-group]'));
  var filter = 'all';

  function apply(){{
    var term = q.value.trim().toLowerCase();
    var anyVisible = false;

    sections.forEach(function(sec){{
      var group = sec.getAttribute('data-group');
      var groupAllowed = (filter === 'all') || (filter === group);
      if (!groupAllowed) {{ sec.classList.add('hidden'); return; }}

      var items = sec.querySelectorAll('[data-search]');
      var shown = 0;
      Array.prototype.forEach.call(items, function(el){{
        var hit = !term || el.getAttribute('data-search').indexOf(term) !== -1;
        el.classList.toggle('hidden', !hit);
        if (hit) shown++;
      }});
      sec.classList.toggle('hidden', shown === 0);
      if (shown > 0) anyVisible = true;
    }});

    empty.classList.toggle('on', !anyVisible);
  }}

  q.addEventListener('input', apply);
  tabs.forEach(function(t){{
    t.addEventListener('click', function(){{
      filter = t.getAttribute('data-filter');
      tabs.forEach(function(x){{ x.setAttribute('aria-selected', String(x === t)); }});
      apply();
    }});
  }});
  // "/" 快速聚焦搜尋
  document.addEventListener('keydown', function(e){{
    if (e.key === '/' && document.activeElement !== q) {{ e.preventDefault(); q.focus(); }}
    if (e.key === 'Escape' && document.activeElement === q) {{ q.value = ''; apply(); }}
  }});
  apply();
}})();
</script>
</body>
</html>
"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"索引已產生：{OUT}")
    print(f"  個股 {len(order)} 檔 / {sum(len(s['reports']) for _, s in order)} 份報告")
    print(f"  大盤 {len(market)} 份 ｜ 其他 {len(other)} 份 ｜ 合計 {total} 份")
    print(f"  最新報告日期：{latest.isoformat()}")
    print()
    for code, s in order:
        print(f"  {code}  {s['name']:<12} {len(s['reports']):>2} 份   最新 {s['reports'][0]['date']}")


if __name__ == "__main__":
    main()
