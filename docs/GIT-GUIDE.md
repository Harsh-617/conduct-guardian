# Git for two people — plain-language guide

Written for someone who has **not** used git before. Two people share this repo. The whole point
of this page is: **you two never overwrite each other's work.**

---

## The one-sentence mental model

GitHub holds the master copy. Each of you has your own copy on your own laptop. You *pull* to get
their latest changes, you *push* to send yours up. Trouble only happens when you both change **the
same lines of the same file** at the same time — so the plan below is mostly about avoiding that.

## The setup that keeps you out of trouble

**Split by folder.** Agree who owns what, and mostly stay in your own lane:

```
conduct-guardian/
├── backend/     ← Surya (+ Claude) — FastAPI, database, the LLM screening
├── frontend/    ← the other person, if the UI moves in here
└── docs/        ← shared, but only one of you edits a given file at a time
```

If you're both in `backend/` at once, just say so out loud first and work on different files.

## The daily rhythm (do this every single time)

**Before you start working — always:**

```bash
git pull
```

That pulls down whatever your teammate pushed. Do it first thing, every session. Most git pain
comes from skipping this.

**When you've finished a chunk of work:**

```bash
git add -A
git commit -m "short description of what you changed"
git push
```

That's it. Those four commands cover ~95% of what you'll ever need.

## If `git push` gets rejected

You'll see something about *"updates were rejected"* or *"behind"*. It just means your teammate
pushed while you were working. Fix:

```bash
git pull
git push
```

If the pull says **CONFLICT**, git is telling you *you both edited the same lines and I won't guess
which one wins.* Don't panic and don't delete anything. Open the file — you'll see:

```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> main
```

Delete the `<<<<<<<`, `=======`, `>>>>>>>` marker lines, keep the text you actually want (often
both, in order), save, then:

```bash
git add -A
git commit -m "resolve conflict"
git push
```

**Or just ask Claude** — paste the conflict in and it'll sort it out. Conflicts are normal, not a
disaster.

## Branches and PRs — do you need them?

For two people on a hackathon deadline: **probably not for everyday work.** Both pushing to `main`
with a `git pull` first is faster and has fewer moving parts.

Use a branch when you're doing something big and risky that you don't want to break `main` while
it's half-finished:

```bash
git checkout -b my-big-change     # start it
# ...work, commit as usual...
git push -u origin my-big-change  # send it up
```

Then on GitHub click **"Compare & pull request"** → **"Merge"**. A PR is just *"please look at my
changes before they join main."* Back to main afterwards with `git checkout main`.

## Adding your teammate

Once the repo exists, they need write access or they can't push:

```bash
gh repo edit --add-collaborator THEIR_GITHUB_USERNAME
```

Or on GitHub: **Settings → Collaborators → Add people**. They'll get an email invite they must
accept. Then they run, once:

```bash
git clone https://github.com/YOUR_USERNAME/conduct-guardian.git
cd conduct-guardian
```

## Rules that prevent 90% of problems

1. **`git pull` before you start. Every time.** Non-negotiable.
2. **Push small and often** — many small commits beat one giant one. Small conflicts are easy;
   giant ones are miserable.
3. **Never commit secrets.** `GROQ_API_KEY`, `DATABASE_URL` — these live in `.env`, which is
   gitignored. If a key ever does get committed, it is **burned**: rotate it immediately, don't
   just delete the line. (Removing it from the file does not remove it from git history.)
4. **Tell each other what you're touching.** One sentence in chat beats a merge conflict.
5. **Don't run commands you don't understand** because a forum said so — especially
   `git reset --hard`, `git push --force`, or anything with `-f`. Those destroy work. Ask first.

## Cheat sheet

| I want to… | Command |
|---|---|
| Get their latest changes | `git pull` |
| See what I've changed | `git status` |
| Save + send my work | `git add -A` → `git commit -m "..."` → `git push` |
| See recent history | `git log --oneline -10` |
| Undo changes to a file I haven't committed | `git checkout -- path/to/file` |
| Find out which branch I'm on | `git branch --show-current` |

Anything weirder than this: ask Claude before typing. Recovering from a bad git command is much
harder than avoiding it.
