#!/usr/bin/env python3
"""Encrypt a built issue into the public site and update the encrypted archive index.

Only the public key in docs/site.json is used, so no password is needed here.

  publish.py --workspace ../frontier-analyst --site . --issue issues/2026-10-27-no1
  publish.py --workspace ../frontier-analyst --site . --reencrypt-all   (after a new keygen)

The plain-text archive index lives in the private workspace (issues/manifest.json).
The public site only ever receives encrypted envelopes with opaque file names.
"""
import argparse
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fa_crypto import encrypt_bytes, load_site  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def write_env(site, data: bytes, ctype: str, path: str) -> None:
    with open(path, "w") as f:
        json.dump(encrypt_bytes(site, data, ctype), f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="path to the private workspace repo")
    ap.add_argument("--site", required=True, help="path to the public site repo")
    ap.add_argument("--issue", help="issue folder inside the workspace, e.g. issues/2026-10-27-no1")
    ap.add_argument("--reencrypt-all", action="store_true")
    a = ap.parse_args()

    ws, site_root = os.path.abspath(a.workspace), os.path.abspath(a.site)
    docs = os.path.join(site_root, "docs")
    data_dir = os.path.join(docs, "data")
    os.makedirs(data_dir, exist_ok=True)
    site_path = os.path.join(docs, "site.json")
    site = load_site(site_path)

    # Display settings (only the motif switch is public)
    cfg_path = os.path.join(ws, "config.yaml")
    if yaml and os.path.exists(cfg_path):
        cfg = yaml.safe_load(open(cfg_path)) or {}
        motif = (cfg.get("issue") or {}).get("motif", "aletheia")
        if site.get("display", {}).get("motif") != motif:
            site.setdefault("display", {})["motif"] = motif
            json.dump(site, open(site_path, "w"), indent=1)

    man_path = os.path.join(ws, "issues", "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {"issues": []}

    todo = []
    if a.issue:
        idir = os.path.join(ws, a.issue)
        meta = json.load(open(os.path.join(idir, "issue.json")))
        entry = next((i for i in manifest["issues"] if i["folder"] == a.issue), None)
        if entry is None:
            entry = {"id": secrets.token_hex(8), "folder": a.issue}
            manifest["issues"].append(entry)
        entry.update({
            "number": meta["number"], "date": meta["date"], "title": meta["title"],
            "lead": meta.get("lead", ""),
            "html": f"data/{entry['id']}.enc",
            "pdf": f"data/{entry['id']}-pdf.enc" if os.path.exists(os.path.join(idir, "issue.pdf")) else None,
        })
        todo = [entry]
    if a.reencrypt_all:
        todo = manifest["issues"]

    for e in todo:
        idir = os.path.join(ws, e["folder"])
        write_env(site, open(os.path.join(idir, "issue.html"), "rb").read(), "text/html",
                  os.path.join(docs, e["html"]))
        if e.get("pdf"):
            write_env(site, open(os.path.join(idir, "issue.pdf"), "rb").read(), "application/pdf",
                      os.path.join(docs, e["pdf"]))
        print(f"encrypted issue No. {e['number']} -> {e['html']}")

    manifest["issues"].sort(key=lambda i: i["number"])
    json.dump(manifest, open(man_path, "w"), indent=1, ensure_ascii=False)
    public_manifest = {"issues": [{k: v for k, v in i.items() if k != "folder"} for i in manifest["issues"]]}
    write_env(site, json.dumps(public_manifest, ensure_ascii=False).encode(), "application/json",
              os.path.join(data_dir, "manifest.enc"))
    print(f"archive index: {len(manifest['issues'])} issue(s), encrypted")


if __name__ == "__main__":
    main()
