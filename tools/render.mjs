// Reads every theme in a real browser: readability scores, and a share image for each.
// Drives Chrome over the DevTools protocol with Node's own WebSocket, so it needs no packages.

import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
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

/**
 * Scores each theme and draws its share image into dist/og/.
 * @returns {Promise<{ scores: Record<string, unknown>, og: string[] } | null>} null without Chrome
 */
export async function render(themes, { dist, base, only, og: drawCards = true } = {}) {
  const browser = await Browser.launch().catch(error => { console.warn(`Skipping the browser checks: ${error.message}`); return null })
  if (!browser) { console.warn('No Chrome found: readability scores and share images are skipped.'); return null }
  const server = createServer(dist, base)
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const origin = `http://127.0.0.1:${server.address().port}${base}`
  const scores = {}
  const og = []
  try {
    const measure = await browser.page(800, 600)
    await measure.go(`${origin}assets/measure.html`)
    for (const theme of themes) {
      if (only && !only.includes(theme.id)) continue
      scores[theme.id] = await measure.evaluate(`measure(${JSON.stringify(theme.svg)})`)
    }
    if (!drawCards) return { scores, og }
    const card = await browser.page(1200, 630)
    fs.mkdirSync(path.join(dist, 'og'), { recursive: true })
    for (const theme of [...themes, { id: 'site', name: '' }]) {
      if (only && !only.includes(theme.id)) continue
      const target = theme.id === 'site' ? (themes[0]?.id ?? '') : theme.id
      await card.go(`${origin}assets/og.html?id=${encodeURIComponent(target)}&title=${encodeURIComponent(theme.id === 'site' ? '' : theme.name)}&author=${encodeURIComponent(theme.author ?? '')}`)
      const { data } = await card.send('Page.captureScreenshot', { format: 'png' })
      fs.writeFileSync(path.join(dist, 'og', `${theme.id}.png`), Buffer.from(data, 'base64'))
      og.push(theme.id)
    }
  } finally {
    server.close()
    await browser.close()
  }
  return { scores, og }
}

/** Scores one SVG file: `node tools/render.mjs path/to/backdrop.svg` (used by the submission bot). */
export async function scoreFile(svg, { dist, base }) {
  const result = await render([{ id: 'candidate', name: 'candidate', svg }], { dist, base, only: ['candidate'], og: false })
  return result?.scores.candidate ?? null
}
