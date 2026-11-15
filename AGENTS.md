# AGENTS.md

Guidance for AI coding agents (Codex, OpenCode, Claude Code, Cursor, Gemini CLI, ...) working in this repository or on behalf of someone who wants a backdrop.

## If you were sent here to install a backdrop

You don't need to clone anything. Follow https://backdrop-club.netlify.app/llms.txt. In short:

```
npx -y github:faiqhilman13/backdrop-club list            # show the person the themes (add --json to parse)
npx -y github:faiqhilman13/backdrop-club setup           # install the loader in Claude Code, once
npx -y github:faiqhilman13/backdrop-club use <their-pick>
```

Let the person choose the theme. Each one has a preview at `https://backdrop-club.netlify.app/og/<id>.png`.

## What this repository is

A gallery of backdrops for the Claude desktop app, published to GitHub Pages, plus the pieces around it:

| Path | What |
| --- | --- |
| `themes/<id>/` | One folder per theme: `theme.json` and `backdrop.svg`, nothing else |
| `lib/check.mjs` | The rulebook. The build, the bot, the CLI, the website and the loader all use it |
| `plugin/` | The loader mod people install in Claude Code (`/backdrop`, Claude's two tools, the shared pick file) |
| `cli/backdrop.mjs` | The command line, run through `npx -y github:faiqhilman13/backdrop-club` |
| `tools/build.mjs` | Builds the site into `dist/`. `--render` scores readability and draws share images with Chrome |
| `tools/submission.mjs` | The bot that turns submission issues into pull requests |
| `site/` | Page scripts and styles, the photo maker, `llms.txt` |
| `art/` | The Python kit that drew the starter themes, and their sources |

No package dependencies. Node 22 for the tools, Chrome or Chromium for `--render`, Python 3 with numpy for `art/`.

## Adding a theme

1. Make `themes/<id>/backdrop.svg` (the id is lower-case words joined by dashes) and `themes/<id>/theme.json`:
   ```json
   { "name": "Harbour at dusk", "author": "<github-username>", "description": "One plain sentence.", "tags": ["city", "sea"], "added": "YYYY-MM-DD", "license": "CC-BY-4.0" }
   ```
2. Follow the rules in https://backdrop-club.netlify.app/guide/#rules. The short version: the scene stays in the bottom third of the window; pale fills by day, dark by night; 4.5:1 contrast for chat text in both modes; still, self-contained SVG under 120,000 characters.
3. Check it: `node tools/build.mjs --render --check --only=<id>`. It must pass.
4. To draw in the house style, use the kit: see `art/README.md`, write `art/scene_<name>.py`, preview with `python3 art/look.py scene_<name> <dir>`, export with `python3 art/export.py scene_<name>`.

## Changing code

- Edit `lib/check.mjs`, never its copies: the build writes `plugin/hooks/check.js` and `dist/assets/check.mjs` from it.
- `node tools/build.mjs --render` then `node tools/serve.mjs` serves the site at http://127.0.0.1:4173/backdrop-club/.
- Loader tests: `claude plugin test plugin`. Validate: `claude plugin validate plugin` and `claude plugin validate .`.
- Bump `plugin/.claude-plugin/plugin.json`'s version when the loader changes, so installs update.
- Pushing to `main` deploys the site (`.github/workflows/deploy.yml`).

## Maintaining the gallery

- **Taking a theme down:** delete its `themes/<id>/` folder and add `{ "id": "<id>", "reason": "...", "date": "YYYY-MM-DD" }` to `site/revoked.json`, then push. The id can't be reused, the theme leaves the site, and installed loaders drop it within a few hours (they check `api/v1/index.json`'s `revoked` list).
- **Updating a theme:** change its `backdrop.svg` and push. Its fingerprint (`hash` in the API) changes, and loaders that kept the old copy fetch the new one within a few hours.
- **Builds:** readability scores and share images are cached under `.cache/render/`, keyed by each theme's fingerprint (and by the code that made them), locally and in CI. A push renders only new or changed themes. Delete `.cache/` to start over.
- **API:** clients use `api/v1/`. Keep the unversioned `api/` files: loaders older than 0.3.0 read them. Change `v1`'s shape only by adding fields; anything else is a `v2`.
- **A mirror:** `.github/workflows/mirror.yml` pushes every branch and tag to a second host once a `MIRROR_URL` secret exists. Make an empty repository on Codeberg or GitLab, create an access token with write access, then run `gh secret set MIRROR_URL -R faiqhilman13/backdrop-club` and paste `https://<user>:<token>@codeberg.org/<user>/backdrop-club.git`.
- **The address:** people use `https://backdrop-club.netlify.app/`, a Netlify proxy (`netlify/_redirects`) in front of the GitHub Pages build, so a merge shows up there with no second deploy. The loader and CLI read data straight from GitHub Pages (`api` in `site/config.json`). Pages opened at the old `github.io` address send people to the new one. To move to a custom domain later, add it to the Netlify site and set `origin` in `site/config.json`.

## Don't

- Put anything but drawing elements in a theme (the rulebook refuses scripts, animation, event handlers, external links and fonts).
- Commit `dist/`.
- Submit or merge a theme on someone's behalf without their say-so: submissions are public and go out under their GitHub account.
