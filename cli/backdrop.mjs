#!/usr/bin/env node
// Backdrop Club from a shell, for people and for agents (Claude Code, Codex, OpenCode, ...).
// No install: `npx -y github:faiqhilman13/backdrop-club <command>`. Node 18 or newer.

import { execFileSync, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { check, forceScheme, slug } from '../lib/check.mjs'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '..')
const REPO = 'faiqhilman13/backdrop-club'
const PLUGIN = 'backdrop-club'
const NPX = `npx -y github:${REPO}`

const argv = process.argv.slice(2)
const flags = {}
const words = []
for (let i = 0; i < argv.length; i++) {
  const a = argv[i]
  if (a.startsWith('--')) {
    const [k, v] = a.slice(2).split('=')
    if (v !== undefined) flags[k] = v
    else if (['json', 'yes', 'help'].includes(k)) flags[k] = true
    else flags[k] = argv[++i]
  } else if (a === '-h') flags.help = true
  else if (a === '-y') flags.yes = true
  else words.push(a)
}
// Data comes from the gallery's origin; links shown to people use its short address.
const SITE = (flags.site ?? process.env.BACKDROP_CLUB_SITE ?? 'https://faiqhilman13.github.io/backdrop-club/').replace(/\/?$/, '/')
const WEB = (flags.web ?? process.env.BACKDROP_CLUB_WEB ?? (flags.site || process.env.BACKDROP_CLUB_SITE ? SITE : 'https://backdrop-club.netlify.app/')).replace(/\/?$/, '/')
const asJson = Boolean(flags.json)

/** Where the current pick lives; the loader mod in Claude Code reads the same file. */
function pickFile() {
  const base = process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config')
  return path.join(base, 'backdrop-club', 'current.json')
}

function out(human, data) {
  if (asJson) process.stdout.write(`${JSON.stringify(data ?? { ok: true }, null, 2)}\n`)
  else process.stdout.write(`${human}\n`)
}

function fail(message, code = 1, data = {}) {
  if (asJson) process.stdout.write(`${JSON.stringify({ ok: false, error: message, ...data }, null, 2)}\n`)
  else process.stderr.write(`${message}\n`)
  process.exit(code)
}

async function getJson(rel) {
  let response
  try {
    response = await fetch(`${SITE}${rel}`, { headers: { 'user-agent': 'backdrop-club-cli' } })
  } catch (error) {
    fail(`Couldn't reach the gallery at ${SITE} (${error.message}).`)
  }
  if (response.status === 404) return undefined
  if (!response.ok) fail(`The gallery answered ${response.status} for ${rel}.`)
  return response.json()
}

let revoked = []
async function gallery() {
  const index = await getJson('api/v1/index.json')
  if (!index || !Array.isArray(index.themes)) fail('The gallery sent no theme list.')
  revoked = Array.isArray(index.revoked) ? index.revoked : []
  return index.themes.map(t => ({
    ...t,
    page: `${WEB}t/${t.id}/`,
    preview: `${WEB}og/${t.id}.png`,
    svg: `${WEB}t/${t.id}/backdrop.svg`,
    use: `${NPX} use ${t.id}`,
  }))
}

const key = text => String(text).toLowerCase().replace(/[^a-z0-9]+/g, '')
function find(list, asked) {
  const k = key(asked)
  if (!k) return undefined
  return list.find(t => key(t.id) === k || key(t.name) === k)
    ?? list.find(t => key(t.id).startsWith(k) || key(t.name).startsWith(k))
    ?? list.find(t => key(t.name).includes(k))
}

function table(list) {
  if (list.length === 0) return 'No themes.'
  const w = Math.max(...list.map(t => t.id.length))
  return list.map(t => `${t.id.padEnd(w)}  ${t.name} by @${t.author}${t.tags?.length ? `  [${t.tags.filter(x => x !== 'dither').join(', ')}]` : ''}`).join('\n')
}

function readPick() {
  try { return JSON.parse(fs.readFileSync(pickFile(), 'utf8')) } catch { return null }
}

function writePick(pick) {
  const file = pickFile()
  fs.mkdirSync(path.dirname(file), { recursive: true })
  const tmp = `${file}.${process.pid}.tmp`
  fs.writeFileSync(tmp, JSON.stringify({ ...pick, at: new Date().toISOString() }))
  fs.renameSync(tmp, file)
  return file
}

function loaderInstalled() {
  const config = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude')
  try {
    const data = JSON.parse(fs.readFileSync(path.join(config, 'plugins', 'installed_plugins.json'), 'utf8'))
    return Object.keys(data.plugins ?? data).some(k => k.startsWith(`${PLUGIN}@`))
  } catch {
    return false
  }
}

const HELP = `Backdrop Club: backdrops for the Claude desktop app.  ${WEB}

  ${NPX} <command> [--json]

Browse
  list [--tag <tag>]       every theme, newest first
  search <words>           themes whose name, tags or author match
  show <id>                one theme: details, page, preview image, files
  tags                     the tags, and how many themes have each

Use in the Claude app
  setup                    install the loader in Claude Code (needs the claude CLI), once
  use <id> | random        show that theme in the Claude app, within seconds
  current                  what is showing
  off | on                 hide the backdrop, or bring it back

Files
  download <id> [--out <dir>] [--mode both|light|dark]

Make and share
  check <file.svg>         the gallery's rules, and a readability score if Chrome is installed
  submit <file.svg> --name <name> [--description <text>] [--tags a,b] [--yes]
                           open a submission issue on GitHub with gh; without --yes it only shows it

Docs
  docs                     the guide for agents (also at ${WEB}llms.txt)

Every command takes --json for output a program can read.`

async function main() {
  const [command = 'help', ...rest] = words
  if (flags.help || command === 'help') return out(HELP, { ok: true, help: HELP })

  if (command === 'docs') {
    const local = path.join(ROOT, 'site', 'llms.txt')
    const text = fs.existsSync(local) ? fs.readFileSync(local, 'utf8') : await (await fetch(`${WEB}llms.txt`)).text()
    return out(text, { ok: true, docs: text })
  }

  if (command === 'list') {
    let list = await gallery()
    if (flags.tag) list = list.filter(t => t.tags?.includes(String(flags.tag).toLowerCase()))
    return out(`${list.length} theme${list.length === 1 ? '' : 's'}${flags.tag ? ` tagged ${flags.tag}` : ''}. Previews: ${WEB}\n\n${table(list)}\n\nUse one: ${NPX} use <id>`, { ok: true, count: list.length, themes: list })
  }

  if (command === 'search') {
    const terms = rest.map(w => w.toLowerCase()).filter(Boolean)
    if (terms.length === 0) fail(`Say what to look for: ${NPX} search mountains`)
    const list = (await gallery()).filter(t => {
      const hay = `${t.id} ${t.name} ${t.author} ${t.description} ${(t.tags ?? []).join(' ')}`.toLowerCase()
      return terms.every(w => hay.includes(w))
    })
    return out(list.length ? table(list) : `Nothing matches "${terms.join(' ')}". Try ${NPX} list`, { ok: true, count: list.length, themes: list })
  }

  if (command === 'tags') {
    const counts = {}
    for (const t of await gallery()) for (const tag of t.tags ?? []) if (tag !== 'dither') counts[tag] = (counts[tag] ?? 0) + 1
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])
    return out(sorted.map(([t, n]) => `${t} (${n})`).join('\n'), { ok: true, tags: Object.fromEntries(sorted) })
  }

  if (command === 'show') {
    const list = await gallery()
    const t = find(list, rest.join(' '))
    if (!t) fail(`No theme called "${rest.join(' ')}". Try ${NPX} list`, 1)
    return out([
      `${t.name} by @${t.author}`,
      t.description,
      `Tags: ${(t.tags ?? []).join(', ')}`,
      `Page: ${t.page}`,
      `Preview (light and dark): ${t.preview}`,
      `SVG: ${t.svg}`,
      `Use it: ${t.use}`,
    ].filter(Boolean).join('\n'), { ok: true, theme: t })
  }

  if (command === 'setup') {
    if (loaderInstalled()) return out('The Backdrop Club loader is already installed in Claude Code.', { ok: true, installed: true, already: true })
    const claude = spawnSync('claude', ['--version'], { encoding: 'utf8' })
    if (claude.error) {
      fail(`The claude CLI isn't on the PATH. In Claude Code (the desktop app's Code tab or a terminal), type:\n  /plugin install ${PLUGIN} --marketplace ${REPO}`, 2, { manual: `/plugin install ${PLUGIN} --marketplace ${REPO}` })
    }
    const scope = flags.scope ?? 'user'
    const run = spawnSync('claude', ['plugin', 'install', PLUGIN, '--marketplace', REPO, '--scope', scope], { encoding: 'utf8' })
    if (run.status !== 0) fail(`Installing the loader failed:\n${(run.stderr || run.stdout || '').trim()}`, run.status ?? 1)
    return out(`Installed the Backdrop Club loader (${scope} scope). New Claude Code sessions show the backdrop; pick one with ${NPX} use <id>.`, { ok: true, installed: true, scope })
  }

  if (command === 'use') {
    const asked = rest.join(' ')
    if (!asked) fail(`Say which theme: ${NPX} use tokyo (or random). See ${NPX} list`)
    const list = await gallery()
    const current = readPick()
    const others = list.filter(x => x.id !== current?.id)
    const t = asked.toLowerCase() === 'random' ? (others[Math.floor(Math.random() * others.length)] ?? list[0]) : find(list, asked)
    if (!t) fail(`No theme called "${asked}". Try ${NPX} list`)
    if (revoked.includes(t.id)) fail(`${t.name} was taken down from the gallery.`)
    const data = await getJson(`api/v1/themes/${encodeURIComponent(t.id)}.json`)
    if (!data?.svg) fail(`${t.name} could not be fetched.`)
    const result = check(data.svg)
    if (!result.ok) fail(`${t.name} was refused by the rules: ${result.errors[0]}`)
    const file = writePick({ id: data.id, name: data.name, author: data.author, svg: result.svg, hash: data.hash, off: false })
    const installed = loaderInstalled()
    const note = installed ? 'An open Claude Code session switches within a few seconds; new sessions start with it.' : `The loader isn't installed in Claude Code yet. Run: ${NPX} setup`
    return out(`Picked ${data.name} by @${data.author}. ${note}`, { ok: true, theme: { ...t, svg: undefined }, file, loaderInstalled: installed })
  }

  if (command === 'current') {
    const pick = readPick()
    if (!pick?.id) return out('Nothing picked yet: the loader shows its default scene.', { ok: true, current: null })
    return out(`${pick.off ? 'Off (last pick: ' : ''}${pick.name} by @${pick.author}${pick.off ? ')' : ''}  ${WEB}t/${pick.id}/`, { ok: true, current: { id: pick.id, name: pick.name, author: pick.author, off: Boolean(pick.off), at: pick.at } })
  }

  if (command === 'off' || command === 'on') {
    const pick = readPick() ?? {}
    writePick({ ...pick, off: command === 'off' })
    return out(command === 'off' ? 'Backdrop off. Bring it back with on.' : `Backdrop on${pick.name ? `: ${pick.name}` : ''}.`, { ok: true, off: command === 'off' })
  }

  if (command === 'download') {
    const list = await gallery()
    const t = find(list, rest.join(' '))
    if (!t) fail(`No theme called "${rest.join(' ')}". Try ${NPX} list`)
    const data = await getJson(`api/v1/themes/${encodeURIComponent(t.id)}.json`)
    const result = check(data?.svg ?? '')
    if (!result.ok) fail(`${t.name} could not be fetched cleanly.`)
    const dir = path.resolve(flags.out ?? '.')
    fs.mkdirSync(dir, { recursive: true })
    const mode = flags.mode ?? 'both'
    const files = []
    if (mode === 'both' || mode === 'all') files.push([`${t.id}.svg`, result.svg])
    if (mode === 'light' || mode === 'all') files.push([`${t.id}-light.svg`, forceScheme(result.svg, 'light')])
    if (mode === 'dark' || mode === 'all') files.push([`${t.id}-dark.svg`, forceScheme(result.svg, 'dark')])
    if (files.length === 0) fail('--mode is both, light, dark or all.')
    for (const [name, text] of files) fs.writeFileSync(path.join(dir, name), text)
    return out(`Saved ${files.map(([n]) => path.join(dir, n)).join(', ')}. Licence: ${data.license}; credit @${data.author}.`, { ok: true, files: files.map(([n]) => path.join(dir, n)), license: data.license, author: data.author })
  }

  if (command === 'check') {
    const file = rest[0]
    if (!file) fail(`Say which file: ${NPX} check my-backdrop.svg`)
    const result = check(fs.readFileSync(file, 'utf8'))
    let score = null
    if (result.ok) {
      try {
        const dist = fs.mkdtempSync(path.join(os.tmpdir(), 'backdrop-cli-'))
        fs.cpSync(path.join(ROOT, 'site', 'assets'), path.join(dist, 'assets'), { recursive: true })
        fs.copyFileSync(path.join(ROOT, 'lib', 'check.mjs'), path.join(dist, 'assets', 'check.mjs'))
        const { scoreFile } = await import('../tools/render.mjs')
        score = await scoreFile(result.svg, { dist, base: '/backdrop-club/' })
        fs.rmSync(dist, { recursive: true, force: true })
      } catch { score = null }
    }
    const lines = [
      result.ok ? `Passes the rules: ${result.stats.chars.toLocaleString('en')} characters, ${result.stats.elements} elements.` : 'Breaks the rules:',
      ...result.errors.map(e => `  - ${e}`),
      ...result.warnings.map(w => `  note: ${w}`),
      score ? `Readability: ${score.light.contrast}:1 in light mode, ${score.dark.contrast}:1 in dark (needs 4.5:1 in both) - ${score.ok ? (score.grade === 'clean' ? 'reads clean' : 'readable') : 'too little contrast'}.` : (result.ok ? 'Readability not scored (needs Google Chrome or Chromium).' : ''),
    ].filter(Boolean)
    const ok = result.ok && (score ? score.ok : true)
    out(lines.join('\n'), { ok, rules: { ok: result.ok, errors: result.errors, warnings: result.warnings, stats: result.stats }, readability: score })
    process.exit(ok ? 0 : 1)
  }

  if (command === 'submit') {
    const file = rest[0]
    if (!file) fail(`Say which file: ${NPX} submit my-backdrop.svg --name "Harbour at dusk"`)
    const name = String(flags.name ?? '').trim()
    if (!name) fail('Give it a name with --name "..."')
    const result = check(fs.readFileSync(file, 'utf8'))
    if (!result.ok) fail(`Fix these first:\n${result.errors.map(e => `  - ${e}`).join('\n')}`)
    const tags = String(flags.tags ?? '').split(',').map(t => slug(t)).filter(Boolean).slice(0, 5)
    const body = [
      '### Theme name', '', name, '',
      '### One line about it', '', String(flags.description ?? '').trim() || '_No response_', '',
      '### Tags', '', tags.join(', ') || '_No response_', '',
      '### Theme file', '', '```xml', result.svg, '```', '',
      '### Rights', '', '- [X] I made this art, or have the right to share it, and I license it under CC BY 4.0.', '',
    ].join('\n')
    if (body.length > 65000) fail(`It's too big for an issue (${body.length} characters; GitHub allows 65,536). Open a pull request instead: see CONTRIBUTING.md in ${REPO}.`)
    const title = `Theme: ${name}`
    if (!flags.yes) {
      return out(`Ready to submit "${name}" (${tags.join(', ') || 'no tags'}, ${result.stats.chars.toLocaleString('en')} characters) as a public GitHub issue on ${REPO}, under your GitHub account.\nBy submitting you confirm you made the art or may share it, and license it under CC BY 4.0.\nRun again with --yes to send it.`, { ok: true, sent: false, title, repo: REPO })
    }
    const tmp = path.join(os.tmpdir(), `backdrop-submit-${process.pid}.md`)
    fs.writeFileSync(tmp, body)
    let url
    try {
      url = execFileSync('gh', ['issue', 'create', '-R', REPO, '--title', title, '--body-file', tmp], { encoding: 'utf8' }).trim()
    } catch (error) {
      fail(`gh couldn't create the issue (is it installed and logged in? gh auth status).\n${error.stderr ?? error.message}`)
    } finally {
      fs.rmSync(tmp, { force: true })
    }
    return out(`Submitted: ${url}\nA bot checks it and opens a pull request within a few minutes.`, { ok: true, sent: true, url })
  }

  fail(`Unknown command "${command}".\n\n${HELP}`)
}

main().catch(error => fail(error?.stack ?? String(error)))
