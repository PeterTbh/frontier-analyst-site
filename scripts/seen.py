#!/usr/bin/env python3
"""Keep the log of everything already reported (workspace state/seen.json).

  seen.py add  --workspace ../frontier-analyst --issue issues/2026-10-27-no1
  seen.py companies --workspace ../frontier-analyst      (list companies seen so far)
"""
import argparse
import json
import os


def load(ws):
    p = os.path.join(ws, "state", "seen.json")
    data = json.load(open(p)) if os.path.exists(p) else {}
    data.setdefault("items", [])
    data.setdefault("companies", [])
    return p, data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "companies"])
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--issue")
    a = ap.parse_args()
    ws = os.path.abspath(a.workspace)
    path, data = load(ws)

    if a.cmd == "companies":
        print("\n".join(sorted(data["companies"])))
        return

    issue = json.load(open(os.path.join(ws, a.issue, "issue.json")))
    known = {i["url"] for i in data["items"]}
    added = 0
    for s in issue.get("sections", []):
        for it in s.get("items", []):
            urls = [it["source"]["url"]] + [x["url"] for x in it.get("also") or []]
            for u in urls:
                if u not in known:
                    data["items"].append({"url": u, "title": it["title"], "date": it.get("date"),
                                          "issue": issue["number"], "section": s["id"]})
                    known.add(u)
                    added += 1
    comps = set(data["companies"])
    for c in issue.get("competitors", []):
        comps.add(c["company"])
    data["companies"] = sorted(comps)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"seen.json: +{added} urls, {len(data['items'])} total, {len(data['companies'])} companies")


if __name__ == "__main__":
    main()
