# Netlify

`backdrop-club.netlify.app` is a proxy: `_redirects` sends every request to the GitHub Pages build, so each merge to `main` shows up here with no second deploy. Redeploy this folder only if `_redirects` changes:

```
npx netlify-cli deploy --prod --no-build --dir netlify --site 81354aec-ee29-4a31-be68-60449dd221fe
```
