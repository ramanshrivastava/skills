#!/usr/bin/env python3
"""Scan AI assistant transcripts (Claude Code + Codex) for plaintext secrets.

Read-only. Prints file:line + a REDACTED preview (prefix + length) + the matched
secret type, so you can rotate/scrub without the script re-exposing full values.

Caveat: the 40-char-hex patterns (wandb/Deepgram) also match git SHAs and
sha256 hashes — treat those as low-confidence; the prefixed token formats
(npm_, pypi-, sk_, cfut_, whsec_, AKIA, AIza) are high-confidence.

Usage:
  python3 scan_secrets.py [--source claude|codex|both] [--projects-dir DIR] [--codex-dir DIR]
"""
import argparse, re
from pathlib import Path

# (label, compiled pattern). Patterns target known token shapes — high precision,
# low recall is fine: better to flag obvious live keys than drown in false positives.
PATTERNS = [
    ("npm token",            re.compile(r"npm_[A-Za-z0-9]{36}")),
    ("PyPI token",           re.compile(r"pypi-[A-Za-z0-9_-]{50,}")),
    ("OpenAI/sk key",        re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("ElevenLabs key",       re.compile(r"sk_[a-f0-9]{40,}")),
    ("Deepgram key",         re.compile(r"\b[a-f0-9]{40}\b")),
    ("wandb key",            re.compile(r"wandb_[A-Za-z0-9_-]{40,}|\b[a-f0-9]{40}\b")),
    ("Cloudflare API token", re.compile(r"cf[a-z]*_[A-Za-z0-9_-]{30,}|cfut_[A-Za-z0-9]{30,}")),
    ("Svix webhook secret",  re.compile(r"whsec_[A-Za-z0-9+/=]{20,}")),
    ("AWS access key",       re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Google API key",       re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("Slack token",          re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Generic bearer",       re.compile(r"(?i)(?:authorization|bearer)\s*[:=]\s*[A-Za-z0-9._-]{24,}")),
    ("Private key block",    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
]


def redact(s: str) -> str:
    s = s.strip()
    if len(s) <= 10:
        return s[:3] + "…"
    return f"{s[:6]}…{s[-2:]} (len {len(s)})"


def main():
    home = Path.home()
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["claude", "codex", "both"], default="both")
    ap.add_argument("--projects-dir", default=str(home / ".claude" / "projects"))
    ap.add_argument("--codex-dir", default=str(home / ".codex" / "sessions"))
    a = ap.parse_args()

    # Both transcript stores are fixed home-relative paths — scan whichever exist,
    # independent of which assistant is running this scan. Missing dirs are skipped.
    roots = []
    if a.source in ("claude", "both"):
        roots.append(Path(a.projects_dir))
    if a.source in ("codex", "both"):
        roots.append(Path(a.codex_dir))
    jsonl_files = [jf for root in roots if root.exists() for jf in root.rglob("*.jsonl")]

    findings = []  # (file, lineno, label, redacted)
    seen = set()   # dedup identical (file,label,redacted)
    for jf in jsonl_files:
        try:
            with jf.open(encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, 1):
                    for label, pat in PATTERNS:
                        for m in pat.findall(line):
                            val = m if isinstance(m, str) else m[0]
                            red = redact(val)
                            key = (str(jf), label, red)
                            if key in seen:
                                continue
                            seen.add(key)
                            findings.append((str(jf), i, label, red))
        except OSError:
            continue

    if not findings:
        print("No plaintext secrets matched.")
        return

    by_type = {}
    for _, _, label, _ in findings:
        by_type[label] = by_type.get(label, 0) + 1

    print(f"=== {len(findings)} secret-like matches across transcripts ===\n")
    print("By type:")
    for label, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {label}: {n}")
    print("\nLocations (value redacted):")
    for f, ln, label, red in sorted(findings):
        short = f.replace(str(home), "~")
        print(f"  {short}:{ln}  [{label}]  {red}")


if __name__ == "__main__":
    main()
