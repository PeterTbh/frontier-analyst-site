#!/usr/bin/env python3
"""Fail if anything private could end up in the public engine repo.

  leak_check.py --workspace ../frontier-analyst --site .

Checks every file that git would publish (tracked + untracked, minus .gitignore):
  * docs/ contains only the viewer, fonts, site.json and encrypted envelopes
  * every docs/data/*.enc is a well-formed encrypted envelope
  * site.json holds only the public key and the password-locked private key
  * no published file contains a distinctive line from the topic files or the people watchlist,
    a watched person's name, an issue title or headline, a confidential term from the workspace
    config, or a source URL from an issue
Exit code 0 = clean, 1 = leak found (do not push).
"""
import argparse
import json
import os
import re
import subprocess
import sys

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

ALLOWED_DOCS = re.compile(r"^docs/(index\.html|viewer\.js|viewer\.css|site\.json|robots\.txt|\.nojekyll|"
                          r"fonts/[\w.\-]+\.(woff2|txt)|data/[0-9a-f]{16}(-pdf)?\.enc|data/manifest\.enc)$")
ENVELOPE_KEYS = {"format", "type", "ek", "iv", "ct"}


def published_files(site):
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=site, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def needles(ws):
    """Distinctive strings that must never appear in public files."""
    found = set()
    cfg = {}
    if yaml and os.path.exists(os.path.join(ws, "config.yaml")):
        cfg = yaml.safe_load(open(os.path.join(ws, "config.yaml"))) or {}
    for t in cfg.get("confidential_terms") or []:
        found.add(str(t).lower())
    for tp in cfg.get("topics") or []:
        p = os.path.join(ws, tp)
        if not os.path.exists(p):
            continue
        for line in open(p):
            line = line.strip().strip("-*#|` ").strip()
            if len(line) >= 40:                      # long, distinctive lines only
                found.add(line.lower()[:80])
    people = (cfg.get("watch") or {}).get("people")
    if people and yaml and os.path.exists(os.path.join(ws, people)):
        pdata = yaml.safe_load(open(os.path.join(ws, people))) or {}
        for p in pdata.get("people") or []:
            if p.get("name") and len(p["name"]) >= 8:          # who the reader follows is private
                found.add(str(p["name"]).lower())
        for line in open(os.path.join(ws, people)):
            line = line.strip().strip("-*#|` ").strip()
            if len(line) >= 40:
                found.add(line.lower()[:80])
    idir = os.path.join(ws, "issues")
    for root, _, files in os.walk(idir):
        if "issue.json" in files:
            issue = json.load(open(os.path.join(root, "issue.json")))
            for k in ("title", "lead"):
                if issue.get(k) and len(issue[k]) >= 12:
                    found.add(issue[k].lower())
            for s in issue.get("sections", []):
                for it in s.get("items", []):
                    found.add(it["title"].lower())
                    found.add(it["source"]["url"].lower())
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--site", required=True)
    a = ap.parse_args()
    ws, site = os.path.abspath(a.workspace), os.path.abspath(a.site)
    problems = []

    files = published_files(site)
    for f in files:
        if f.startswith("docs/") and not ALLOWED_DOCS.match(f):
            problems.append(f"unexpected file in docs/: {f}")
        if f.startswith(("topics/", "issues/", "state/", "secrets/")) or f in ("people.yaml",) or f.endswith(("config.yaml",)) and not f.startswith("examples/"):
            problems.append(f"workspace file inside the public repo: {f}")

    for f in files:
        if f.startswith("docs/data/") and f.endswith(".enc"):
            env = json.load(open(os.path.join(site, f)))
            if set(env) != ENVELOPE_KEYS or env.get("format") != "fa-enc-1":
                problems.append(f"{f} is not a clean encrypted envelope")
    sj = json.load(open(os.path.join(site, "docs", "site.json")))
    if set(sj) - {"format", "kdf", "private_key", "public_key", "display"}:
        problems.append("site.json has unexpected keys")
    if set(sj.get("private_key", {})) != {"alg", "iv", "aad", "ct"}:
        problems.append("site.json private key is not in locked form")

    ns = needles(ws)
    for f in files:
        if f.endswith((".woff2", ".enc")) or f.startswith("docs/fonts/"):
            continue
        try:
            text = open(os.path.join(site, f), encoding="utf-8").read().lower()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for n in ns:
            if n and n in text:
                problems.append(f"{f} contains private text: '{n[:60]}'")

    for p in problems:
        print("LEAK:", p)
    print(f"leak check: {len(files)} public files scanned, {len(ns)} private strings, "
          f"{'CLEAN' if not problems else str(len(problems)) + ' problem(s)'}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
