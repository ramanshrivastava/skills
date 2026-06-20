#!/usr/bin/env python3
"""Render a self-contained HTML dashboard from the distilled corpus.

Reads distilled.jsonl (produced by distill.py) and writes a single dark-themed
dashboard.html with NO external dependencies (inline CSS, CSS bar charts) so it
works offline. Shows AGGREGATES ONLY — counts, tools, projects, timeline — never
raw prompt text, so the file is safe to share.

Usage:
  python3 dashboard.py [--in PATH] [--out PATH] [--top N]
"""
import argparse, json, collections, html
from pathlib import Path


def load(path: Path):
    recs = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return recs


def bar_rows(counter, top, palette):
    items = counter.most_common(top)
    mx = max((n for _, n in items), default=1) or 1  # `or 1`: non-empty all-zero → no div-by-zero
    out = []
    for i, (label, n) in enumerate(items):
        pct = round(100 * n / mx, 1)
        c = palette[i % len(palette)]
        out.append(
            f'<div class="row"><span class="lbl" title="{html.escape(str(label))}">{html.escape(str(label))}</span>'
            f'<span class="track"><span class="fill" style="width:{pct}%;background:{c}"></span></span>'
            f'<span class="num">{n:,}</span></div>'
        )
    return "\n".join(out) or '<div class="empty">no data</div>'


def short_proj(p: str) -> str:
    parts = [x for x in str(p).split("/") if x]
    return "/".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else str(p))


def main():
    home = Path.home()
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(home / ".cache" / "mine-logs-for-skills" / "distilled.jsonl"))
    ap.add_argument("--out", default=str(home / ".cache" / "mine-logs-for-skills" / "dashboard.html"))
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()

    recs = load(Path(a.inp))
    if not recs:
        raise SystemExit(f"No records in {a.inp} — run distill.py first.")

    sessions = len(recs)
    prompts = sum(r.get("n_prompts", 0) for r in recs)
    by_source = collections.Counter(r.get("source", "?") for r in recs)
    src_prompts = collections.Counter()
    tools = collections.Counter()
    proj_prompts = collections.Counter()
    months = collections.Counter()
    for r in recs:
        src_prompts[r.get("source", "?")] += r.get("n_prompts", 0)
        tools.update(r.get("tool_counts", {}))
        proj_prompts[short_proj(r.get("project", "?"))] += r.get("n_prompts", 0)
        end = r.get("ended") or r.get("started")
        if end:
            months[str(end)[:7]] += 1
    projects = len({r.get("project") for r in recs})

    palette = ["#7c9cff", "#5ed6c0", "#f7b955", "#ff7b9c", "#b78bff", "#6fd0ff",
               "#9ae66e", "#ffd166", "#ef8e8e", "#8ec7ff"]

    # source split chips
    src_chips = " ".join(
        f'<span class="chip"><b>{html.escape(s)}</b> {by_source[s]:,} sess · {src_prompts[s]:,} prompts</span>'
        for s in sorted(by_source))

    # monthly activity (sessions per month, chronological)
    mrows = []
    if months:
        mmax = max(months.values())
        for m in sorted(months):
            pct = round(100 * months[m] / mmax, 1)
            mrows.append(
                f'<div class="row"><span class="lbl">{html.escape(m)}</span>'
                f'<span class="track"><span class="fill" style="width:{pct}%;background:#7c9cff"></span></span>'
                f'<span class="num">{months[m]:,}</span></div>')
    mhtml = "\n".join(mrows) or '<div class="empty">no dates</div>'

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Log Miner — Dashboard</title>
<style>
:root{{--bg:#0d0f14;--card:#161a23;--line:#242a36;--fg:#e6e9ef;--mut:#8b93a7}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:32px 20px 64px}}
h1{{font-size:22px;margin:0 0 4px;letter-spacing:-.02em}}
.sub{{color:var(--mut);margin:0 0 24px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:14px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}}
.kpi .v{{font-size:30px;font-weight:700;letter-spacing:-.03em}}
.kpi .k{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-top:2px}}
.chips{{margin:6px 0 26px;display:flex;gap:10px;flex-wrap:wrap}}
.chip{{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 12px;color:var(--mut)}}
.chip b{{color:var(--fg)}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}}
.panel h2{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:0 0 14px}}
.row{{display:grid;grid-template-columns:160px 1fr 56px;align-items:center;gap:10px;margin:7px 0}}
.lbl{{color:var(--fg);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px}}
.track{{background:#0d0f14;border-radius:6px;height:14px;overflow:hidden}}
.fill{{display:block;height:100%;border-radius:6px}}
.num{{text-align:right;color:var(--mut);font-variant-numeric:tabular-nums}}
.empty{{color:var(--mut)}}
.full{{grid-column:1 / -1}}
.foot{{color:var(--mut);margin-top:24px;font-size:12px}}
@media(max-width:760px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}.row{{grid-template-columns:120px 1fr 48px}}}}
</style></head>
<body><div class="wrap">
<h1>Agent Log Miner</h1>
<p class="sub">Distilled from your Claude Code + OpenAI Codex transcripts · aggregates only</p>
<div class="kpis">
  <div class="kpi"><div class="v">{sessions:,}</div><div class="k">Sessions</div></div>
  <div class="kpi"><div class="v">{projects:,}</div><div class="k">Projects</div></div>
  <div class="kpi"><div class="v">{prompts:,}</div><div class="k">User prompts</div></div>
  <div class="kpi"><div class="v">{sum(tools.values()):,}</div><div class="k">Tool calls</div></div>
</div>
<div class="chips">{src_chips}</div>
<div class="grid">
  <div class="panel"><h2>Top tools</h2>{bar_rows(tools, a.top, palette)}</div>
  <div class="panel"><h2>Busiest projects (by prompts)</h2>{bar_rows(proj_prompts, a.top, palette)}</div>
  <div class="panel full"><h2>Activity by month (sessions)</h2>{mhtml}</div>
</div>
<p class="foot">Generated by mine-logs-for-skills · no raw prompt text included.</p>
</div></body></html>"""

    out = Path(a.out)
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out}  ({len(doc):,} bytes)  sessions={sessions} projects={projects} prompts={prompts}")


if __name__ == "__main__":
    main()
