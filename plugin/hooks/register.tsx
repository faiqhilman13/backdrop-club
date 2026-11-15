import type { EngineInterface, Register } from 'claude-code'
import { check } from './check.js'
import { DEFAULT } from './default.js'

// The gallery this loader draws from. Every theme there passed the same check this mod runs.
const SITE = 'https://faiqhilman13.github.io/backdrop-club/'
// The backdrop's name to the app: one name, whichever theme is showing.
const NAME = 'backdrop-club'
const COMMAND = 'backdrop'
// Kept across sessions: the picked theme, and whether the person turned backdrops off.
const KEPT = 'theme'
const OFF = 'off'
// How opaque the app's panels are over the backdrop.
const VEIL = 0.6

type Theme = { id: string; name: string; author: string; svg: string }
type Listed = { id: string; name: string; author: string; tags: string[] }

let shown: Theme = DEFAULT
let isOff = false
// Whether a window has said it draws the backdrop, and how often it has drawn it since it was named.
let isDrawn = false
let drawnSinceSet = 0

function isTheme(value: unknown): value is Theme {
  const v = value as Partial<Theme> | null | undefined
  return typeof v?.id === 'string' && typeof v.name === 'string' && typeof v.author === 'string' && typeof v.svg === 'string'
}

function key(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '')
}

/** Reads the person's pick, from this session or another. Answers whether what shows changed. */
async function readKept($: EngineInterface) {
  const was = { id: shown.id, svg: shown.svg, isOff }
  try {
    const kept = await $.store.get(KEPT)
    shown = isTheme(kept) && check(kept.svg).ok ? kept : DEFAULT
    isOff = (await $.store.get(OFF)) === true
  } catch {
    // An unreadable store is no pick: the default shows.
  }
  return was.id !== shown.id || was.svg !== shown.svg || was.isOff !== isOff
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

async function fetchJson($: EngineInterface, path: string): Promise<unknown> {
  const response = await $.http.fetch(`${SITE}${path}`)
  if (response.status === 404) return undefined
  if (!response.ok) throw new Error(`the gallery answered ${response.status}`)
  return JSON.parse(response.text)
}

async function gallery($: EngineInterface): Promise<Listed[]> {
  const data = (await fetchJson($, 'api/index.json')) as { themes?: unknown } | undefined
  return Array.isArray(data?.themes) ? (data.themes as Listed[]).filter(t => typeof t?.id === 'string' && typeof t.name === 'string') : []
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
  const data = await fetchJson($, `api/themes/${encodeURIComponent(listed.id)}.json`)
  if (!isTheme(data)) return `${listed.name} could not be fetched from the gallery. Your backdrop stays as it was.`
  const result = check(data.svg)
  if (!result.ok) return `${listed.name} was refused: ${result.errors[0]} Your backdrop stays as it was.`
  const wasOff = isOff
  shown = { id: data.id, name: data.name, author: data.author, svg: result.svg }
  isOff = false
  await $.store.set(KEPT, shown)
  await $.store.delete(OFF)
  if (wasOff || !isDrawn) await name($)
  $.ui.invalidate('ui.render')
  return `Now showing ${shown.name} by @${shown.author}. It follows light and dark mode, and stays across sessions.`
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
    await readKept($)
    await name($)
    try {
      await $.command.register({ name: COMMAND, description: 'Pick a backdrop from the Backdrop Club gallery', argumentHint: '[name | random | list | off | on]' })
    } catch {
      // Another mod may hold the name; the backdrop still shows.
    }
    return next(e)
  })

  // A window that was not there at the start may attach later: name the backdrop again until one draws it.
  on('prompt.submit', async ($, e, next) => {
    const changed = await readKept($)
    if (!isOff && !isDrawn && drawnSinceSet === 0) await name($)
    else if (changed) $.ui.invalidate('ui.render')
    return next(e)
  })

  on('ui.render', { component: 'Backdrop' }, async ($, e, next) => {
    const asked: { scene?: unknown; id?: unknown } = e.props
    const scene = typeof asked.scene === 'string' ? asked.scene : asked.id
    if (scene !== NAME || isOff || (e.surface !== 'desktop' && e.surface !== 'mobile')) return next(e)
    const { Svg } = $.ui.resolve(e)
    drawnSinceSet += 1
    return <Svg source={shown.svg} alt={`${shown.name}, a backdrop by @${shown.author}`} isInteractive />
  })

  on('command.run', { command: COMMAND }, async ($, e) => {
    const args = e.args.trim()
    const [word = '', ...rest] = args.split(/\s+/)
    const verb = word.toLowerCase()

    if (verb === '' || verb === 'help') {
      return { text: `${isOff ? 'Backdrops are off.' : `Showing ${shown.name} by @${shown.author}.`}\n${HELP}` }
    }
    if (verb === 'off') {
      isOff = true
      await $.store.set(OFF, true)
      try { await $.theme.clear() } catch {}
      return { text: `Backdrop off. /${COMMAND} on brings ${shown.name} back.` }
    }
    if (verb === 'on') {
      isOff = false
      await $.store.delete(OFF)
      await name($)
      $.ui.invalidate('ui.render')
      return { text: `Showing ${shown.name} by @${shown.author}.` }
    }
    if (verb === 'default' || verb === 'reset') {
      shown = DEFAULT
      isOff = false
      await $.store.delete(KEPT)
      await $.store.delete(OFF)
      await name($)
      $.ui.invalidate('ui.render')
      return { text: `Back to ${DEFAULT.name}.` }
    }

    let list: Listed[]
    try {
      list = await gallery($)
    } catch (error) {
      return { text: `Couldn't reach the gallery (${error instanceof Error ? error.message : String(error)}). Your backdrop stays as it was.` }
    }
    if (list.length === 0) return { text: `The gallery didn't answer with any themes. Your backdrop stays as it was.\nBrowse: ${SITE}` }

    if (verb === 'list') {
      const tag = rest.join(' ').toLowerCase()
      const picked = tag ? list.filter(t => Array.isArray(t.tags) && t.tags.includes(tag)) : list
      if (picked.length === 0) return { text: `No themes tagged "${tag}" yet. Browse: ${SITE}` }
      const lines = picked.slice(0, 60).map(t => `${t.id === shown.id ? '* ' : '  '}${t.id}  (${t.name} by @${t.author})`)
      const more = picked.length > 60 ? `\n…and ${picked.length - 60} more at ${SITE}` : ''
      return { text: `${picked.length} theme${picked.length === 1 ? '' : 's'}${tag ? ` tagged ${tag}` : ''}. Pick one with /${COMMAND} <name>.\n${lines.join('\n')}${more}` }
    }

    try {
      if (verb === 'random' || verb === 'surprise') {
        const others = list.filter(t => t.id !== shown.id)
        const pick = others[Math.floor(Math.random() * others.length)] ?? list[0]!
        return { text: await use($, pick) }
      }
      const found = findIn(list, args)
      if (!found) return { text: `No theme called "${args}" yet. Try /${COMMAND} list, or browse ${SITE}` }
      return { text: await use($, found) }
    } catch (error) {
      return { text: `Couldn't fetch that theme (${error instanceof Error ? error.message : String(error)}). Your backdrop stays as it was.` }
    }
  })
}
