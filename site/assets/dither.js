// Turns a picture into a backdrop: chunky ordered-dither pixels along the window's foot,
// one look for light mode and one for dark, in a single small SVG.

export const W = 512
export const H = 160
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16)
const bayer = (x, y) => BAYER[(y & 3) * 4 + (x & 3)]

export const PAGE = { day: '#f5f2ea', night: '#0b0c14' }

/** Colour sets for the Silhouette style: sky from top to horizon, the land, night lights. */
export const PALETTES = {
  dawn: { label: 'Dawn', day: { sky: ['#f5f2ea', '#f8e1d6', '#f4c3b6'], land: '#a8cac4', far: '#c9dcd3' }, night: { sky: ['#0b0c14', '#171428', '#34204a'], land: '#05060b', far: '#11131f', lights: '#ffcf6b' } },
  aurora: { label: 'Aurora', day: { sky: ['#f5f2ea', '#e2f1e8', '#c4e6d8'], land: '#a9bad9', far: '#cdd6e8' }, night: { sky: ['#0b0c14', '#0d2426', '#1b5446'], land: '#040509', far: '#0e1720', lights: '#7cf2c8' } },
  dusk: { label: 'Dusk', day: { sky: ['#f5f2ea', '#efe2f4', '#dcc8ef'], land: '#b9a9da', far: '#d8cdec' }, night: { sky: ['#0b0c14', '#190f2e', '#3a1c4c'], land: '#06040c', far: '#140e22', lights: '#ff9ad5' } },
  desert: { label: 'Desert', day: { sky: ['#f5f2ea', '#f8e6c9', '#f2cba0'], land: '#dcae84', far: '#ead0b2' }, night: { sky: ['#0b0c14', '#1f130f', '#472517'], land: '#0a0605', far: '#1b110c', lights: '#ffb36b' } },
  sea: { label: 'Sea', day: { sky: ['#f5f2ea', '#dfeef3', '#bfdeea'], land: '#9fbfd0', far: '#c6dbe5' }, night: { sky: ['#0b0c14', '#0b1a2a', '#123a55'], land: '#03060b', far: '#0b1522', lights: '#9fd8ff' } },
}

// ---------- colour helpers ----------
const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16))
const toHex = rgb => `#${rgb.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('')}`
function lin(v) { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4 }
const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
function rgbToHsl([r, g, b]) {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b); const min = Math.min(r, g, b); const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4
  return [h / 6, s, l]
}
function hslToRgb([h, s, l]) {
  if (s === 0) return [l * 255, l * 255, l * 255]
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  const f = t => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p }
  return [f(h + 1 / 3) * 255, f(h) * 255, f(h - 1 / 3) * 255]
}
/** Pale and soft, so dark text keeps at least 7:1 over it. */
function pastel(rgb) {
  let [h, s, l] = rgbToHsl(rgb)
  s = Math.min(s, 0.5) * 0.85
  l = 0.68 + l * 0.22
  let out = hslToRgb([h, s, l])
  for (let i = 0; i < 20 && lum(out) < 0.42; i++) { l = Math.min(0.97, l + 0.02); out = hslToRgb([h, s, l]) }
  return out
}
/** Deep and quiet, so light text keeps its contrast; `accent` lets one colour stay brighter. */
function deep(rgb, accent) {
  let [h, s, l] = rgbToHsl(rgb)
  if (accent) return hslToRgb([h, Math.min(1, s * 1.1 + 0.15), 0.5 + l * 0.15])
  s = Math.min(s, 0.6)
  l = 0.04 + l * 0.16
  let out = hslToRgb([h, s, l])
  for (let i = 0; i < 20 && lum(out) > 0.035; i++) { l = Math.max(0.01, l - 0.01); out = hslToRgb([h, s, l]) }
  return out
}

/** A few colours that stand for the picture: k-means on its pixels. */
function quantize(pixels, k) {
  const n = pixels.length / 4
  const pts = []
  for (let i = 0; i < n; i++) pts.push([pixels[i * 4], pixels[i * 4 + 1], pixels[i * 4 + 2]])
  pts.sort((a, b) => lum(a) - lum(b))
  let centres = Array.from({ length: k }, (_, i) => pts[Math.floor(((i + 0.5) / k) * (n - 1))].slice())
  const owner = new Uint8Array(n)
  for (let round = 0; round < 12; round++) {
    const sums = centres.map(() => [0, 0, 0, 0])
    for (let i = 0; i < n; i++) {
      let best = 0; let bestD = Infinity
      for (let c = 0; c < k; c++) {
        const d = (pts[i][0] - centres[c][0]) ** 2 + (pts[i][1] - centres[c][1]) ** 2 + (pts[i][2] - centres[c][2]) ** 2
        if (d < bestD) { bestD = d; best = c }
      }
      owner[i] = best
      const s = sums[best]; s[0] += pts[i][0]; s[1] += pts[i][1]; s[2] += pts[i][2]; s[3] += 1
    }
    centres = centres.map((c, i) => sums[i][3] ? [sums[i][0] / sums[i][3], sums[i][1] / sums[i][3], sums[i][2] / sums[i][3]] : c)
  }
  return centres.sort((a, b) => lum(a) - lum(b))
}

/** Picks between the two nearest colours per pixel, by the ordered-dither threshold. */
function ditherTo(rgb, palette, x, y) {
  let a = 0; let b = 1; let da = Infinity; let db = Infinity
  for (let i = 0; i < palette.length; i++) {
    const p = palette[i]
    const d = (rgb[0] - p[0]) ** 2 + (rgb[1] - p[1]) ** 2 + (rgb[2] - p[2]) ** 2
    if (d < da) { db = da; b = a; da = d; a = i } else if (d < db) { db = d; b = i }
  }
  const pa = palette[a]; const pb = palette[b]
  const seg = [pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]]
  const len = seg[0] ** 2 + seg[1] ** 2 + seg[2] ** 2
  const t = len === 0 ? 0 : Math.max(0, Math.min(1, ((rgb[0] - pa[0]) * seg[0] + (rgb[1] - pa[1]) * seg[1] + (rgb[2] - pa[2]) * seg[2]) / len))
  return t > bayer(x, y) ? b : a
}

/** The pixels of `image` that fill a cols-by-rows strip, cropped like CSS cover, with `focus` 0 (top) to 1 (bottom). */
export function sample(image, cols, rows, focus) {
  const canvas = document.createElement('canvas')
  canvas.width = cols
  canvas.height = rows
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  const iw = image.naturalWidth || image.width
  const ih = image.naturalHeight || image.height
  const scale = Math.max(cols / iw, rows / ih)
  const sw = cols / scale
  const sh = rows / scale
  const sx = (iw - sw) / 2
  const sy = (ih - sh) * focus
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(image, sx, sy, sw, sh, 0, 0, cols, rows)
  return ctx.getImageData(0, 0, cols, rows).data
}

/** Otsu's threshold over the picture's lightness: where its land and sky part. */
export function autoCut(pixels) {
  const hist = new Array(256).fill(0)
  for (let i = 0; i < pixels.length; i += 4) hist[Math.round(lum([pixels[i], pixels[i + 1], pixels[i + 2]]) ** (1 / 2.2) * 255)] += 1
  const total = pixels.length / 4
  let sum = 0; for (let i = 0; i < 256; i++) sum += i * hist[i]
  let sumB = 0; let wB = 0; let best = 0; let cut = 128
  for (let i = 0; i < 256; i++) {
    wB += hist[i]; if (!wB) continue
    const wF = total - wB; if (!wF) break
    sumB += i * hist[i]
    const between = wB * wF * (sumB / wB - (sum - sumB) / wF) ** 2
    if (between > best) { best = between; cut = i }
  }
  return Math.round((cut / 255) * 100)
}

function rand(seed) {
  let s = seed >>> 0
  return () => { s = (s + 0x6d2b79f5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
}

/**
 * Makes the backdrop.
 * @param {Uint8ClampedArray} pixels from `sample`
 * @param {{ cols: number, rows: number, mode: 'silhouette' | 'photo', palette: string, cut: number, stars: boolean, lights: boolean }} o
 * @returns {{ svg: string, colours: number }}
 */
export function makeBackdrop(pixels, o) {
  const { cols, rows } = o
  const s = W / cols
  const top = H - rows * s
  const fade = Math.max(2, Math.round(rows * 0.28))
  const index = new Uint8Array(cols * rows) // 0 is the page
  let dayInks
  let nightInks
  const nightOnly = []
  const random = rand(cols * 7919 + rows * 104729 + Math.round(o.cut * 31))
  // Bright colours stay below the line where chat text ends (the prompt box sits there).
  const low = Math.ceil((134 - top) / s)

  if (o.mode === 'silhouette') {
    const p = PALETTES[o.palette] ?? PALETTES.dawn
    // Inks: 1..3 sky bands (index 1 = page-ish top sky), 4 far land, 5 land.
    dayInks = [p.day.sky[0], p.day.sky[1], p.day.sky[2], p.day.far, p.day.land]
    nightInks = [p.night.sky[0], p.night.sky[1], p.night.sky[2], p.night.far, p.night.land]
    const cut = o.cut / 100
    const land = new Int16Array(cols).fill(rows)
    const far = new Int16Array(cols).fill(rows)
    for (let x = 0; x < cols; x++) {
      for (let y = 0; y < rows; y++) {
        const i = (y * cols + x) * 4
        const l = lum([pixels[i], pixels[i + 1], pixels[i + 2]]) ** (1 / 2.2)
        if (l < cut) { land[x] = y; break }
      }
      for (let y = 0; y < rows; y++) {
        const i = (y * cols + x) * 4
        const l = lum([pixels[i], pixels[i + 1], pixels[i + 2]]) ** (1 / 2.2)
        if (l < Math.min(0.97, cut + 0.18)) { far[x] = y; break }
      }
    }
    // Lone pixels in the outline read as noise: smooth them away.
    const smooth = a => a.map((v, x) => [a[x - 1] ?? v, v, a[x + 1] ?? v].sort((m, n) => m - n)[1])
    const landS = smooth(land)
    const farS = smooth(far)
    const horizon = Math.min(...landS)
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        let ink
        if (y >= landS[x]) ink = 5
        else if (y >= farS[x]) ink = 4
        else {
          // Sky: page at the top, warming to the horizon.
          const t = Math.min(1, y / Math.max(1, Math.max(horizon, rows * 0.6)))
          const level = t * 2.2
          const base = Math.floor(level)
          ink = 1 + Math.min(2, base + (level - base > bayer(x, y) ? 1 : 0))
        }
        index[y * cols + x] = ink === 1 ? 0 : ink
      }
    }
    if (o.lights) {
      const lit = []
      for (let x = 0; x < cols; x++) for (let y = Math.max(landS[x] + 2, low); y < rows - 1; y++) if (random() < 0.04 && (x + y) % 2 === 0) lit.push([x, y])
      nightOnly.push({ fill: p.night.lights, cells: lit })
    }
  } else {
    // Photo: the picture's own colours, softened by day and deepened by night.
    const k = 5
    const palette = quantize(pixels, k)
    const share = new Array(k).fill(0)
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const i = (y * cols + x) * 4
        const c = ditherTo([pixels[i], pixels[i + 1], pixels[i + 2]], palette, x, y)
        index[y * cols + x] = c === k - 1 && y < low ? k + 1 : c + 1
        share[c] += 1
      }
    }
    // The brightest colour may glow at night, if it is a small part of the picture.
    const brightest = k - 1
    const glow = share[brightest] / (cols * rows) < 0.12
    dayInks = [...palette.map(c => toHex(pastel(c))), toHex(pastel(palette[brightest]))]
    nightInks = [...palette.map((c, i) => toHex(deep(c, glow && i === brightest))), toHex(deep(palette[brightest], false))]
  }

  // The top rows dissolve into the page, so the art never draws a hard line across the window.
  for (let y = 0; y < fade; y++) {
    const keep = (y + 1) / (fade + 1)
    for (let x = 0; x < cols; x++) if (bayer(x, y) > keep) index[y * cols + x] = 0
  }

  // One path per ink, shared by both looks through <use>: each run of pixels is one stroke.
  const runs = new Map()
  for (let y = 0; y < rows; y++) {
    const yy = +(top + y * s + s / 2).toFixed(3)
    let x = 0
    while (x < cols) {
      const ink = index[y * cols + x]
      let end = x + 1
      while (end < cols && index[y * cols + end] === ink) end += 1
      if (ink !== 0) {
        if (!runs.has(ink)) runs.set(ink, { d: [], row: -1, pen: 0 })
        const r = runs.get(ink)
        const x0 = +(x * s).toFixed(3)
        const len = +((end - x) * s).toFixed(3)
        if (r.row !== y) { r.d.push(`M${x0} ${yy}h${len}`); r.row = y }
        else r.d.push(`m${+(x0 - r.pen).toFixed(3)} 0h${len}`)
        r.pen = +(x0 + len).toFixed(3)
      }
      x = end
    }
  }
  const sw = +(s * 1.04).toFixed(3)
  const defs = [...runs].map(([ink, r]) => `<path id="k${ink}" d="${r.d.join('')}"/>`).join('')
  const uses = inks => [...runs.keys()].map(ink => `<use href="#k${ink}" stroke="${inks[ink - 1]}"/>`).join('')

  // A few dim stars high up, at night only.
  let stars = ''
  if (o.stars) {
    const pick = []
    for (let i = 0; i < 18; i++) pick.push(`M${Math.round(random() * W)} ${Math.round(8 + random() * Math.max(10, top - 40))}h1`)
    stars = `<path d="${pick.join('')}" stroke="#8f93b8" stroke-width="1" opacity=".55"/>`
  }
  const extra = nightOnly.map(({ fill, cells }) => cells.length ? `<path d="${cells.map(([x, y]) => `M${+(x * s).toFixed(3)} ${+(top + y * s + s / 2).toFixed(3)}h${s}`).join('')}" stroke="${fill}" stroke-width="${sw}"/>` : '').join('')

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="100%" height="100%" preserveAspectRatio="xMidYMax slice">`
    + `<style>:root{color-scheme:light dark}.n{display:none}@media (prefers-color-scheme:dark){.d{display:none}.n{display:inline}}</style>`
    + `<defs>${defs}</defs>`
    + `<g class="d"><rect width="${W}" height="${H}" fill="${PAGE.day}"/><g stroke-width="${sw}" fill="none">${uses(dayInks)}</g></g>`
    + `<g class="n"><rect width="${W}" height="${H}" fill="${PAGE.night}"/>${stars}<g stroke-width="${sw}" fill="none">${uses(nightInks)}</g>${extra}</g>`
    + `</svg>`
  return { svg, colours: runs.size }
}

/** A made-up skyline to try the maker with, drawn on a canvas. */
export function sampleImage() {
  const c = document.createElement('canvas')
  c.width = 1200
  c.height = 500
  const g = c.getContext('2d')
  const sky = g.createLinearGradient(0, 0, 0, 500)
  sky.addColorStop(0, '#9cc9e8'); sky.addColorStop(0.6, '#f6c9a8'); sky.addColorStop(1, '#f39f86')
  g.fillStyle = sky
  g.fillRect(0, 0, 1200, 500)
  const r = rand(42)
  g.fillStyle = '#5b6f8c'
  for (let x = 0; x < 1200; x += 26) { const h = 60 + r() * 120; g.fillRect(x, 500 - h - 60, 24, h) }
  g.fillStyle = '#26324a'
  let x = 0
  while (x < 1200) {
    const w = 30 + r() * 70
    const h = 90 + r() ** 2 * 260
    g.fillRect(x, 500 - h, w, h)
    if (r() < 0.15) { g.fillRect(x + w / 2 - 3, 500 - h - 70, 6, 70) }
    x += w + 4
  }
  g.fillStyle = '#1b2436'
  g.fillRect(0, 450, 1200, 50)
  return c
}
