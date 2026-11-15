# Netlify

`backdrop-club.netlify.app` is a proxy: `_redirects` sends every request to the GitHub Pages build, so each merge to `main` shows up here with no second deploy. Redeploy this folder only if `_redirects` changes:

```
npx netlify-cli deploy --prod --dir netlify --site backdrop-club
```
