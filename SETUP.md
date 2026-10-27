# Setting up Frontier Analyst for a new reader

You need a Claude plan with scheduled tasks (Pro or higher) and a free GitHub account.
Most of this is done by Claude; you do the clicks marked **You**.

## 1. Repositories (You, about 2 minutes)

1. On this repository click **Use this template → Create a new repository**. Make it **public**
   (GitHub Pages is free for public repositories; everything in it stays encrypted).
2. Create a second, **private**, empty repository for your workspace, for example `frontier-analyst`.
3. Give Claude access: install the Claude GitHub app on both repositories
   (github.com/apps/claude → Configure → Only select repositories).

## 2. Ask Claude to do the rest

Open a Claude session that can reach both repositories (Claude Code, or a Claude chat with GitHub
connected) and say:

> Set up Frontier Analyst using SETUP.md. Engine: `<you>/<public-repo>`. Workspace:
> `<you>/<private-repo>`. Here is my brief: … (paste or attach your Markdown)

Claude then follows the steps below.

## 3. What Claude does

1. **Workspace.** Copy `examples/workspace/` into the private repo. Fill in `config.yaml`
   (recipients, schedule, site URL `https://<you>.github.io/<public-repo>/`).
2. **Briefs.** Turn the reader's Markdown into one file per section under `topics/`, each with the
   front matter shown in `examples/workspace/topics/example.md`. Ask before dropping anything.
   Remove anything that identifies the reader's own company or plans, and put names that must
   never appear into `confidential_terms`.
3. **Keys.** Generate a passphrase outside both repositories and create the key pair:
   ```bash
   mkdir -p ~/.fa-local && chmod 700 ~/.fa-local
   python3 -c "import secrets,xkcdpass,os;p=os.path.join(os.path.dirname(xkcdpass.__file__),'static','eff-long');w=[l.split()[-1] for l in open(p) if l.strip()];print('-'.join(secrets.choice(w) for _ in range(6)))" > ~/.fa-local/site-password.txt
   python3 scripts/fa_crypto.py keygen --site docs/site.json --password-file ~/.fa-local/site-password.txt
   ```
   (`pip install xkcdpass` first.) Show the reader the passphrase **once**, then delete the file.
   It is not stored anywhere else, and it is never committed.
4. **Reset the site.** Remove any `docs/data/*.enc` copied from the template, commit `docs/site.json`.
5. **First issue.** Follow `RUN.md` once, by hand, and let the reader review it.
6. **Schedule.** Create a scheduled task (for example Tuesday and Friday early morning) whose
   prompt is:
   > Produce the next Frontier Analyst issue. Engine repo `<you>/<public-repo>`, workspace repo
   > `<you>/<private-repo>`. Attach both with push access, clone them, then follow RUN.md in the
   > engine repo exactly.

## 4. Turn on the website (You, 30 seconds)

In the public repo: **Settings → Pages → Build and deployment → Deploy from a branch →
`main` / `/docs` → Save**. The site appears at `https://<you>.github.io/<public-repo>/`.

## Changing things later

- **What gets researched:** edit or replace files in `topics/` in the workspace.
- **Who gets the email, page limit, schedule:** `config.yaml` in the workspace (the schedule itself
  is changed in the scheduled task's settings).
- **New passphrase:** generate one, run `keygen` again, then
  `scripts/publish.py --workspace <ws> --site . --reencrypt-all` to re-encrypt the archive.
- **Remove the owl / ἀλήθεια details:** set `issue.motif: none` in `config.yaml`.
