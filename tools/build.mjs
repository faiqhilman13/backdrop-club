#!/usr/bin/env node
// Builds the gallery from themes/: the website into dist/, and the loader's bundled files.
//
//   node tools/build.mjs            check every theme and build the site
//   node tools/build.mjs --render   also score readability and draw share images (needs Chrome)
//   node tools/build.mjs --check    only check the themes; exit 1 on any problem
//
// A theme is a folder themes/<id>/ holding theme.json and backdrop.svg. Nothing else is read.

import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { ID, LIMIT, READING, check, checkDetails, forceScheme } from '../lib/check.mjs'
import { pages } from './pages.mjs'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const config = JSON.parse(fs.readFileSync(path.join(ROOT, 'site/config.json'), 'utf8'))
const flags = new Set(process.argv.slice(2).filter(a => !a.startsWith('--only=')))
// --only=a,b checks just those themes: other themes' problems are left to their own checks.
const ONLY = (process.argv.find(a => a.startsWith('--only=')) ?? '').slice('--only='.length).split(',').filter(Boolean)
// A check builds into a folder of its own, so checks running side by side never share one.
const DIST = flags.has('--check') ? fs.mkdtempSync(path.join(os.tmpdir(), 'backdrop-check-')) : path.join(ROOT, 'dist')
if (flags.has('--check')) process.on('exit', () => fs.rmSync(DIST, { recursive: true, force: true }))

export function loadThemes(dir = path.join(ROOT, 'themes')) {
  const themes = []
  const problems = []
  for (const id of fs.readdirSync(dir).sort()) {
    const folder = path.join(dir, id)
    if (!fs.statSync(folder).isDirectory()) continue
    const say = text => problems.push(`themes/${id}: ${text}`)
    if (!ID.test(id) || id.length > 40) { say('the folder name must be lower-case words joined by dashes'); continue }
    let details
    try { details = JSON.parse(fs.readFileSync(path.join(folder, 'theme.json'), 'utf8')) } catch (error) { say(`theme.json: ${error.message}`); continue }
    for (const problem of checkDetails(details)) say(`theme.json: ${problem}`)
    let svg = ''
    try { svg = fs.readFileSync(path.join(folder, 'backdrop.svg'), 'utf8') } catch { say('backdrop.svg is missing'); continue }
    const result = check(svg)
    for (const error of result.errors) say(`backdrop.svg: ${error}`)
    const extra = fs.readdirSync(folder).filter(f => !['theme.json', 'backdrop.svg'].includes(f))
    if (extra.length > 0) say(`only theme.json and backdrop.svg belong here, not ${extra.join(', ')}`)
    if (!result.ok) continue
    themes.push({
      id,
      name: details.name.trim(),
      author: details.author,
      description: (details.description ?? '').trim(),
      tags: details.tags ?? [],
      added: details.added ?? new Date().toISOString().slice(0, 10),
      license: details.license ?? 'CC-BY-4.0',
      svg: result.svg,
      hash: crypto.createHash('sha256').update(result.svg).digest('hex').slice(0, 16),
      chars: result.svg.length,
      hasDarkMode: result.stats.hasDarkMode,
      warnings: result.warnings,
    })
  }
  return { themes, problems }
}

function write(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, content)
}

function copyDir(from, to) {
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    const a = path.join(from, entry.name)
    const b = path.join(to, entry.name)
    if (entry.isDirectory()) copyDir(a, b)
    else { fs.mkdirSync(to, { recursive: true }); fs.copyFileSync(a, b) }
  }
}

/** Writes `content` to `file` only when it differs, and says so. */
function sync(file, content) {
  const old = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : null
  if (old === content) return false
  write(file, content)
  console.log(`updated ${path.relative(ROOT, file)}`)
  return true
}

const STARTER = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 160" width="100%" height="100%" preserveAspectRatio="xMidYMax slice">
  <style>
    :root { color-scheme: light dark }
    .night { display: none }
    @media (prefers-color-scheme: dark) {
      .day { display: none }
      .night { display: inline }
    }
  </style>
  <g class="day">
    <rect width="512" height="160" fill="#f5f2ea"/>
    <circle cx="300" cy="126" r="14" fill="#f4bcae"/>
    <path d="M0 160V136L64 124L128 134L196 114L252 128L318 110L388 126L452 118L512 130V160Z" fill="#b5d3cd"/>
    <path d="M0 160V146L90 140L170 148L260 138L350 146L430 140L512 146V160Z" fill="#9cc3bd"/>
  </g>
  <g class="night">
    <rect width="512" height="160" fill="#0b0c14"/>
    <circle cx="300" cy="126" r="14" fill="#2b2240"/>
    <path d="M0 160V136L64 124L128 134L196 114L252 128L318 110L388 126L452 118L512 130V160Z" fill="#141826"/>
    <path d="M0 160V146L90 140L170 148L260 138L350 146L430 140L512 146V160Z" fill="#07080e"/>
  </g>
</svg>`

const FAVICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" shape-rendering="crispEdges"><style>rect{fill:#d9466f}.g{fill:#2f6f68}@media (prefers-color-scheme:dark){rect{fill:#ff8fb1}.g{fill:#6ee7b7}}</style><rect x="5" y="3" width="6" height="1"/><rect x="4" y="4" width="8" height="1"/><rect x="3" y="5" width="10" height="2"/><rect x="3" y="8" width="10" height="1"/><rect x="4" y="10" width="8" height="1"/><rect class="g" x="0" y="12" width="16" height="2"/><rect class="g" x="2" y="15" width="12" height="1"/></svg>`

/** Themes taken down: their ids, and why. Listed in site/revoked.json. */
function readRevoked() {
  try {
    const list = JSON.parse(fs.readFileSync(path.join(ROOT, 'site/revoked.json'), 'utf8'))
    return Array.isArray(list) ? list.filter(r => typeof r?.id === 'string') : []
  } catch {
    return []
  }
}

async function main() {
  const loaded = loadThemes()
  const isMine = text => ONLY.length === 0 || ONLY.some(id => text.startsWith(`themes/${id}:`))
  const problems = loaded.problems.filter(isMine)
  const themes = ONLY.length > 0 ? loaded.themes.filter(t => ONLY.includes(t.id)) : loaded.themes
  for (const id of ONLY) if (!themes.some(t => t.id === id) && !problems.some(p => p.startsWith(`themes/${id}:`))) problems.push(`themes/${id}: not found`)
  const revoked = readRevoked()
  for (const theme of loaded.themes) if (revoked.some(r => r.id === theme.id)) problems.push(`themes/${theme.id}: this id was taken down (site/revoked.json); use another id`)
  for (const theme of themes) for (const w of theme.warnings) console.log(`note: themes/${theme.id}: ${w}`)
  if (problems.length > 0) {
    console.error(`\n${problems.length} problem${problems.length === 1 ? '' : 's'}:\n${problems.map(p => `  - ${p}`).join('\n')}`)
    process.exit(1)
  }
  console.log(`${themes.length} themes pass the rules (each under ${LIMIT.toLocaleString('en')} characters).`)
  if (flags.has('--check') && !flags.has('--render')) return

  // Newest first, then by name.
  themes.sort((a, b) => b.added.localeCompare(a.added) || a.name.localeCompare(b.name))
  const byId = new Map(themes.map(t => [t.id, t]))

  fs.rmSync(DIST, { recursive: true, force: true })
  copyDir(path.join(ROOT, 'site/assets'), path.join(DIST, 'assets'))
  fs.copyFileSync(path.join(ROOT, 'lib/check.mjs'), path.join(DIST, 'assets/check.mjs'))
  write(path.join(DIST, 'assets/site.json'), JSON.stringify({ base: config.base, repo: config.repo, command: config.command, plugin: config.plugin }))

  for (const theme of themes) {
    const dir = path.join(DIST, 't', theme.id)
    write(path.join(dir, 'backdrop.svg'), theme.svg)
    write(path.join(dir, 'light.svg'), forceScheme(theme.svg, 'light'))
    write(path.join(dir, 'dark.svg'), forceScheme(theme.svg, 'dark'))
    const record = JSON.stringify({ id: theme.id, name: theme.name, author: theme.author, description: theme.description, tags: theme.tags, license: theme.license, hash: theme.hash, svg: theme.svg })
    write(path.join(DIST, 'api/v1/themes', `${theme.id}.json`), record)
    write(path.join(DIST, 'api/themes', `${theme.id}.json`), record)
  }

  // Scores and share images come from a real browser.
  if (flags.has('--render')) {
    const { render } = await import('./render.mjs')
    const result = await render(themes, { dist: DIST, base: config.base, og: !flags.has('--check'), cacheDir: path.join(ROOT, '.cache', 'render') })
    if (result) {
      for (const theme of themes) {
        theme.score = result.scores[theme.id]
        theme.hasOg = result.og.includes(theme.id)
      }
      const failing = themes.filter(t => t.score && (t.score.light.contrast < READING.minContrast || t.score.dark.contrast < READING.minContrast))
      for (const t of themes) if (t.score) console.log(`  ${t.id.padEnd(20)} light ${String(t.score.light.contrast).padStart(4)}:1 busy ${t.score.light.busy}   dark ${String(t.score.dark.contrast).padStart(4)}:1 busy ${t.score.dark.busy}`)
      if (failing.length > 0) {
        console.error(`\nToo little contrast for chat text (needs ${READING.minContrast}:1 in both modes): ${failing.map(t => t.id).join(', ')}`)
        process.exit(1)
      }
      if (flags.has('--check')) return
    }
  }

  const featured = config.featured.map(id => byId.get(id)).filter(Boolean)
  for (const t of themes) if (!featured.includes(t)) featured.push(t)
  const p = pages(config)

  write(path.join(DIST, 'index.html'), p.home(themes, featured.slice(0, 8)))
  write(path.join(DIST, 'gallery/index.html'), p.galleryPage(themes))
  themes.forEach((theme, i) => {
    const more = [...themes.slice(i + 1), ...themes.slice(0, i)].slice(0, 3)
    write(path.join(DIST, 't', theme.id, 'index.html'), p.themePage(theme, more))
  })
  write(path.join(DIST, 'make/index.html'), p.makePage())
  write(path.join(DIST, 'submit/index.html'), p.submitPage())
  write(path.join(DIST, 'guide/index.html'), p.guidePage(STARTER))
  write(path.join(DIST, 'agents/index.html'), p.agentsPage())
  fs.copyFileSync(path.join(ROOT, 'site/llms.txt'), path.join(DIST, 'llms.txt'))
  write(path.join(DIST, '404.html'), p.notFound())
  write(path.join(DIST, 'favicon.svg'), FAVICON)
  write(path.join(DIST, '.nojekyll'), '')

  const updated = new Date().toISOString()
  const listed = themes.map(t => ({ id: t.id, name: t.name, author: t.author, description: t.description, tags: t.tags, added: t.added, hash: t.hash }))
  write(path.join(DIST, 'api/index.json'), JSON.stringify({ updated, count: themes.length, themes: listed }))
  // v1 also names the themes taken down, so loaders drop them from machines that kept a copy.
  write(path.join(DIST, 'api/v1/index.json'), JSON.stringify({ version: 1, updated, count: themes.length, themes: listed, revoked: revoked.map(r => r.id) }))

  const site = `${config.origin}${config.base}`
  const urls = ['', 'gallery/', 'make/', 'submit/', 'guide/', 'agents/', 'llms.txt', ...themes.map(t => `t/${t.id}/`)]
  write(path.join(DIST, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u => `  <url><loc>${site}${u}</loc></url>`).join('\n')}\n</urlset>\n`)
  write(path.join(DIST, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${site}sitemap.xml\n`)

  // The loader carries the rulebook and one scene, so it works offline from the first start.
  sync(path.join(ROOT, 'plugin/hooks/check.js'), `// Copied from lib/check.mjs by tools/build.mjs. Edit that file, not this one.\n${fs.readFileSync(path.join(ROOT, 'lib/check.mjs'), 'utf8')}`)
  sync(path.join(ROOT, 'plugin/hooks/site.js'), `// Written by tools/build.mjs from site/config.json: where the loader fetches themes.\nexport const SITE = ${JSON.stringify(`${config.origin}${config.base}`)}\n`)
  const fallback = byId.get(config.defaultTheme) ?? themes[0]
  sync(path.join(ROOT, 'plugin/hooks/default.js'), `// Written by tools/build.mjs from themes/${fallback.id}. The scene shown before any other is picked.\nexport const DEFAULT = ${JSON.stringify({ id: fallback.id, name: fallback.name, author: fallback.author, svg: fallback.svg })}\n`)

  console.log(`Built ${themes.length} theme pages into dist/.`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error); process.exit(1) })
}
