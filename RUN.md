# Producing an issue

The procedure a run follows, start to finish. Standards for judging and writing are in
`ANALYST.md`; read it before step 3. Two repositories are involved:

- **Engine** (this public repo): scripts, templates, the encrypted website in `docs/`.
- **Workspace** (a private repo): `config.yaml`, `topics/`, `state/`, `issues/`. Its contents are
  never published and never quoted.

Paths below use `$E` for the engine checkout and `$W` for the workspace checkout.

## 0. Set up

1. **Cloud session:** attach both repositories with push access (`add_repo`, access `push`) and
   clone each once with `git clone --depth 1` into `/home/claude/<repo-name>`. Before pushing
   later, `git fetch origin main` and rebase if needed. **Local Claude Code:** check both out side
   by side.
2. `pip install --break-system-packages -q jinja2 pyyaml cryptography pypdf` if any import fails.
   Chromium and Playwright must be available for the PDF.
3. Read `$W/config.yaml`, every file listed under `topics:`, `$W/state/seen.json`,
   `$W/state/sources.json` and `$W/issues/manifest.json` (may not exist yet).
4. Issue number = last number + 1 (or 1). Window: from the last issue's date (or
   `first_issue_lookback_days` ago) to today. Issue folder: `issues/<today>-no<N>` in `$W`.
   **Guard:** if the last issue is dated today or yesterday, stop here and report
   "Skipped: last issue is less than two days old". Do not publish or email anything.
5. Make a task list with steps 1–9 so progress is visible.

## 1. Newsletters

If a Gmail tool is available and `delivery.newsletter_address` is set:
- Search `deliveredto:<newsletter_address> after:<from>`.
- Read each newsletter. Note candidate items, and prefer the primary source it links to over the
  newsletter's own wording.
- Move each newsletter out of the inbox into `delivery.newsletter_label`: create the label if it
  is missing, add it, and remove `INBOX`.

## 2. Scan

Per topic file, in `order`. Budget for the whole run: about 50 web searches and 50 page fetches,
split by `weight` (high ≈ half, the rest shared). Stop early when the topics are covered.

For each topic, in this order:
1. **Known primary sources** in `$W/state/sources.json` (company blogs, preprint listings, regulator
   pages, newsletter archives): fetch and look for entries dated inside the window.
2. **Companies and people** named in the brief: search for news in the window (funding, launch,
   pricing, customers, hires, papers). Use the current year in queries.
3. **Search terms** from the brief.
4. **Channels** (YouTube, podcasts, Substack) named in the brief: look for episodes or posts in the
   window on the topic; use a transcript or show notes only if accessible. Never summarise whole
   episodes, only the relevant claim.
5. **Coming up**: deadlines and events in the next 14 days.

Keep a scratch list of candidates in `$W/work/candidates.md` (gitignored): title, date, URL,
source, one-line claim, topic. Ignore anything dated before the window unless it surfaced only now
and clears the bar; then say so in the summary.

When a feed or listing URL proves useful and stable, add it to `$W/state/sources.json` under
`feeds` with the topic id, so later runs start there.

## 3. Triage

- Drop anything already in `state/seen.json` (same URL, or the same event: same actor + same
  action + same number).
- Apply each topic's inclusion bar and leave-out list (`ANALYST.md` → Inclusion).
- Merge duplicates; keep the primary source.
- Rank by impact. Respect `items_per_issue` from each topic's front matter.

## 4. Verify

For every item you keep, open the primary source and confirm the date, numbers and names. If only
press coverage exists, look for one independent confirmation. Rate credibility from what you
actually confirmed. If the key claim cannot be confirmed and the impact is below 4, drop it.

## 5. Write

Write `$W/issues/<folder>/issue.json` following the schema and writing rules in `ANALYST.md`.
Section `id` and `label` come from each topic's front matter. Then run:

```bash
python3 $E/scripts/validate_issue.py --workspace $W --issue issues/<folder>
python3 $E/scripts/build_issue.py   --workspace $W --site $E --issue issues/<folder>
```

Fix every validation error. If the build exits with code 3 the PDF is too long: cut the
lowest-impact items or shorten summaries and build again. Optionally check the first page:
`pdftoppm -r 60 -png -f 1 -l 1 issue.pdf /tmp/p1` and look at the image.

## 6. Publish

```bash
python3 $E/scripts/publish.py --workspace $W --site $E --issue issues/<folder>
python3 $E/scripts/seen.py add --workspace $W --issue issues/<folder>
python3 $E/scripts/leak_check.py --workspace $W --site $E
```

`leak_check.py` must pass before anything is pushed. Then commit and push:
- Engine: `git add docs && git commit -m "Publish issue" && git push` (generic message only).
- Workspace: `git add -A && git commit -m "Issue <N>" && git push`.

## 7. Deliver

With the Gmail tool: send one email to every address in `delivery.email_to`.
- Subject: `<title from config> No. <N> · <issue title>`
- `htmlBody`: the exact contents of `issues/<folder>/email.html` (read the file and pass it unchanged)
- `body` (plain-text fallback): the issue title, the "In brief" lines, and the site URL.

No attachments: the PDF is on the website (Download PDF) and in the workspace.

## 8. Report

End the run with a short summary: issue number, items per section, sources that failed or were
paywalled, items dropped for low credibility, and anything that needs the owner's attention
(e.g. a topic file that produced nothing for three issues in a row).

## If something fails

- A source is unreachable: skip it, mention it in `note`.
- Nothing clears the bar in a section: publish the section as empty ("Nothing that clears the bar").
- Gmail unavailable: publish anyway and say so in the report.
- A push is rejected: fetch, rebase, push again once. Never force-push.
