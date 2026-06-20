#!/usr/bin/env python3
"""Distill AI coding-assistant transcripts into a compact, agent-readable corpus.

Supports BOTH Claude Code and OpenAI Codex CLI transcripts. The raw logs are far
too large to load into a model context (hundreds of MB); this does the cheap,
deterministic part — stream every session, keep genuine *user intents* and the
*tool calls* used to satisfy them, aggregate per-project + globally — so an agent
can read the result and reason over it semantically.

It does NOT cluster or judge — that's the agent's job. This produces high-signal,
low-volume input, tagged by source so cross-tool patterns surface (cwd is the
join key: the same repo worked in either assistant groups together).

Transcript locations:
  Claude Code : ~/.claude/projects/<dashed-cwd>/<uuid>.jsonl   (message-stream)
  Codex CLI   : ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl    (event-stream)

Outputs (default ~/.cache/mine-logs-for-skills/):
  distilled.jsonl  one JSON record per session (complete, machine-readable)
  corpus.md        size-bounded digest: per-source counts, global tool-frequency,
                   and prompts grouped by project

Usage:
  python3 distill.py [--source claude|codex|both] [--claude-dir DIR] [--codex-dir DIR]
                     [--out DIR] [--max-prompt-chars N] [--min-prompt-chars N]
                     [--since YYYY-MM-DD]
"""
import argparse, json, collections
from pathlib import Path

# User text starting with these is harness/system noise, not a genuine intent.
NOISE_PREFIXES = ("<", "Caveat:", "[Request interrupted", "This session is being continued")


# ----------------------------- Claude Code -----------------------------------
def _claude_is_user_prompt(d: dict) -> bool:
    if d.get("type") != "user" or d.get("isSidechain"):
        return False
    m = d.get("message", {})
    if not isinstance(m, dict) or m.get("role") != "user":
        return False
    c = m.get("content")
    return isinstance(c, str) and bool(c.strip())  # list content == tool_result


def distill_claude_file(jf: Path, max_chars: int, min_chars: int):
    cwd = branch = version = title = None
    ts_first = ts_last = None
    prompts, tool_seq = [], []
    tool_counts = collections.Counter()
    sidechain_tools = collections.Counter()

    with jf.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            cwd = cwd or d.get("cwd")
            branch = branch or d.get("gitBranch")
            version = version or d.get("version")
            title = title or d.get("aiTitle")
            ts = d.get("timestamp")
            if ts:
                # ISO-8601/Z strings sort chronologically; use min/max so a
                # resumed or out-of-order log can't yield ended < started.
                ts_first = ts if ts_first is None else min(ts_first, ts)
                ts_last = ts if ts_last is None else max(ts_last, ts)
            if _claude_is_user_prompt(d):
                s = d["message"]["content"].strip()
                if len(s) >= min_chars and not s.startswith(NOISE_PREFIXES):
                    prompts.append(s[:max_chars])
            if d.get("type") == "assistant":
                m = d.get("message", {})
                for b in (m.get("content") or []) if isinstance(m, dict) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        name = b.get("name", "?")
                        if d.get("isSidechain"):
                            sidechain_tools[name] += 1
                        else:
                            tool_counts[name] += 1
                            if len(tool_seq) < 60:
                                tool_seq.append(name)

    if not prompts and not tool_counts:
        return None
    return _record("claude", jf, cwd or jf.parent.name, branch, version, title,
                   ts_first, ts_last, prompts, tool_counts, tool_seq, sidechain_tools)


# -------------------------------- Codex --------------------------------------
def distill_codex_file(jf: Path, max_chars: int, min_chars: int):
    cwd = branch = version = title = None
    ts_first = ts_last = None
    prompts, tool_seq = [], []
    tool_counts = collections.Counter()

    with jf.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
            ts = d.get("timestamp")
            if ts:
                # ISO-8601/Z strings sort chronologically; use min/max so a
                # resumed or out-of-order log can't yield ended < started.
                ts_first = ts if ts_first is None else min(ts_first, ts)
                ts_last = ts if ts_last is None else max(ts_last, ts)

            if t == "session_meta":
                cwd = cwd or p.get("cwd")
                version = version or p.get("cli_version")
                git = p.get("git")
                if isinstance(git, dict):
                    branch = branch or git.get("branch")
            elif t == "event_msg" and p.get("type") == "user_message":
                msg = p.get("message")  # may be non-str in some Codex versions
                s = msg.strip() if isinstance(msg, str) else ""
                if len(s) >= min_chars and not s.startswith(NOISE_PREFIXES):
                    prompts.append(s[:max_chars])
            # Tool calls appear EITHER as top-level type=function_call OR as a
            # response_item whose payload.type=function_call (version-dependent).
            elif t == "function_call" or (t == "response_item" and p.get("type") == "function_call"):
                name = p.get("name", "?")
                tool_counts[name] += 1
                if len(tool_seq) < 60:
                    tool_seq.append(name)

    if not prompts and not tool_counts:
        return None
    # Codex parent dir is a day bucket (e.g. "20") — useless as a project key and
    # collides across dates; fall back to a unique per-file sentinel instead.
    return _record("codex", jf, cwd or f"unknown:{jf.stem}", branch, version, title,
                   ts_first, ts_last, prompts, tool_counts, tool_seq, collections.Counter())


# ------------------------------- shared --------------------------------------
def _record(source, jf, project, branch, version, title, ts_first, ts_last,
            prompts, tool_counts, tool_seq, sidechain_tools):
    return {
        "source": source,
        "file": str(jf),
        "project": project,
        "branch": branch,
        "version": version,
        "title": title,
        "started": ts_first,
        "ended": ts_last,
        "n_prompts": len(prompts),
        "prompts": prompts,
        "tool_counts": dict(tool_counts.most_common()),
        "tool_sequence": tool_seq,
        "subagent_tool_counts": dict(sidechain_tools.most_common()),
    }


def main():
    home = Path.home()
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["claude", "codex", "both"], default="both")
    ap.add_argument("--claude-dir", default=str(home / ".claude" / "projects"))
    ap.add_argument("--codex-dir", default=str(home / ".codex" / "sessions"))
    ap.add_argument("--out", default=str(home / ".cache" / "mine-logs-for-skills"))
    ap.add_argument("--max-prompt-chars", type=int, default=400)
    ap.add_argument("--min-prompt-chars", type=int, default=12)
    ap.add_argument("--since", help="ISO date YYYY-MM-DD; skip sessions ending before this")
    a = ap.parse_args()

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Both stores are fixed home-relative paths — read whichever exist, regardless
    # of which assistant is running this. A missing store is skipped, not an error.
    records = []
    claude_dir, codex_dir = Path(a.claude_dir), Path(a.codex_dir)
    if a.source in ("claude", "both") and claude_dir.exists():
        for jf in claude_dir.rglob("*.jsonl"):
            r = distill_claude_file(jf, a.max_prompt_chars, a.min_prompt_chars)
            if r:
                records.append(r)
    if a.source in ("codex", "both") and codex_dir.exists():
        for jf in codex_dir.rglob("rollout-*.jsonl"):
            r = distill_codex_file(jf, a.max_prompt_chars, a.min_prompt_chars)
            if r:
                records.append(r)

    if a.since:
        # Keep only sessions with a known end date at/after the cutoff; undated
        # sessions can't be confirmed recent, so they're excluded when --since is set.
        records = [r for r in records if r.get("ended") and r["ended"][:10] >= a.since]

    with (out_dir / "distilled.jsonl").open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # --- aggregate ---
    by_project = collections.defaultdict(list)
    for r in records:
        by_project[r["project"]].append(r)
    global_tools = collections.Counter()
    for r in records:
        global_tools.update(r["tool_counts"])
    src_counts = collections.Counter(r["source"] for r in records)
    src_prompts = collections.Counter()
    for r in records:
        src_prompts[r["source"]] += r["n_prompts"]
    total_prompts = sum(r["n_prompts"] for r in records)

    lines = ["# AI assistant log corpus (distilled)\n"]
    lines.append(f"- sessions: **{len(records)}**  ")
    lines.append(f"- projects: **{len(by_project)}**  ")
    lines.append(f"- user prompts: **{total_prompts}**  ")
    lines.append(f"- by source: " + ", ".join(
        f"**{s}** {src_counts[s]} sessions / {src_prompts[s]} prompts" for s in sorted(src_counts)) + "\n")
    lines.append("## Global tool frequency\n")
    for name, n in global_tools.most_common(40):
        lines.append(f"- `{name}`: {n}")
    lines.append("")
    lines.append("## Prompts grouped by project\n")
    lines.append("_Read these semantically to find recurring intents, friction, and skill "
                 "candidates. Patterns recurring across MANY projects → global skills; confined "
                 "to one → project-scoped. The `[source]` tag shows which assistant produced each "
                 "session._\n")
    for proj, recs in sorted(by_project.items(), key=lambda kv: -sum(x["n_prompts"] for x in kv[1])):
        np = sum(x["n_prompts"] for x in recs)
        if np == 0:
            continue
        srcs = "/".join(sorted({x["source"] for x in recs}))
        lines.append(f"### {proj}  ({len(recs)} sessions, {np} prompts) [{srcs}]\n")
        for r in recs:
            for p in r["prompts"]:
                lines.append(f"- {' '.join(p.split())}")
        lines.append("")

    (out_dir / "corpus.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"source={a.source} sessions={len(records)} projects={len(by_project)} prompts={total_prompts}")
    print("by source: " + dict(src_counts).__repr__())
    print(f"wrote {out_dir/'distilled.jsonl'}")
    print(f"wrote {out_dir/'corpus.md'}")


if __name__ == "__main__":
    main()
