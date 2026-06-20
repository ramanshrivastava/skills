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


# Catppuccin Mocha accents — one per row (mauve, blue, teal, peach, pink, sky,
# green, yellow, maroon, lavender, sapphire, red)
PALETTE = ["#cba6f7", "#89b4fa", "#94e2d5", "#fab387", "#f5c2e7", "#89dceb",
           "#a6e3a1", "#f9e2af", "#eba0ac", "#b4befe", "#74c7ec", "#f38ba8"]


def bar_rows(counter, top):
    items = counter.most_common(top)
    mx = max((n for _, n in items), default=1) or 1  # `or 1`: non-empty all-zero → no div-by-zero
    out = []
    for i, (label, n) in enumerate(items):
        pct = round(100 * n / mx, 1)
        c = PALETTE[i % len(PALETTE)]
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
    ap.add_argument("--anonymize", action="store_true",
                    help="replace project names with neutral codenames (project-NN by rank)")
    ap.add_argument("--alias-file",
                    help="JSON {substring: label} to relabel projects (overrides --anonymize per match); keep local, do not commit")
    ap.add_argument("--install-cmd", help="install command shown in a terminal-style bar")
    ap.add_argument("--repo", help="owner/repo tag shown in the footer")
    ap.add_argument("--exclude", help="comma-separated project substrings to drop from the dashboard")
    a = ap.parse_args()

    recs = load(Path(a.inp))
    if not recs:
        raise SystemExit(f"No records in {a.inp} — run distill.py first.")

    if a.exclude:
        subs = [s.strip() for s in a.exclude.split(",") if s.strip()]
        recs = [r for r in recs if not any(s in str(r.get("project", "")) for s in subs)]

    # --- project label mapping (real name -> displayed name) -----------------
    alias = {}
    if a.alias_file:
        alias = json.loads(Path(a.alias_file).read_text(encoding="utf-8"))
    # rank distinct projects by total prompts for stable codename assignment
    raw_totals = collections.Counter()
    for r in recs:
        raw_totals[r.get("project", "?")] += r.get("n_prompts", 0)
    ranked = [p for p, _ in raw_totals.most_common()]
    codename = {p: f"project-{i+1:02d}" for i, p in enumerate(ranked)}

    def proj_label(project: str) -> str:
        project = str(project)
        for sub, lbl in alias.items():          # substring match wins (descriptive names)
            if sub in project:
                return lbl
        if a.anonymize:
            return codename.get(project, "project-??")
        return short_proj(project)

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
        proj_prompts[proj_label(r.get("project", "?"))] += r.get("n_prompts", 0)
        end = r.get("ended") or r.get("started")
        if end:
            months[str(end)[:7]] += 1
    projects = len({r.get("project") for r in recs})


    # source split chips
    src_chips = " ".join(
        f'<span class="chip"><b>{html.escape(s)}</b> {by_source[s]:,} sess · {src_prompts[s]:,} prompts</span>'
        for s in sorted(by_source))

    # monthly activity (sessions per month, chronological)
    mrows = []
    if months:
        mmax = max(months.values())
        for i, m in enumerate(sorted(months)):
            pct = round(100 * months[m] / mmax, 1)
            c = PALETTE[i % len(PALETTE)]
            mrows.append(
                f'<div class="row"><span class="lbl">{html.escape(m)}</span>'
                f'<span class="track"><span class="fill" style="width:{pct}%;background:{c}"></span></span>'
                f'<span class="num">{months[m]:,}</span></div>')
    mhtml = "\n".join(mrows) or '<div class="empty">no dates</div>'

    # optional install bar (terminal-style, one line per command) + repo footer tag
    if a.install_cmd:
        ilines = "".join(
            f'<div class="iline"><span class="prompt">$</span> <span class="cmd">{html.escape(l)}</span></div>'
            for l in a.install_cmd.split("\n") if l.strip())
        install_html = f'<div class="install">{ilines}</div>'
    else:
        install_html = ""
    repo_html = (f' · <span class="repo">github.com/{html.escape(a.repo)}</span>'
                 if a.repo else "")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAMAN SKILLS — Agent Log Dashboard</title>
<style>
:root{{--bg:#181825;--card:#1e1e2e;--line:#2a2b3c;--fg:#cdd6f4;--mut:#9399b2;--track:#11111b;--accent:#cba6f7}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:940px;margin:0 auto;padding:64px 48px 72px}}
.logo{{font-size:30px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;margin:0;background:linear-gradient(90deg,#cba6f7,#b4befe);-webkit-background-clip:text;background-clip:text;color:transparent}}
.sub{{color:var(--mut);margin:10px 0 0;font-size:14px}}
.install{{margin:28px 0 48px;padding:16px 18px;background:var(--card);border-radius:12px;font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13.5px}}
.install .iline{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.9}}
.install .prompt{{color:#a6e3a1;margin-right:10px;user-select:none}}
.install .cmd{{color:var(--fg)}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:40px;padding-bottom:44px;border-bottom:1px solid var(--line);margin-bottom:48px}}
.kpi .v{{font-size:42px;font-weight:600;letter-spacing:-.03em;line-height:1}}
.kpi .k{{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.12em;margin-top:10px}}
.chips{{display:flex;gap:24px;margin:0 0 48px;color:var(--mut);font-size:13px}}
.chip b{{color:var(--fg);font-weight:600}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:56px;margin-bottom:48px}}
.panel h2{{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:var(--mut);margin:0 0 22px;font-weight:600}}
.tag{{text-transform:none;letter-spacing:0;color:#6c7086;font-weight:400;font-style:italic;margin-left:6px}}
.row{{display:grid;grid-template-columns:148px 1fr 52px;align-items:center;gap:14px;margin:12px 0}}
.lbl{{color:var(--fg);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px}}
.track{{background:var(--track);border-radius:999px;height:8px;overflow:hidden}}
.fill{{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#cba6f7,#b4befe)}}
.num{{text-align:right;color:var(--mut);font-size:13px;font-variant-numeric:tabular-nums}}
.empty{{color:var(--mut)}}
.full{{grid-column:1 / -1}}
.foot{{color:#6c7086;margin-top:8px;font-size:12px;letter-spacing:.02em}}
.repo{{color:#7f849c}}
@media(max-width:760px){{.wrap{{padding:40px 22px}}.kpis{{grid-template-columns:repeat(2,1fr);gap:28px}}.grid{{grid-template-columns:1fr;gap:40px}}.row{{grid-template-columns:120px 1fr 48px}}}}
</style></head>
<body><div class="wrap">
<h1 class="logo">RAMAN&nbsp;SKILLS</h1>
<p class="sub">Agent log miner · Claude Code + OpenAI Codex · aggregates only</p>
{install_html}
<div class="kpis">
  <div class="kpi"><div class="v">{sessions:,}</div><div class="k">Sessions</div></div>
  <div class="kpi"><div class="v">{projects:,}</div><div class="k">Projects</div></div>
  <div class="kpi"><div class="v">{prompts:,}</div><div class="k">User prompts</div></div>
  <div class="kpi"><div class="v">{sum(tools.values()):,}</div><div class="k">Tool calls</div></div>
</div>
<div class="chips">{src_chips}</div>
<div class="grid">
  <div class="panel"><h2>Top tools</h2>{bar_rows(tools, a.top)}</div>
  <div class="panel"><h2>Busiest projects (by prompts) <span class="tag">names are examples</span></h2>{bar_rows(proj_prompts, a.top)}</div>
  <div class="panel full"><h2>Activity by month (sessions)</h2>{mhtml}</div>
</div>
<p class="foot">Generated by mine-logs-for-skills · project names are illustrative examples · no raw prompt text.{repo_html}</p>
</div></body></html>"""

    out = Path(a.out)
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out}  ({len(doc):,} bytes)  sessions={sessions} projects={projects} prompts={prompts}")


if __name__ == "__main__":
    main()
