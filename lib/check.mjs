// The gallery's one rulebook: what a backdrop may hold, and how its looks are read.
// Runs unchanged in Node (the build, the submission bot), in browsers (the Submit
// and Make pages) and inside the loader mod, so every place applies the same rules.

/** The most characters a theme may have. The app draws up to 131072; the rest is headroom. */
export const LIMIT = 120000

/** The most elements a theme may have, so it draws quickly in every window. */
export const MAX_ELEMENTS = 20000

const ELEMENTS = new Set([
  'svg', 'g', 'defs', 'symbol', 'use', 'title', 'desc', 'style',
  'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan',
  'lineargradient', 'radialgradient', 'stop', 'pattern', 'clippath', 'mask', 'image',
  'filter', 'fegaussianblur', 'fecolormatrix', 'fecomposite', 'feblend', 'feoffset', 'feflood',
  'femerge', 'femergenode', 'feturbulence', 'fedisplacementmap', 'fecomponenttransfer',
  'fefuncr', 'fefuncg', 'fefuncb', 'fefunca', 'femorphology',
])
const MOVING = new Set(['animate', 'animatetransform', 'animatemotion', 'animatecolor', 'set'])
const TEXT_HOLDERS = new Set(['style', 'text', 'tspan', 'title', 'desc'])
const IMAGE_DATA = /^data:image\/(png|jpe?g|webp|gif);base64,[a-z0-9+/=\s]+$/i
const ATTRIBUTE = /([^\s=/>"']+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+)))?/g

/** A theme's id: lower-case words joined by dashes. */
export const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

/** Turns a name into an id: "Tokyo at Night!" -> "tokyo-at-night". */
export function slug(text) {
  return String(text).toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40).replace(/-+$/g, '')
}

function cssProblems(css, where) {
  const text = css.toLowerCase().replace(/\/\*[\s\S]*?\*\//g, '')
  const problems = []
  if (/@import|@font-face|@namespace/.test(text)) problems.push(`${where}: @import, @font-face and @namespace are not allowed`)
  if (/expression\s*\(|javascript:|behavior\s*:|-moz-binding/.test(text)) problems.push(`${where}: script-like CSS is not allowed`)
  if (/@keyframes|animation|transition/.test(text)) problems.push(`${where}: themes are still pictures; animation is not allowed`)
  for (const [, target] of text.matchAll(/url\(\s*(['"]?)([^'")]*)\1\s*\)/g)) {
    if (!target.startsWith('#')) problems.push(`${where}: url(${target.slice(0, 40)}) points outside the file; only url(#id) is allowed`)
  }
  return problems
}

/**
 * Reads a theme and says whether the gallery takes it.
 * @param {string} svg the theme file
 * @returns {{ ok: boolean, errors: string[], warnings: string[], svg: string, stats: { chars: number, elements: number, hasDarkMode: boolean } }}
 *   `svg` is the file as the gallery serves it: comments and prolog gone, sized to fill the window.
 */
export function check(svg) {
  const errors = []
  const warnings = []
  const fail = text => { if (errors.length < 25) errors.push(text) }
  let source = typeof svg === 'string' ? svg : ''
  source = source.replace(/^﻿/, '').trim()

  if (source.length === 0) {
    fail('The file is empty.')
    return { ok: false, errors, warnings, svg: '', stats: { chars: 0, elements: 0, hasDarkMode: false } }
  }
  if (/<!DOCTYPE|<!ENTITY/i.test(source)) fail('DOCTYPE and ENTITY declarations are not allowed.')

  // Prolog and comments go; nothing in them is drawn.
  source = source.replace(/^<\?xml[\s\S]*?\?>\s*/i, '').replace(/<!--[\s\S]*?-->/g, '').trim()
  if (/<\?/.test(source)) fail('Processing instructions (<? ... ?>) are not allowed.')

  const stack = []
  let elements = 0
  let root = null
  let at = 0
  while (at < source.length) {
    const open = source.indexOf('<', at)
    const text = source.slice(at, open === -1 ? source.length : open)
    if (text.trim().length > 0) {
      const parent = stack[stack.length - 1]
      if (parent === undefined) fail('There is text outside the <svg> element.')
      else if (!TEXT_HOLDERS.has(parent)) fail(`<${parent}> holds text, which only <text>, <tspan>, <title>, <desc> and <style> may.`)
      else if (parent === 'style') errors.push(...cssProblems(text, '<style>').slice(0, 5))
    }
    if (open === -1) break

    if (source.startsWith('<![CDATA[', open)) {
      const end = source.indexOf(']]>', open)
      if (end === -1) { fail('A CDATA section is never closed.'); break }
      const parent = stack[stack.length - 1]
      if (parent !== 'style') fail('CDATA is only allowed inside <style>.')
      else errors.push(...cssProblems(source.slice(open + 9, end), '<style>').slice(0, 5))
      at = end + 3
      continue
    }

    const close = source.indexOf('>', open)
    if (close === -1) { fail('A tag is never closed.'); break }
    const tag = source.slice(open + 1, close)
    at = close + 1

    if (tag.startsWith('/')) {
      const name = tag.slice(1).trim().toLowerCase()
      const top = stack.pop()
      if (top !== name) { fail(`</${name}> closes <${top ?? 'nothing'}>.`); break }
      continue
    }
    if (tag.startsWith('!')) { fail(`<${tag.slice(0, 20)}> is not allowed.`); continue }

    const isEmpty = tag.endsWith('/')
    const body = isEmpty ? tag.slice(0, -1) : tag
    const name = (body.match(/^[^\s/]+/) ?? [''])[0]
    const lower = name.toLowerCase()
    elements += 1

    if (root === null) {
      root = lower
      if (lower !== 'svg') fail('The file must start with an <svg> element.')
    } else if (stack.length === 0) {
      fail('Everything must sit inside the one <svg> element.')
    }
    if (MOVING.has(lower)) fail(`<${name}> moves; themes are still pictures.`)
    else if (lower === 'script') fail('<script> is not allowed.')
    else if (lower === 'foreignobject') fail('<foreignObject> is not allowed.')
    else if (!ELEMENTS.has(lower)) fail(`<${name}> is not an element themes may use.`)

    for (const [, rawName, a, b, c] of body.slice(name.length).matchAll(ATTRIBUTE)) {
      const attribute = rawName.toLowerCase()
      const value = a ?? b ?? c ?? ''
      if (attribute.startsWith('on')) { fail(`<${name} ${rawName}>: event handlers are not allowed.`); continue }
      if (/javascript:|vbscript:/i.test(value.replace(/[\s\u0000-\u001f]/g, ''))) fail(`<${name} ${rawName}>: script links are not allowed.`)
      if (attribute === 'href' || attribute === 'xlink:href' || attribute.endsWith(':href')) {
        const isLocal = value.startsWith('#')
        const isPicture = lower === 'image' && IMAGE_DATA.test(value)
        if (!isLocal && !isPicture) fail(`<${name} ${rawName}>: links must point inside the file (#id)${lower === 'image' ? ' or be a base64 PNG, JPEG, WebP or GIF' : ''}.`)
      }
      if (attribute === 'style') errors.push(...cssProblems(value, `<${name} style>`).slice(0, 3))
      else if (/url\(/i.test(value)) {
        for (const [, , target] of value.matchAll(/url\(\s*(['"]?)([^'")]*)\1\s*\)/gi)) {
          if (!target.startsWith('#')) fail(`<${name} ${rawName}>: url(${target.slice(0, 40)}) points outside the file.`)
        }
      }
    }
    if (lower === 'svg' && stack.length === 0 && !/\sviewBox\s*=/.test(body)) fail('The <svg> element needs a viewBox, so it can scale to any window.')
    if (!isEmpty) stack.push(lower)
  }
  if (errors.length === 0 && stack.length > 0) fail(`<${stack[stack.length - 1]}> is never closed.`)
  if (elements > MAX_ELEMENTS) fail(`It has ${elements} elements; the most is ${MAX_ELEMENTS}.`)

  const served = errors.length === 0 ? normalize(source) : source
  if (served.length > LIMIT) fail(`It is ${served.length.toLocaleString('en')} characters; the most is ${LIMIT.toLocaleString('en')}.`)

  const hasDarkMode = /prefers-color-scheme\s*:\s*dark/i.test(served) || /light-dark\(/i.test(served)
  if (!hasDarkMode) warnings.push('It has one look for both light and dark mode. That works only if it reads well in both: the check below decides.')
  if (/<image/i.test(served)) warnings.push('It embeds a bitmap. Vector shapes stay sharp at every window size.')

  return { ok: errors.length === 0, errors, warnings, svg: served, stats: { chars: served.length, elements, hasDarkMode } }
}

/** The file as the app should get it: filling the window, see-through around the art. */
export function normalize(svg) {
  let out = svg.replace(/^<\?xml[\s\S]*?\?>\s*/i, '').replace(/<!--[\s\S]*?-->/g, '').trim()
  const end = out.indexOf('>')
  let head = out.slice(0, end)
  const rest = out.slice(end)
  const set = (name, value, replace) => {
    const pattern = new RegExp(`\\s${name}\\s*=\\s*("[^"]*"|'[^']*')`)
    if (pattern.test(head)) { if (replace) head = head.replace(pattern, ` ${name}="${value}"`) }
    else head += ` ${name}="${value}"`
  }
  set('xmlns', 'http://www.w3.org/2000/svg', false)
  set('width', '100%', true)
  set('height', '100%', true)
  set('preserveAspectRatio', 'xMidYMax slice', false)
  out = head + rest
  if (!/color-scheme\s*:\s*light\s+dark/i.test(out)) {
    const open = out.indexOf('>') + 1
    out = `${out.slice(0, open)}<style>:root{color-scheme:light dark}</style>${out.slice(open)}`
  }
  return out
}

/** The theme as one mode sees it: its light/dark switch fixed to `scheme`. */
export function forceScheme(svg, scheme) {
  const yes = '(min-width:0px)'
  const no = '(max-width:0.001px)'
  return svg
    .replace(/\(\s*prefers-color-scheme\s*:\s*(dark|light)\s*\)/gi, (_, mode) => (mode.toLowerCase() === scheme ? yes : no))
    .replace(/color-scheme\s*:\s*light\s+dark/gi, `color-scheme:${scheme}`)
}

/**
 * Checks the details beside a theme file.
 * @returns {string[]} what is wrong, or nothing
 */
export function checkDetails(details) {
  const problems = []
  const d = details ?? {}
  if (typeof d.name !== 'string' || d.name.trim().length === 0 || d.name.length > 40) problems.push('name: 1 to 40 characters')
  if (typeof d.author !== 'string' || !/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$/.test(d.author)) problems.push('author: a GitHub username')
  if (d.description !== undefined && (typeof d.description !== 'string' || d.description.length > 200)) problems.push('description: at most 200 characters')
  if (d.tags !== undefined && (!Array.isArray(d.tags) || d.tags.length > 6 || !d.tags.every(t => typeof t === 'string' && /^[a-z0-9-]{1,20}$/.test(t)))) problems.push('tags: up to 6 lower-case words')
  if (d.added !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(d.added)) problems.push('added: a date, YYYY-MM-DD')
  return problems
}

/** Readability, read from pixels: what the Check and the build both report. */
export const READING = {
  // Where chat text sits in a window, as fractions of its width and height.
  // The chat column: at most 800px wide (72% of a narrow window), centred, above the prompt box.
  zone: { column: 800, share: 0.72, top: 0.05, bottom: 0.82 },
  // The app's text and window colours in each mode (close to Claude's own).
  light: { text: [31, 30, 29], page: [250, 249, 245] },
  dark: { text: [245, 244, 238], page: [38, 38, 36] },
  // The window shapes it is read at.
  sizes: [[1440, 900], [1000, 1000], [1920, 1080]],
  // The least contrast the darkest 1% of the reading zone may have (WCAG AA is 4.5).
  minContrast: 4.5,
}

function channel(v) {
  const c = v / 255
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}
export function luminance([r, g, b]) {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}
export function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

/**
 * Scores the pixels of one rendered window.
 * @param {Uint8ClampedArray} data RGBA pixels
 * @returns {{ contrast: number, busy: number }} the contrast the worst 1% of the reading
 *   zone gives the mode's text, and the share of it that changes sharply from pixel to pixel
 */
export function scorePixels(data, width, height, scheme) {
  const { zone } = READING
  const text = READING[scheme].text
  const textL = luminance(text)
  const column = Math.min(zone.column, width * zone.share)
  const x0 = Math.floor((width - column) / 2)
  const x1 = Math.floor((width + column) / 2)
  const y0 = Math.floor(height * zone.top)
  const y1 = Math.floor(height * zone.bottom)
  const buckets = new Uint32Array(220)
  let count = 0
  let sharp = 0
  const lum = new Float32Array(256)
  for (let i = 0; i < 256; i++) lum[i] = channel(i)
  for (let y = y0; y < y1; y += 2) {
    for (let x = x0; x < x1; x += 2) {
      const i = (y * width + x) * 4
      const L = 0.2126 * lum[data[i]] + 0.7152 * lum[data[i + 1]] + 0.0722 * lum[data[i + 2]]
      const ratio = (Math.max(L, textL) + 0.05) / (Math.min(L, textL) + 0.05)
      buckets[Math.min(219, Math.floor(ratio * 10))] += 1
      const j = i + 4
      const R = 0.2126 * lum[data[j]] + 0.7152 * lum[data[j + 1]] + 0.0722 * lum[data[j + 2]]
      if (Math.abs(Math.sqrt(L) - Math.sqrt(R)) > 0.09) sharp += 1
      count += 1
    }
  }
  let seen = 0
  let worst = 21
  for (let b = 0; b < buckets.length; b++) {
    seen += buckets[b]
    if (seen >= count * 0.01) { worst = b / 10; break }
  }
  return { contrast: Math.round(worst * 10) / 10, busy: Math.round((sharp / Math.max(1, count)) * 1000) / 1000 }
}
