import type { EngineInterface, Register } from 'claude-code'
import { check } from './check.js'
import { DEFAULT } from './default.js'
import { SITE } from './site.js'

// The gallery's API. Every theme there passed the same check this mod runs.
const API = `${SITE}api/v1/`
// How often a session asks the gallery whether the picked theme changed or was taken down.
const CHECK_EVERY_MS = 6 * 60 * 60 * 1000
const CHECKED = 'checkedAt'
// The backdrop's name to the app: one name, whichever theme is showing.
const NAME = 'backdrop-club'
const COMMAND = 'backdrop'
// Kept across sessions in the mod's store, as a fallback for the pick file.
const KEPT = 'theme'
const OFF = 'off'
// How opaque the app's panels are over the backdrop.
const VEIL = 0.6
// How often an open session looks for a pick made elsewhere (the CLI, another session).
const POLL_MS = 3000
// The model's two tools, as the engine names them (a pattern, so the matcher types check).
const TOOLS = { find: /^mcp__backdrop-club__find_backdrops$/, set: /^mcp__backdrop-club__set_backdrop$/ }

type Theme = { id: string; name: string; author: string; svg: string; hash?: string }
type Listed = { id: string; name: string; author: string; description?: string; tags?: string[]; hash?: string }
type Gallery = { themes: Listed[]; revoked: string[] }

let shown: Theme = DEFAULT
let isOff = false
// Whether a window has said it draws the backdrop, and how often it has drawn it since it was named.
let isDrawn = false
let drawnSinceSet = 0
// The pick file every session and the CLI share, and when it last changed.
let pickPath: string | undefined
let pickStamp = -1
let poller: { cancel: () => void } | undefined

function isTheme(value: unknown): value is Theme {
  const v = value as Partial<Theme> | null | undefined
  return typeof v?.id === 'string' && typeof v.name === 'string' && typeof v.author === 'string' && typeof v.svg === 'string'
}

function key(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

/** ~/.config/backdrop-club/current.json, or under $XDG_CONFIG_HOME: where the CLI writes a pick. */
async function locatePick($: EngineInterface) {
  if (pickPath !== undefined) return pickPath
  try {
    const xdg = await $.env.get('XDG_CONFIG_HOME')
    const home = (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE'))
    const base = xdg || (home ? `${home}/.config` : undefined)
    pickPath = base ? `${base}/backdrop-club/current.json` : ''
  } catch {
    pickPath = ''
  }
  return pickPath
}

/** Reads the pick: the shared file first, then this mod's store. Answers whether what shows changed. */
async function readPick($: EngineInterface) {
  const was = { id: shown.id, svg: shown.svg, isOff }
  let next: Theme | undefined
  let off = false
  let found = false
  const file = await locatePick($)
  if (file) {
    try {
      const pick = JSON.parse(await $.fs.read(file)) as Partial<Theme> & { off?: boolean }
      found = true
      off = pick.off === true
      if (isTheme(pick) && check(pick.svg).ok) next = { id: pick.id, name: pick.name, author: pick.author, svg: check(pick.svg).svg, hash: typeof pick.hash === 'string' ? pick.hash : undefined }
    } catch {
      // No file yet, or one this mod can't read: the store decides.
    }
  }
  if (!found) {
    try {
      const kept = await $.store.get(KEPT)
      if (isTheme(kept) && check(kept.svg).ok) next = kept
      off = (await $.store.get(OFF)) === true
    } catch {
      // An unreadable store is no pick.
    }
  }
  shown = next ?? DEFAULT
  isOff = off
  return { changed: was.id !== shown.id || was.svg !== shown.svg || was.isOff !== isOff, wasOff: was.isOff }
}

/** Keeps a pick in the shared file (for the CLI and other sessions) and in the store. */
async function savePick($: EngineInterface) {
  const file = await locatePick($)
  try {
    if (file) await $.fs.write(file, JSON.stringify({ ...shown, off: isOff, at: new Date(await $.clock.now()).toISOString() }))
  } catch {
    // The store still has it.
  }
  try {
    await $.store.set(KEPT, shown)
    if (isOff) await $.store.set(OFF, true)
    else await $.store.delete(OFF)
  } catch {
    // The file still has it.
  }
  pickStamp = await stamp($)
}

async function stamp($: EngineInterface) {
  const file = await locatePick($)
  if (!file) return -1
  try {
    return (await $.fs.stat(file)).mtimeMs
  } catch {
    return -1
  }
}

/** Names the session's backdrop. No colours of its own: the app keeps its light and dark looks. */
async function name($: EngineInterface) {
  if (isOff) return
  try {
    // Sent as `scene` for newer windows and `id` for older ones, as the app's own examples do.
    const backdrop = { scene: NAME, id: NAME, glass: { blur: 0, opacity: VEIL } }
    drawnSinceSet = 0
    const set = await $.theme.set({ backdrop })
    isDrawn = set.isDrawn
  } catch {
    // Without a theme there is nothing to draw; the chat goes on as it was.
  }
}

/** Shows what the pick now says: draws the new theme, or clears or restores the backdrop. */
async function apply($: EngineInterface, wasOff: boolean) {
  if (isOff) {
    try { await $.theme.clear() } catch {}
    return
  }
  if (wasOff || !isDrawn) await name($)
  $.ui.invalidate('ui.render')
}

/** Picks up a change made elsewhere: the CLI, an agent, or another session. */
async function follow($: EngineInterface) {
  const now = await stamp($)
  if (now === pickStamp) return
  pickStamp = now
  const { changed, wasOff } = await readPick($)
  if (changed) await apply($, wasOff)
}

async function fetchJson($: EngineInterface, path: string): Promise<unknown> {
  const response = await $.http.fetch(`${API}${path}`)
  if (response.status === 404) return undefined
  if (!response.ok) throw new Error(`the gallery answered ${response.status}`)
  return JSON.parse(response.text)
}

async function catalog($: EngineInterface): Promise<Gallery> {
  const data = (await fetchJson($, 'index.json')) as { themes?: unknown; revoked?: unknown } | undefined
  const themes = Array.isArray(data?.themes) ? (data.themes as Listed[]).filter(t => typeof t?.id === 'string' && typeof t.name === 'string') : []
  const revoked = Array.isArray(data?.revoked) ? (data.revoked as unknown[]).filter((id): id is string => typeof id === 'string') : []
  return { themes, revoked }
}

async function gallery($: EngineInterface): Promise<Listed[]> {
  return (await catalog($)).themes
}

function findIn(list: Listed[], asked: string) {
  const k = key(asked)
  if (k === '') return undefined
  return list.find(t => key(t.id) === k || key(t.name) === k)
    ?? list.find(t => key(t.id).startsWith(k) || key(t.name).startsWith(k))
    ?? list.find(t => key(t.name).includes(k))
}

/** Fetches a theme, checks it, and shows it. Answers what to tell the person. */
async function use($: EngineInterface, listed: Listed) {
  const data = await fetchJson($, `themes/${encodeURIComponent(listed.id)}.json`)
  if (!isTheme(data)) return `${listed.name} could not be fetched from the gallery. The backdrop stays as it was.`
  const result = check(data.svg)
  if (!result.ok) return `${listed.name} was refused: ${result.errors[0]} The backdrop stays as it was.`
  const wasOff = isOff
  shown = { id: data.id, name: data.name, author: data.author, svg: result.svg, hash: typeof (data as { hash?: unknown }).hash === 'string' ? (data as { hash: string }).hash : undefined }
  isOff = false
  await savePick($)
  await apply($, wasOff)
  return `Now showing ${shown.name} by @${shown.author}. It follows light and dark mode, and stays across sessions.`
}

/** One answer for the slash command and the model's tool alike. */
async function pick($: EngineInterface, asked: string) {
  const [word = ''] = asked.split(/\s+/)
  const verb = word.toLowerCase()
  if (verb === 'off') {
    isOff = true
    await savePick($)
    try { await $.theme.clear() } catch {}
    return `Backdrop off. /${COMMAND} on brings ${shown.name} back.`
  }
  if (verb === 'on') {
    isOff = false
    await savePick($)
    await name($)
    $.ui.invalidate('ui.render')
    return `Showing ${shown.name} by @${shown.author}.`
  }
  if (verb === 'default' || verb === 'reset') {
    const wasOff = isOff
    shown = DEFAULT
    isOff = false
    await savePick($)
    await apply($, wasOff)
    return `Back to ${DEFAULT.name}.`
  }
  let list: Listed[]
  try {
    list = await gallery($)
  } catch (error) {
    return `Couldn't reach the gallery (${error instanceof Error ? error.message : String(error)}). The backdrop stays as it was.`
  }
  if (list.length === 0) return `The gallery didn't answer with any themes. The backdrop stays as it was.\nBrowse: ${SITE}`
  try {
    if (verb === 'random' || verb === 'surprise') {
      const others = list.filter(t => t.id !== shown.id)
      return await use($, others[Math.floor(Math.random() * others.length)] ?? list[0]!)
    }
    const found = findIn(list, asked)
    if (!found) return `No theme called "${asked}" yet. Try /${COMMAND} list, or browse ${SITE}`
    return await use($, found)
  } catch (error) {
    return `Couldn't fetch that theme (${error instanceof Error ? error.message : String(error)}). The backdrop stays as it was.`
  }
}

/**
 * Keeps the picked theme current: fetches it again when its author updated it, and drops it when
 * the gallery took it down. At most every few hours, and never in the way of the session starting.
 */
async function checkForUpdates($: EngineInterface) {
  if (shown.id === DEFAULT.id && shown.svg === DEFAULT.svg) return
  try {
    const now = await $.clock.now()
    const last = await $.store.get(CHECKED)
    if (typeof last === 'number' && now - last < CHECK_EVERY_MS) return
    await $.store.set(CHECKED, now)
    const { themes, revoked } = await catalog($)
    if (revoked.includes(shown.id)) {
      const gone = shown.name
      const wasOff = isOff
      shown = DEFAULT
      await savePick($)
      await apply($, wasOff)
      $.ui.toast(`${gone} was taken down from the gallery, so the backdrop is back to ${DEFAULT.name}.`)
      return
    }
    const listed = themes.find(t => t.id === shown.id)
    if (listed?.hash && listed.hash !== shown.hash) await use($, listed)
  } catch {
    // Offline or the gallery is down: the copy on this machine stays.
  }
}

function describe(t: Listed) {
  const tags = (t.tags ?? []).filter(x => x !== 'dither')
  return `${t.id}: ${t.name} by @${t.author}${tags.length ? ` [${tags.join(', ')}]` : ''}${t.description ? ` - ${t.description}` : ''} (preview ${SITE}og/${t.id}.png)`
}

const HELP = [
  `/${COMMAND} <name>   switch to a theme from the gallery`,
  `/${COMMAND} random   a surprise`,
  `/${COMMAND} list [tag]   what the gallery has`,
  `/${COMMAND} off | on   hide the backdrop, or bring it back`,
  `Browse them all: ${SITE}`,
].join('\n')

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await readPick($)
    pickStamp = await stamp($)
    await name($)
    try {
      await $.command.register({ name: COMMAND, description: 'Pick a backdrop from the Backdrop Club gallery', argumentHint: '[name | random | list | off | on]' })
    } catch {
      // Another mod may hold the name; the backdrop still shows.
    }
    try {
      await $.tool.register({
        name: 'find_backdrops',
        description: 'Lists backdrop themes for the Claude desktop app from the Backdrop Club gallery: pixel-art cities and landscapes drawn behind the chat, each with a light and a dark look. Use it when the person asks about backdrops, themes, wallpapers or the app\'s background. Returns each theme\'s id, name, author, tags and a preview image link, and what is showing now. Show the person the options and let them choose.',
        inputSchema: { type: 'object', properties: { query: { type: 'string', description: 'Words to match in names, tags, descriptions or authors, such as "mountains" or "japan". Leave it out to list every theme.' } } },
      })
      await $.tool.register({
        name: 'set_backdrop',
        description: 'Shows a Backdrop Club theme behind the chat in the Claude desktop app, by its id or name from find_backdrops; or "random", "off" to hide the backdrop, "on" to bring it back, "default". Only use a theme the person chose or asked for.',
        inputSchema: { type: 'object', properties: { theme: { type: 'string', description: 'A theme id or name, or random, off, on, default.' } }, required: ['theme'] },
      })
    } catch {
      // Without the tools, the slash command and the CLI still work.
    }
    poller?.cancel()
    poller = $.clock.every(POLL_MS, () => { void follow($) })
    $.clock.after(1500, () => { void checkForUpdates($) })
    return next(e)
  })

  // A window that was not there at the start may attach later: name the backdrop again until one draws it.
  on('prompt.submit', async ($, e, next) => {
    const { changed, wasOff } = await readPick($)
    pickStamp = await stamp($)
    if (!isOff && !isDrawn && drawnSinceSet === 0) await name($)
    else if (changed) await apply($, wasOff)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Backdrop' }, async ($, e, next) => {
    const asked: { scene?: unknown; id?: unknown } = e.props
    const scene = typeof asked.scene === 'string' ? asked.scene : asked.id
    if (scene !== NAME || isOff || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    drawnSinceSet += 1
    return <Svg source={shown.svg} alt={`${shown.name}, a backdrop by @${shown.author}`} isInteractive />
  })

  on('tool.call', { tool: TOOLS.find }, async ($, e) => {
    const query = String((e as unknown as { query?: unknown }).query ?? '').toLowerCase().trim()
    let list: Listed[]
    try {
      list = await gallery($)
    } catch (error) {
      return { result: `Couldn't reach the gallery (${error instanceof Error ? error.message : String(error)}). Browse it at ${SITE}` }
    }
    const terms = query.split(/\s+/).filter(Boolean)
    const picked = list.filter(t => {
      const hay = `${t.id} ${t.name} ${t.author} ${t.description ?? ''} ${(t.tags ?? []).join(' ')}`.toLowerCase()
      return terms.every(w => hay.includes(w))
    })
    const now = isOff ? `The backdrop is off (last: ${shown.name}).` : `Showing now: ${shown.name} (${shown.id}).`
    const body = picked.length > 0 ? picked.slice(0, 80).map(describe).join('\n') : `Nothing matches "${query}". There are ${list.length} themes in all.`
    return { result: `${now}\n${picked.length} theme${picked.length === 1 ? '' : 's'}${query ? ` matching "${query}"` : ''}:\n${body}\nGallery: ${SITE}` }
  }).catch(() => ({ result: `The backdrop gallery couldn't be read just now. Browse it at ${SITE}` }))

  on('tool.call', { tool: TOOLS.set }, async ($, e) => {
    const theme = String((e as unknown as { theme?: unknown }).theme ?? '').trim()
    if (!theme) return { result: 'Say which theme: an id or name from find_backdrops, or random, off, on.' }
    return { result: await pick($, theme) }
  }).catch(() => ({ result: 'Setting the backdrop failed; it stays as it was. The person can also type /backdrop <name>.' }))

  on('command.run', { command: COMMAND }, async ($, e) => {
    const args = e.args.trim()
    const [word = '', ...rest] = args.split(/\s+/)
    const verb = word.toLowerCase()

    if (verb === '' || verb === 'help') {
      return { text: `${isOff ? 'Backdrops are off.' : `Showing ${shown.name} by @${shown.author}.`}\n${HELP}` }
    }
    if (verb === 'list') {
      let list: Listed[]
      try {
        list = await gallery($)
      } catch (error) {
        return { text: `Couldn't reach the gallery (${error instanceof Error ? error.message : String(error)}).` }
      }
      const tag = rest.join(' ').toLowerCase()
      const picked = tag ? list.filter(t => Array.isArray(t.tags) && t.tags.includes(tag)) : list
      if (picked.length === 0) return { text: `No themes tagged "${tag}" yet. Browse: ${SITE}` }
      const lines = picked.slice(0, 60).map(t => `${t.id === shown.id ? '* ' : '  '}${t.id}  (${t.name} by @${t.author})`)
      const more = picked.length > 60 ? `\n…and ${picked.length - 60} more at ${SITE}` : ''
      return { text: `${picked.length} theme${picked.length === 1 ? '' : 's'}${tag ? ` tagged ${tag}` : ''}. Pick one with /${COMMAND} <name>.\n${lines.join('\n')}${more}` }
    }
    return { text: await pick($, args) }
  }).catch(() => ({ text: 'The backdrop command failed; the backdrop stays as it was.' }))
}
