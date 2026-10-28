#!/usr/bin/env python3
"""Check an issue.json against the schema, the writing rules and the confidentiality rules.

  validate_issue.py --workspace ../frontier-analyst --issue issues/2026-10-27-no1

Exit code 0 = OK (warnings may be printed), 1 = errors that must be fixed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

KINDS_HINT = {"Funding", "Launch", "Paper", "Preprint", "Policy", "Partnership", "Model release",
              "Hire", "Benchmark", "Field report", "Essay", "Interview", "Deal", "Data release", "Event"}
SOURCE_TYPES = {"Primary", "Press", "Preprint", "Analysis", "Rumour"}
CRED = {"High", "Medium", "Low"}
HYPE = ["revolutionary", "groundbreaking", "game-changing", "game changer", "unprecedented",
        "paradigm shift", "transformative", "cutting-edge", "delve", "landscape", "unlock",
        "supercharge", "in today's", "this week in"]
# "US" (United States) is fine; lower-case "us" and any "we/our" are not.
FIRST_PERSON = re.compile(r"\b([Ww]e|WE|[Oo]urs?|OURS?|us)\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def is_date(s):
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            dt.datetime.strptime(str(s), fmt)
            return True
        except ValueError:
            pass
    return False


def words(s):
    return len(str(s or "").split())


def texts(issue):
    """Yield (where, text) for every human-readable string in the issue."""
    for k in ("title", "lead", "note"):
        if issue.get(k):
            yield k, issue[k]
    for n, o in enumerate(issue.get("overview", [])):
        yield f"overview[{n}]", o.get("text", "")
    for s in issue.get("sections", []):
        for it in s.get("items", []):
            for k in ("title", "summary", "why", "credibility_note"):
                yield f"{it.get('id')}.{k}", it.get(k, "")
    for c in issue.get("competitors", []):
        yield f"competitor {c.get('company')}", c.get("move", "")
    for q in issue.get("questions", []):
        yield "question", q.get("update", "")
    for c in issue.get("coming_up", []):
        yield "coming_up", c.get("what", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--issue", required=True)
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace)
    issue = json.load(open(os.path.join(ws, a.issue, "issue.json")))
    cfg = (yaml.safe_load(open(os.path.join(ws, "config.yaml"))) if yaml and
           os.path.exists(os.path.join(ws, "config.yaml")) else {}) or {}

    # Top level
    if not isinstance(issue.get("number"), int):
        err("number must be an integer")
    for k in ("date", "title"):
        if not issue.get(k):
            err(f"missing {k}")
    if issue.get("date") and not is_date(issue["date"]):
        err("date must be YYYY-MM-DD")
    per = issue.get("period") or {}
    if not (is_date(per.get("from")) and is_date(per.get("to"))):
        err("period.from / period.to must be dates")
    if words(issue.get("title")) > 14:
        warn("issue title is long (>14 words)")

    ids = {}
    for s in issue.get("sections", []):
        if not s.get("id") or not s.get("label"):
            err("each section needs id and label")
        for it in s.get("items", []):
            iid = it.get("id")
            if not iid or iid in ids:
                err(f"item id missing or duplicated: {iid}")
            ids[iid] = it
            for k in ("kind", "title", "summary", "why", "date", "credibility", "credibility_note"):
                if not it.get(k):
                    err(f"{iid}: missing {k}")
            if it.get("kind") and it["kind"] not in KINDS_HINT:
                warn(f"{iid}: unusual kind '{it['kind']}'")
            if it.get("date") and not is_date(it["date"]):
                err(f"{iid}: date must be YYYY-MM-DD or YYYY-MM")
            src = it.get("source") or {}
            if not str(src.get("url", "")).startswith("https://"):
                err(f"{iid}: source.url must be an https URL")
            if src.get("type") not in SOURCE_TYPES:
                err(f"{iid}: source.type must be one of {sorted(SOURCE_TYPES)}")
            if not src.get("name"):
                err(f"{iid}: source.name missing")
            for al in it.get("also") or []:
                if not str(al.get("url", "")).startswith("https://"):
                    err(f"{iid}: also[].url must be https")
            if it.get("credibility") not in CRED:
                err(f"{iid}: credibility must be High, Medium or Low")
            if not isinstance(it.get("impact"), int) or not 1 <= it["impact"] <= 5:
                err(f"{iid}: impact must be an integer 1-5")
            if it.get("credibility") == "Low" and isinstance(it.get("impact"), int) and it["impact"] < 4:
                warn(f"{iid}: Low credibility with impact < 4: consider dropping")
            if words(it.get("summary")) > 70:
                err(f"{iid}: summary has {words(it.get('summary'))} words (max ~60)")
            if words(it.get("why")) > 40:
                err(f"{iid}: why has {words(it.get('why'))} words (max ~35)")

    ov = issue.get("overview", [])
    if not 3 <= len(ov) <= 5 and len(ids) >= 3:
        warn(f"overview has {len(ov)} lines (aim for 3-5)")
    for o in ov:
        if o.get("item") not in ids:
            err(f"overview line points to unknown item {o.get('item')}")

    for c in issue.get("competitors", []):
        if not c.get("company") or not c.get("move"):
            err("competitor rows need company and move")
        if not isinstance(c.get("impact"), int) or not 1 <= c["impact"] <= 5:
            err(f"competitor {c.get('company')}: impact must be 1-5")
        if c.get("url") and not str(c["url"]).startswith("https://"):
            err(f"competitor {c.get('company')}: url must be https")
    for c in issue.get("coming_up", []):
        if not is_date(c.get("date")):
            err(f"coming_up '{c.get('what')}': date must be YYYY-MM-DD")

    # Writing rules and confidentiality
    conf = [t.lower() for t in (cfg.get("confidential_terms") or [])]
    total = 0
    for where, t in texts(issue):
        total += words(t)
        low = str(t).lower()
        for h in HYPE:
            if h in low:
                err(f"{where}: avoid '{h}'")
        if "!" in str(t):
            err(f"{where}: no exclamation marks")
        if EMOJI.search(str(t)):
            err(f"{where}: no emojis")
        if FIRST_PERSON.search(str(t)):
            err(f"{where}: no first person plural (we/our/us)")
        for term in conf:
            if term and term in low:
                err(f"{where}: contains confidential term '{term}'")
    if total > 2600:
        warn(f"issue text is {total} words; the PDF may exceed the page limit")

    # Already reported?
    seen_p = os.path.join(ws, "state", "seen.json")
    if os.path.exists(seen_p):
        seen_urls = {i.get("url") for i in json.load(open(seen_p)).get("items", [])}
        for iid, it in ids.items():
            if (it.get("source") or {}).get("url") in seen_urls:
                err(f"{iid}: already reported in an earlier issue")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(ids)} items, {total} words, {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
