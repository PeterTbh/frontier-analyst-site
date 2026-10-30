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
   `$W/state/sources.json`, `$W/state/carryover.json` (may not exist) and
   `$W/issues/manifest.json` (may not exist yet). If `watch:` is set
   in the config, also read the people watchlist (`watch.people`) and the newsletter registry
   (`watch.newsletters`).
4. Issue number = last number + 1 (or 1). Window: from the last issue's date (or
   `first_issue_lookback_days` ago) to today. Issue folder: `issues/<today>-no<N>` in `$W`.
   **Guard:** if the last issue is dated today or yesterday, stop here and report
   "Skipped: last issue is less than two days old". Do not publish or email anything.
5. Make a task list with steps 1–9 so progress is visible.

## 1. Newsletters

If a Gmail tool is available and `delivery.newsletter_address` is set. It can be one address or a
list, and several briefings may share an address: each workspace keeps its own registry and
tiers. With a list, use `deliveredto:(<a> OR <b>)` wherever `<newsletter_address>` appears below.
Gmail rate-limits reading message headers and bodies ("Resource has been exhausted"); searches
that return thread IDs only (`view: THREAD_VIEW_IDS_ONLY`) keep working. So count and match with
ID-only searches, and read only what matters.

1. **List.** One ID-only search for `deliveredto:<newsletter_address> after:<from>`, paging
   through all results. If the newsletter registry exists, run one ID-only search per entry,
   `deliveredto:<newsletter_address> after:<from> from:(<match>)`, to map threads to publications.
   Threads that match no entry are unknown senders (usually lists added by Substack
   recommendations).
2. **Status.** Two more ID-only searches in the window: `subject:(confirm OR verify OR
   verification)` and `subject:(welcome OR subscribed)`. In the registry, set `status` to `live`
   once a welcome or an issue has arrived, or `pending-confirm` when only a confirmation request
   has, and set `last_seen`. Never click a confirmation, sign-in or unsubscribe link. Pending
   ones go in the report.
3. **Triage and read.** Decide what to open from the registry, not by reading subject lines first,
   because header reads cost the same quota as bodies. ID-only results come newest first.
   - `core`: open every thread in the window, except for `cadence: daily` senders, where you open
     only the newest.
   - `scan`: open the newest thread per sender while the budget lasts, dailies first.
   - `headlines`: don't open. If quota allows, run one search with `view: THREAD_VIEW_MINIMAL` and
     a page size of 10–20 to get their subject lines, and use them only as leads to search for.
   - `ignore`, unknown senders, and welcome, confirmation and receipt emails: skip.

   Read at most about 25 bodies, as `PLAIN_TEXT`, 30–60 seconds apart. After "Resource has been
   exhausted", wait 2 minutes and retry once, then move on and mention it in `note`.
4. **Use.** Note candidate items and prefer the primary source a newsletter points to. Links
   inside emails are tracking redirects that cannot be opened directly, so search for the primary
   source's title and open the URL from the search result. If no primary can be found, cite the
   newsletter's web version (found by search) with source type `Analysis`.
5. **File.** If a Gmail filter already labels these emails and skips the inbox, do nothing.
   Otherwise add `delivery.newsletter_label` and remove `INBOX` only on the threads you read
   (create the label if it is missing), to save quota.

## 2. Scan

Per topic file, in `order`. Budget for the whole run: about 50 web searches and 50 page fetches,
split by `weight` (high ≈ half, the rest shared). Stop early when the topics are covered.

For each topic, in this order:
1. **Known primary sources** in `$W/state/sources.json` (company blogs, preprint listings, regulator
   pages, newsletter archives): fetch and look for entries dated inside the window. Skip entries
   with `delivery: email` **only if that publication actually delivered** (step 1); a `core` or
   `scan` publication that sent nothing is read from its web archive instead. An unattended run can
   open a URL only if it appears in the scheduled task's prompt or in a search result. If a fetch
   asks for permission, search for the source by name and open the URL from the results instead.
   A source entry may set `access: mcp-connector` when a connector reads it better than its URL.
2. **Companies and people** named in the brief: search for news in the window (funding, launch,
   pricing, customers, hires, papers). Use the current year in queries.
3. **Search terms** from the brief.
4. **Channels** (YouTube, podcasts, Substack) named in the brief: list what appeared in the window,
   then read only what looks relevant, by **Reading channels and archives** below. Never summarise
   whole episodes, only the relevant claim.
5. **Coming up**: deadlines and events in the next 14 days.

6. **People** (once per run, after the topics, about 10 searches). If the people watchlist
   exists: for each `priority: high` person, search `"<name>" <month> <year>` and check their
   `direct` channels (own newsletter, blog, transcripts) for anything inside the window. For
   `normal` people, only note what the rest of the scan surfaced. Keep claims that meet
   `ANALYST.md` → People, and file each under the topic it affects.

### Reading channels and archives

Access paths by platform, tested 2026-10-30. Which publications these apply to is workspace
material: keep the names, URLs and results in `$W/state/sources.json`, never here. Prefer the first
path that works, and record failures in `note`.

- **Substack-hosted sites** (newsletters, and podcasts that host there): fetch `<domain>/archive`,
  which lists post dates, titles and URLs. The homepage renders nothing, and `/api/v1/archive`
  returned months-old posts, so do not trust it. Post pages carry the full text, including
  interview transcripts. This is also how a `core` publication that has not emailed yet gets read.
- **Podcasts**: prefer a transcript the show publishes itself. Those are `Primary` and quotable.
  Where an episode list refuses to fetch, a transcripts index or category page often works.
- **Third-party machine transcripts**: timestamped, but typically carry **no speaker labels**, so a
  quote cannot be attributed to one host and will not meet `ANALYST.md` → People. Treat them as
  leads only, and confirm the words in a primary source before quoting.
- **Video pages**: expect title, channel, publish date, description and chapter titles, but **no
  transcript**. Enough to judge whether an episode matters, never enough to quote. Library or
  show-notes pages that wrap a video are usually metadata only, the same limit. Always read the
  publish date off the page: searches surface old videos as if they were current.
- **Long pages**: a fetch returns the first 100k characters and says how many remain. Transcripts
  run past this, so re-fetch with the stated `offset` when the part you need is missing.

Keep a scratch list of candidates in `$W/work/candidates.md` (gitignored): title, date, URL,
source, one-line claim, topic. Ignore anything dated before the window unless it surfaced only now
and clears the bar; then say so in the summary.

When a feed or listing URL proves useful and stable, add it to `$W/state/sources.json` under
`feeds` with the topic id, so later runs start there.

## 3. Triage

- Add anything in `state/carryover.json` that is still inside its `use_by`: items found after the
  last issue was built, so they predate this window. Judge them like any other candidate, verify
  the primary source the entry names, and delete entries once used or expired.
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
(e.g. a topic file that produced nothing for three issues in a row). From the newsletter registry,
list subscriptions still `pending-confirm`, `core` or `scan` newsletters silent for three issues,
and new unknown senders.

## If something fails

- A source is unreachable: skip it, mention it in `note`.
- Nothing clears the bar in a section: publish the section as empty ("Nothing that clears the bar").
- Gmail unavailable or rate-limited: work with what was read, publish anyway and say so in the
  report.
- A push is rejected: fetch, rebase, push again once. Never force-push.
