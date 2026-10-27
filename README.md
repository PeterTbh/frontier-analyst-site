# Frontier Analyst

A research-briefing skeleton for Claude. Describe what you want to follow in a Markdown file;
Claude scans the web, papers, newsletters and channels on a schedule, verifies what it finds,
rates each item for credibility and impact, and delivers a short, well-designed newsletter:
an email, a PDF and a password-protected website.

- **Topic-agnostic.** Everything topic-specific lives in your own Markdown briefs.
- **Private by design.** Your briefs, settings and archive stay in a private repository.
  The public website only ever receives encrypted files.
- **No API key, no servers.** Runs as a scheduled task on a Claude plan (Pro or higher) and
  publishes with GitHub Pages.

## How it works

```
 private workspace repo                   this repo (public)
 ┌──────────────────────┐                 ┌────────────────────────────────┐
 │ config.yaml          │   each run      │ RUN.md, ANALYST.md  procedure  │
 │ topics/*.md   briefs │ ──────────────▶ │ scripts/   build, encrypt      │
 │ state/  already seen │   Claude        │ templates/ newsletter design   │
 │ issues/  archive     │ ◀────────────── │ docs/      encrypted website   │
 └──────────────────────┘                 └────────────────────────────────┘
                                   │
                                   └──▶ email to your inbox
```

1. A scheduled Claude task opens both repositories and follows [`RUN.md`](RUN.md).
2. It reads your briefs, scans sources, triages against your inclusion bar, verifies each item at
   the primary source, and rates it using the standards in [`ANALYST.md`](ANALYST.md).
3. It writes `issue.json`, validates it, and builds the web, PDF and email versions.
4. It encrypts the issue into `docs/` (public key only, no password needed), pushes, and emails it.

## Encryption

The site is a static page that decrypts in the reader's browser.

- An RSA-3072 key pair is generated once. The public key encrypts every issue, so runs never
  need the password.
- The private key is stored in `docs/site.json`, locked with AES-256-GCM under a key derived from
  your passphrase (PBKDF2-SHA256, 600,000 iterations, random salt).
- Each file has its own random AES-256-GCM key. File names are random; the archive index is
  encrypted too.
- The passphrase is never stored, never put in a URL and never sent anywhere. Use a random
  passphrase of six or more words: the setup generates one.

## Use it yourself

See [`SETUP.md`](SETUP.md). In short: copy this template, create a private workspace from
[`examples/workspace`](examples/workspace), write your brief, and ask Claude to set it up.

## Files

| Path | What it is |
|---|---|
| `RUN.md` | Step-by-step procedure for producing an issue |
| `ANALYST.md` | Research, rating and writing standards; `issue.json` schema |
| `SETUP.md` | Setting it up for a new reader |
| `scripts/` | `build_issue.py`, `validate_issue.py`, `publish.py`, `fa_crypto.py`, `seen.py`, `leak_check.py` |
| `templates/` | Newsletter design: web/PDF (`issue.html.j2`, `issue.css`) and email (`email.html.j2`) |
| `docs/` | The website: viewer, fonts, `site.json` and encrypted issues |
| `examples/workspace/` | Starting point for your private workspace |

Fonts: Newsreader, Inter and EB Garamond, under the SIL Open Font License (see `docs/fonts`).
