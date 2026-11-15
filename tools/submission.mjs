#!/usr/bin/env node
// The submission bot. Run by .github/workflows/submission.yml when someone opens or edits an
// issue made from the "Submit a theme" form: it checks the theme, then opens a pull request
// that adds it, or answers on the issue with what to fix.
//
// The issue is untrusted data. Nothing in it is run: it is parsed, checked against the
// allow-list in lib/check.mjs, and written to two files at a path built from a safe id.
// Commands get their arguments as arrays, never through a shell.

import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { check, checkDetails, slug, READING } from '../lib/check.mjs'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const config = JSON.parse(fs.readFileSync(path.join(ROOT, 'site/config.json'), 'utf8'))
const MARK = '<!-- backdrop-club-bot -->'
const LABEL = 'theme-submission'
const NEEDS = 'needs-changes'

const run = (cmd, args, options = {}) => execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'], ...options }).trim()
const gh = (...args) => run('gh', args)

/** Reads an issue made from the form: "### Label" headings, each followed by its answer. */
export function parseIssue(body) {
  const fields = {}
  const parts = String(body ?? '').replace(/\r\n/g, '\n').split(/^### +(.+)$/m)
  for (let i = 1; i < parts.length; i += 2) {
    let value = parts[i + 1].trim()
    if (value === '_No response_') value = ''
    fields[parts[i].trim().toLowerCase()] = value
  }
  const fence = (fields['theme file'] ?? '').match(/```[a-z]*\n([\s\S]*?)\n?```/)
  return {
    name: (fields['theme name'] ?? '').split('\n')[0].trim(),
    description: (fields['one line about it'] ?? '').split('\n')[0].trim(),
    tags: [...new Set((fields.tags ?? '').split(/[,\n]/).map(t => slug(t)).filter(t => t && t.length <= 20))].slice(0, 5),
    svg: fence ? fence[1] : (fields['theme file'] ?? ''),
    rights: /-\s*\[x\]/i.test(fields.rights ?? ''),
  }
}

/** The id a new theme gets: from its name, made unique against the themes already in the gallery. */
export function pickId(name, author, issueNumber, themesDir = path.join(ROOT, 'themes')) {
  const base = slug(name) || `theme-${issueNumber}`
  const taken = id => {
    const file = path.join(themesDir, id, 'theme.json')
    if (!fs.existsSync(file)) return false
    try { return JSON.parse(fs.readFileSync(file, 'utf8')).issue !== issueNumber } catch { return true }
  }
  if (!taken(base)) return base
  const mine = slug(`${base}-${author}`)
  if (!taken(mine)) return mine
  for (let n = 2; n < 100; n++) if (!taken(`${mine}-${n}`)) return `${mine}-${n}`
  return `${base}-${issueNumber}`
}

function comment(repo, number, text) {
  const body = `${MARK}\n${text}`
  const comments = JSON.parse(gh('api', `repos/${repo}/issues/${number}/comments`, '--paginate'))
  const mine = comments.find(c => c.user?.login === 'github-actions[bot]' && c.body?.includes(MARK))
  if (mine) gh('api', '-X', 'PATCH', `repos/${repo}/issues/comments/${mine.id}`, '-f', `body=${body}`)
  else gh('api', '-X', 'POST', `repos/${repo}/issues/${number}/comments`, '-f', `body=${body}`)
}

function label(repo, number, name, isOn) {
  try {
    if (isOn) gh('api', '-X', 'POST', `repos/${repo}/issues/${number}/labels`, '-f', `labels[]=${name}`)
    else gh('api', '-X', 'DELETE', `repos/${repo}/issues/${number}/labels/${encodeURIComponent(name)}`)
  } catch {
    // A label that is already on, or already off, is fine.
  }
}

async function main() {
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'))
  const repo = process.env.GITHUB_REPOSITORY
  const issue = event.issue
  if (!issue || issue.pull_request || issue.state !== 'open') return
  if (!issue.labels?.some(l => l.name === LABEL)) return

  const author = issue.user.login
  const form = parseIssue(issue.body)
  const problems = []
  if (!form.rights) problems.push('Tick the box that says you made the art (or may share it) and license it under CC BY 4.0.')
  const id = pickId(form.name, author, issue.number)
  const details = { name: form.name, author, description: form.description, tags: form.tags, added: new Date().toISOString().slice(0, 10), license: 'CC-BY-4.0', issue: issue.number }
  problems.push(...checkDetails(details).map(p => `Details: ${p}.`))
  const result = check(form.svg)
  problems.push(...result.errors.map(e => `Theme file: ${e}`))

  let score = null
  if (result.ok) {
    const { scoreFile } = await import('./render.mjs')
    score = await scoreFile(result.svg, { dist: path.join(ROOT, 'dist'), base: config.base })
    if (score && !score.ok) problems.push(`Readability: chat text gets ${score.light.contrast}:1 contrast in light mode and ${score.dark.contrast}:1 in dark; it needs ${READING.minContrast}:1 in both. Keep the art in the bottom third, pale by day and dark by night.`)
  }

  if (problems.length > 0) {
    label(repo, issue.number, NEEDS, true)
    comment(repo, issue.number, [
      `Thanks @${author}! A few things to fix before this can join the gallery:`,
      '',
      ...problems.map(p => `- ${p}`),
      '',
      `Edit this issue (the ··· menu, then **Edit**) and the check runs again. The [Submit page](${config.origin}${config.base}submit/) runs the same checks in your browser.`,
    ].join('\n'))
    console.log(problems.join('\n'))
    return
  }

  // Write the theme on its own branch, one per issue, replaced on each edit.
  const branch = `submission/issue-${issue.number}`
  const dir = path.join(ROOT, 'themes', id)
  run('git', ['config', 'user.name', 'github-actions[bot]'])
  run('git', ['config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
  run('git', ['checkout', '-B', branch])
  fs.mkdirSync(dir, { recursive: true })
  fs.writeFileSync(path.join(dir, 'theme.json'), `${JSON.stringify(details, null, 2)}\n`)
  fs.writeFileSync(path.join(dir, 'backdrop.svg'), result.svg)
  run('git', ['add', path.join('themes', id)])
  run('git', ['commit', '-m', `Add theme: ${form.name} (#${issue.number})\n\nCo-authored-by: ${author} <${issue.user.id}+${author}@users.noreply.github.com>`])
  run('git', ['push', '--force', 'origin', branch])

  const site = `${config.origin}${config.base}`
  const scoreLine = score ? `Text contrast: ${score.light.contrast}:1 in light mode, ${score.dark.contrast}:1 in dark.` : 'Readability was not scored (no browser on the runner).'
  const prs = JSON.parse(gh('pr', 'list', '--head', branch, '--state', 'open', '--json', 'number,url'))
  let url = prs[0]?.url
  const prBody = [
    `Adds **${form.name}** by @${author}. Closes #${issue.number}.`,
    '',
    form.description ? `> ${form.description}` : '',
    '',
    `- Passes the gallery rules (${Math.round(result.svg.length / 1000)} KB, ${result.stats.elements} elements)`,
    `- ${scoreLine}`,
    `- Once merged: ${site}t/${id}/ and \`/${config.command} ${id}\``,
    '',
    'Open the SVG in **Files changed** and switch to the rich view to see it.',
  ].join('\n')
  if (url) gh('pr', 'edit', url, '--body', prBody, '--title', `Add theme: ${form.name}`)
  else url = gh('pr', 'create', '--head', branch, '--base', 'main', '--title', `Add theme: ${form.name}`, '--body', prBody)

  label(repo, issue.number, NEEDS, false)
  comment(repo, issue.number, [
    `Thanks @${author}! **${form.name}** passed every check. ${scoreLine}`,
    '',
    `It's in ${url}. Once it's merged it goes live at ${site}t/${id}/ and anyone can use it with \`/${config.command} ${id}\`.`,
  ].join('\n'))
  console.log(`Opened ${url}`)
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error); process.exit(1) })
}
