// Reads every theme in a real browser: readability scores, and a share image for each.
// Drives Chrome over the DevTools protocol with Node's own WebSocket, so it needs no packages.

import { spawn } from 'node:child_process'
import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer } from './serve.mjs'

const CHROMES = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
]
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

class Browser {
  static async launch() {
    const exe = CHROMES.find(p => p && fs.existsSync(p))
    if (!exe) return null
    const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'backdrop-chrome-'))
    const proc = spawn(exe, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--force-color-profile=srgb', '--remote-debugging-port=0', `--user-data-dir=${profile}`, ...(process.env.CI ? ['--no-sandbox'] : []), 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] })
    const endpoint = await new Promise((resolve, reject) => {
      let seen = ''
      const timer = setTimeout(() => reject(new Error('Chrome did not start in time')), 30000)
      proc.stderr.on('data', chunk => {
        seen += chunk
        const found = seen.match(/DevTools listening on (ws:\/\/\S+)/)
        if (found) { clearTimeout(timer); resolve(found[1]) }
      })
      proc.on('exit', code => { clearTimeout(timer); reject(new Error(`Chrome stopped (${code})`)) })
    })
    const browser = new Browser(proc, profile, new WebSocket(endpoint))
    await new Promise((resolve, reject) => { browser.ws.onopen = resolve; browser.ws.onerror = reject })
    return browser
  }

  constructor(proc, profile, ws) {
    this.proc = proc
    this.profile = profile
    this.ws = ws
    this.next = 0
    this.waiting = new Map()
    ws.onmessage = event => {
      const message = JSON.parse(event.data)
      const job = this.waiting.get(message.id)
      if (!job) return
      this.waiting.delete(message.id)
      if (message.error) job.reject(new Error(message.error.message))
      else job.resolve(message.result)
    }
  }

  send(method, params = {}, sessionId) {
    const id = ++this.next
    this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }))
    return new Promise((resolve, reject) => this.waiting.set(id, { resolve, reject }))
  }

  async page(width, height) {
    const { targetId } = await this.send('Target.createTarget', { url: 'about:blank' })
    const { sessionId } = await this.send('Target.attachToTarget', { targetId, flatten: true })
    const send = (method, params) => this.send(method, params, sessionId)
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
    const evaluate = async expression => {
      const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text)
      return r.result.value
    }
    const go = async (url, ready = 'window.ready === true') => {
      await send('Page.navigate', { url })
      const start = Date.now()
      while (Date.now() - start < 30000) {
        try { if (await evaluate(ready)) return } catch {}
        await sleep(80)
      }
      throw new Error(`timed out loading ${url}`)
    }
    return { send, evaluate, go }
  }

  async close() {
    const exited = new Promise(resolve => { if (this.proc.exitCode !== null) resolve(); else this.proc.once('exit', resolve) })
    try { await this.send('Browser.close') } catch {}
    await Promise.race([exited, sleep(5000)])
    this.proc.kill()
    try { fs.rmSync(this.profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }) } catch {}
  }
}

const HERE = path.dirname(fileURLToPath(import.meta.url))
const sha = text => crypto.createHash('sha256').update(text).digest('hex').slice(0, 24)
/** What a cached result depends on besides the theme: the check's code and the share card's page. */
function versions() {
  const read = file => { try { return fs.readFileSync(path.join(HERE, '..', file), 'utf8') } catch { return '' } }
  return {
    score: sha(read('lib/check.mjs') + read('site/assets/readability.js')),
    og: sha(read('site/assets/og.html')),
  }
}

/**
 * Scores each theme and draws its share image into dist/og/. With `cacheDir`, a theme whose
 * file, name and author are unchanged reuses its earlier results, so a build only renders what is new.
 * @returns {Promise<{ scores: Record<string, unknown>, og: string[] } | null>} null without Chrome and nothing cached
 */
export async function render(themes, { dist, base, only, og: drawCards = true, cacheDir } = {}) {
  const list = only ? themes.filter(t => only.includes(t.id)) : themes
  const v = versions()
  const scores = {}
  const og = []
  const keyOf = (kind, t) => sha(kind === 'score' ? `${t.svg}|${v.score}` : `${t.svg}|${t.id}|${t.name}|${t.author ?? ''}|${v.og}`)
  const cachePath = (kind, t, ext) => (cacheDir ? path.join(cacheDir, kind, `${keyOf(kind, t)}.${ext}`) : null)
  const store = (file, data) => { if (file) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, data) } }

  const needScores = []
  for (const t of list) {
    const file = cachePath('score', t, 'json')
    if (file && fs.existsSync(file)) scores[t.id] = JSON.parse(fs.readFileSync(file, 'utf8'))
    else needScores.push(t)
  }
  // The site's own card shows the first theme.
  const cards = drawCards ? [...list, ...(only ? [] : [{ id: 'site', name: '', author: '', svg: themes[0]?.svg ?? '', target: themes[0]?.id ?? '' }])] : []
  const needCards = []
  if (cards.length > 0) fs.mkdirSync(path.join(dist, 'og'), { recursive: true })
  for (const t of cards) {
    const file = cachePath('og', t, 'png')
    if (file && fs.existsSync(file)) { fs.copyFileSync(file, path.join(dist, 'og', `${t.id}.png`)); og.push(t.id) }
    else needCards.push(t)
  }
  const reused = list.length - needScores.length + (cards.length - needCards.length)
  if (needScores.length + needCards.length === 0) {
    console.log(`Readability and share images: all ${reused} reused from the cache.`)
    return { scores, og }
  }

  const browser = await Browser.launch().catch(error => { console.warn(`Skipping the browser checks: ${error.message}`); return null })
  if (!browser) {
    console.warn('No Chrome found: readability scores and share images are skipped.')
    return Object.keys(scores).length + og.length > 0 ? { scores, og } : null
  }
  const server = createServer(dist, base)
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const origin = `http://127.0.0.1:${server.address().port}${base}`
  try {
    if (needScores.length > 0) {
      const measure = await browser.page(800, 600)
      await measure.go(`${origin}assets/measure.html`)
      for (const theme of needScores) {
        scores[theme.id] = await measure.evaluate(`measure(${JSON.stringify(theme.svg)})`)
        store(cachePath('score', theme, 'json'), JSON.stringify(scores[theme.id]))
      }
    }
    if (needCards.length > 0) {
      const card = await browser.page(1200, 630)
      for (const theme of needCards) {
        const target = theme.target ?? theme.id
        await card.go(`${origin}assets/og.html?id=${encodeURIComponent(target)}&title=${encodeURIComponent(theme.id === 'site' ? '' : theme.name)}&author=${encodeURIComponent(theme.author ?? '')}`)
        const { data } = await card.send('Page.captureScreenshot', { format: 'png' })
        const png = Buffer.from(data, 'base64')
        fs.writeFileSync(path.join(dist, 'og', `${theme.id}.png`), png)
        store(cachePath('og', theme, 'png'), png)
        og.push(theme.id)
      }
    }
  } finally {
    server.close()
    await browser.close()
  }
  console.log(`Readability and share images: ${needScores.length + needCards.length} rendered, ${reused} reused from the cache.`)
  return { scores, og }
}

/** Scores one SVG file: `node tools/render.mjs path/to/backdrop.svg` (used by the submission bot). */
export async function scoreFile(svg, { dist, base }) {
  const result = await render([{ id: 'candidate', name: 'candidate', svg }], { dist, base, only: ['candidate'], og: false })
  return result?.scores.candidate ?? null
}
