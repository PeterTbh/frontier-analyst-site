#!/usr/bin/env python3
"""Render one issue (issue.json) into issue.html (web), issue.pdf (A4) and email.html.

  build_issue.py --workspace ../frontier-analyst --site . --issue issues/2026-10-27-no1

Writes the three files into the issue folder inside the (private) workspace.
Prints the PDF page count and exits with code 3 if it exceeds issue.max_pages.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile

import jinja2

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return dt.datetime.strptime(str(s), fmt)
        except ValueError:
            pass
    return None


def longdate(s):
    d = parse_date(s)
    return f"{d:%A} {d.day} {d:%B %Y}" if d else (s or "")


def shortdate(s):
    d = parse_date(s)
    if not d:
        return s or ""
    return f"{d:%b %Y}" if len(str(s)) == 7 else f"{d.day} {d:%b}"


def load_cfg(ws):
    cfg = {"title": "Frontier Analyst", "language": "en", "max_pages": 4, "motif": "aletheia"}
    p = os.path.join(ws, "config.yaml")
    if yaml and os.path.exists(p):
        raw = yaml.safe_load(open(p)) or {}
        cfg.update({k: v for k, v in (raw.get("issue") or {}).items() if v is not None})
        cfg["site_url"] = (raw.get("site") or {}).get("url")
    return cfg


def pdf_pages(path):
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(path).pages)
    except Exception:
        data = open(path, "rb").read()
        return len(re.findall(rb"/Type\s*/Page[^s]", data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--issue", required=True)
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()

    ws, site = os.path.abspath(a.workspace), os.path.abspath(a.site)
    idir = os.path.join(ws, a.issue)
    issue = json.load(open(os.path.join(idir, "issue.json")))
    cfg = load_cfg(ws)

    items = {it["id"]: it for s in issue.get("sections", []) for it in s.get("items", [])}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(site, "templates")),
                             autoescape=jinja2.select_autoescape(["html", "j2"]))
    env.filters["longdate"] = longdate
    env.filters["shortdate"] = shortdate
    css = open(os.path.join(site, "templates", "issue.css")).read()
    ctx = dict(i=issue, cfg=cfg, items=items, n_items=len(items), css=css, site_url=cfg.get("site_url"))

    html = env.get_template("issue.html.j2").render(**ctx)
    open(os.path.join(idir, "issue.html"), "w").write(html)
    email = env.get_template("email.html.j2").render(**ctx)
    open(os.path.join(idir, "email.html"), "w").write(email)
    print(f"issue.html {len(html)//1024} KB, email.html {len(email)//1024} KB")

    if a.no_pdf:
        return
    from playwright.sync_api import sync_playwright
    tmp = tempfile.mkdtemp()
    try:
        # Embed fonts as data URIs so Chromium renders the PDF with the real typefaces.
        import base64
        fonts_dir = os.path.join(site, "docs", "fonts")

        def inline_font(m):
            data = open(os.path.join(fonts_dir, m.group(1)), "rb").read()
            return "url(data:font/woff2;base64," + base64.b64encode(data).decode() + ")"

        pdf_html = re.sub(r"url\(fonts/([\w.\-]+\.woff2)\)", inline_font, html)
        page_html = os.path.join(tmp, "issue.html")
        open(page_html, "w").write(pdf_html)
        pdf_path = os.path.join(idir, "issue.pdf")
        footer = (
            '<div style="width:100%;font:7.5px Inter,Helvetica,sans-serif;letter-spacing:.08em;'
            'text-transform:uppercase;color:#6b6a66;padding:0 16mm;display:flex;justify-content:space-between">'
            f'<span>{cfg["title"]} · No. {issue["number"]}</span>'
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
        )
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto("file://" + page_html)
            pg.wait_for_load_state("networkidle")
            pg.evaluate("document.fonts.ready")
            pg.pdf(path=pdf_path, format="A4", print_background=True, prefer_css_page_size=True,
                   display_header_footer=True, header_template="<span></span>", footer_template=footer)
            b.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = pdf_pages(pdf_path)
    limit = int(cfg.get("max_pages", 4))
    print(f"issue.pdf {os.path.getsize(pdf_path)//1024} KB, {n} page(s), limit {limit}")
    if n > limit:
        sys.exit(3)


if __name__ == "__main__":
    main()
