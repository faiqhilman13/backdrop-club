# Adding a theme

## The easy way

1. Make your theme with the [maker](https://backdrop-club.netlify.app/make/), or draw one by hand (see the [guide](https://backdrop-club.netlify.app/guide/)).
2. Open the [Submit page](https://backdrop-club.netlify.app/submit/), add your file, a name and a few tags. It shows your theme in light and dark mode and runs the gallery's checks.
3. Press **Copy and open GitHub**, paste into **Theme file**, and create the issue.
4. The bot replies within a couple of minutes: either a pull request with your theme, or a list of what to fix. Edit the issue and it checks again.

You're credited as the issue's author, linked to your GitHub profile.

## By pull request

Add a folder `themes/<id>/` with two files:

`theme.json`

```json
{
  "name": "Harbour at dusk",
  "author": "your-github-username",
  "description": "Cranes and container ships under a pink sky.",
  "tags": ["city", "sea", "sunset"],
  "added": "2026-11-15",
  "license": "CC-BY-4.0"
}
```

`backdrop.svg`: your theme. Then run `node tools/build.mjs --render --check` (Node 22 and Chrome) and open a pull request. The same check runs on it.

## What gets merged

- Art you made or may share. No logos, brands, or other people's photos or artwork.
- Nothing hateful, sexual, or meant to shock. It sits behind people's work all day.
- It passes the checks: the [rules](https://backdrop-club.netlify.app/guide/#rules) are in the guide.
- A distinct scene, not a recolour of an existing theme.

A maintainer reviews every theme before it's merged. Ids are first come, first served.

## Changing the code

The rulebook is `lib/check.mjs`; the build copies it into `site/` and `plugin/`, so edit it there. Run the loader's tests with `claude plugin test plugin`.
