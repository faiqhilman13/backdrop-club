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

/** The whole picture, smaller: what the maker reads every setting from. */
export function prepare(image, maxW = 320) {
  const iw = image.naturalWidth || image.width
  const ih = image.naturalHeight || image.height
  const w = Math.min(maxW, iw)
  const h = Math.max(8, Math.round((ih * w) / iw))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(image, 0, 0, w, h)
  return { data: ctx.getImageData(0, 0, w, h).data, w, h }
}

function topColour(p) {
  const rows = Math.max(1, Math.round(p.h * 0.06))
  const r = []; const g = []; const b = []
  for (let y = 0; y < rows; y++) for (let x = 0; x < p.w; x += 2) { const i = (y * p.w + x) * 4; r.push(p.data[i]); g.push(p.data[i + 1]); b.push(p.data[i + 2]) }
  const mid = a => a.sort((m, n) => m - n)[a.length >> 1]
  return [mid(r), mid(g), mid(b)]
}

/**
 * Where the sky ends in each column of the picture, as one smooth line.
 *
 * Every pixel gets a sky score: blue sky, cool-white cloud, or the colour at the top of the picture
 * score high; warm pixels (rock, earth, trees, buildings) score low, which is what tells a white
 * cloud from sunlit granite. Then the line with sky above it and land below, that bends least from
 * column to column, is found by dynamic programming, so stray clouds don't punch holes in it.
 * `strictness` 0..1: higher calls more of the picture land.
 * @returns {{ line: Int16Array, confidence: number }} confidence 0..1: how clearly sky and land part
 */
export function findSkyline(p, strictness = 0.5) {
  const { w, h, data } = p
  const top = topColour(p)
  // Texture: how much each pixel differs from its neighbours, averaged over three by three.
  // Sky is smooth; rock, trees and buildings are not, even when they are bright or warm.
  const light = new Float32Array(w * h)
  for (let i = 0, j = 0; j < w * h; i += 4, j++) light[j] = (0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]) / 255
  const edge = new Float32Array(w * h)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const j = y * w + x
    edge[j] = Math.abs(light[j] - light[x < w - 1 ? j + 1 : j]) + Math.abs(light[j] - light[y < h - 1 ? j + w : j])
  }
  const texture = new Float32Array(w * h)
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let sum = 0
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) sum += edge[Math.min(h - 1, Math.max(0, y + dy)) * w + Math.min(w - 1, Math.max(0, x + dx))]
    texture[y * w + x] = sum / 9
  }
  const topLight = (0.2126 * top[0] + 0.7152 * top[1] + 0.0722 * top[2]) / 255
  const score = new Float32Array(w * h)
  for (let i = 0, j = 0; j < w * h; i += 4, j++) {
    const r = data[i]; const g = data[i + 1]; const b = data[i + 2]
    const max = Math.max(r, g, b)
    const smooth = texture[j] < 0.035
    let sky = b > 90 ? Math.min(1, Math.max(0, (b - r - 10) / 50)) : 0
    if (b >= r + 3 && max > 185 && max - Math.min(r, g, b) < 60) sky = Math.max(sky, 0.85)
    sky = Math.max(sky, Math.max(0, 1 - Math.hypot(r - top[0], g - top[1], b - top[2]) / 90) * 0.8)
    if (smooth && light[j] > topLight * 0.55) sky = Math.max(sky, 0.7)
    if (r > b + 6 && !smooth) sky *= 0.25
    score[j] = sky
  }
  // cost[s][x]: calling rows above s sky and the rest land, in column x.
  const H = h + 1
  const cost = new Float32Array(H * w)
  for (let x = 0; x < w; x++) {
    let total = 0
    for (let y = 0; y < h; y++) total += score[y * w + x]
    let above = 0
    for (let s = 0; s <= h; s++) {
      cost[s * w + x] = (s - above) * (1.5 - strictness) + (total - above) * (0.5 + strictness)
      if (s < h) above += score[s * w + x]
    }
  }
  // Big jumps are allowed (a building's side) but cost more the bigger they are.
  const maxStep = Math.max(3, Math.round(h / 5))
  const bend = (0.08 * h) / 40
  let acc = new Float32Array(H)
  for (let s = 0; s < H; s++) acc[s] = cost[s * w]
  const back = new Int16Array(H * w)
  for (let x = 1; x < w; x++) {
    const next = new Float32Array(H)
    for (let s = 0; s < H; s++) {
      let best = Infinity
      let from = s
      for (let d = -maxStep; d <= maxStep; d++) {
        const t = s - d
        if (t < 0 || t >= H) continue
        const c = acc[t] + bend * Math.abs(d)
        if (c < best) { best = c; from = t }
      }
      next[s] = best + cost[s * w + x]
      back[s * w + x] = from
    }
    acc = next
  }
  let s = 0
  for (let k = 1; k < H; k++) if (acc[k] < acc[s]) s = k
  const line = new Int16Array(w)
  line[w - 1] = s
  for (let x = w - 1; x > 0; x--) { s = back[s * w + x]; line[x - 1] = s }
  // How clearly the two sides differ: the mean sky score above the line minus below it.
  let up = 0; let upN = 0; let down = 0; let downN = 0
  for (let x = 0; x < w; x += 2) for (let y = 0; y < h; y += 2) { if (y < line[x]) { up += score[y * w + x]; upN++ } else { down += score[y * w + x]; downN++ } }
  const confidence = Math.max(0, (upN ? up / upN : 0) - (downN ? down / downN : 1))
  return { line, confidence }
}

function rand(seed) {
  let s = seed >>> 0
  return () => { s = (s + 0x6d2b79f5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
}

const mixHex = (a, b, t) => toHex(hex(a).map((v, i) => v + (hex(b)[i] - v) * t))

/**
 * Makes the backdrop from a picture `prepare` read.
 *
 * The part of the picture where land meets sky is found and laid along the window's foot: its
 * width over the middle of the window (what every window shape shows), its height into the art
 * band. Beyond the picture's edges the ridge carries on, easing down, for wide windows.
 * @param {{ data: Uint8ClampedArray, w: number, h: number }} p
 * @param {{ cols: number, rows: number, mode: 'silhouette' | 'photo', palette: string, cut: number, focus: number, stars: boolean, lights: boolean }} o
 * @returns {{ svg: string, colours: number, found: boolean }}
 */
export function makeBackdrop(p, o) {
  const { cols, rows } = o
  const s = W / cols
  const top = H - rows * s
  const fade = Math.max(2, Math.round(rows * 0.24))
  const index = new Uint8Array(cols * rows) // 0 is the page
  let dayInks
  let nightInks
  const nightOnly = []
  const random = rand(cols * 7919 + rows * 104729 + Math.round(o.cut * 31))
  // Bright colours stay below the line where chat text ends (the prompt box sits there).
  const low = Math.ceil((134 - top) / s)

  // Where land meets sky in the picture, and the band of it to keep.
  const { line, confidence } = findSkyline(p, o.cut / 100)
  const land = [...line].filter(v => v < p.h).sort((a, c) => a - c)
  const found = confidence > 0.3 && land.length > p.w * 0.25
  const hi = found ? land[Math.floor(land.length * 0.04)] : p.h * 0.4
  const lo = found ? land[Math.floor(land.length * 0.92)] : p.h * 0.75
  let zoneH = Math.min(p.h, Math.max((lo - hi) * 1.35, p.h * 0.14))
  let z0 = hi - zoneH * 0.06 + ((o.focus ?? 0.6) - 0.6) * zoneH
  z0 = Math.max(0, Math.min(p.h - zoneH, z0))
  zoneH = Math.min(zoneH, p.h - z0)
  // The highest peak sits just under the dissolve at the band's top.
  const head = Math.round(fade * 0.55)
  const landRows = rows - head
  const sY = landRows / zoneH
  // The picture fills the middle of the window, the part every window shape shows.
  const span = Math.round(Math.min(cols * 0.56, Math.max(cols * 0.42, p.w * sY * 0.9)))
  const x0 = Math.round((cols - span) / 2)
  const sX = p.w / span
  const rowOf = py => head + (py - z0) * sY
  const pixelAt = (X, Y) => {
    const px = Math.min(p.w - 1, Math.max(0, Math.floor((X - x0 + 0.5) * sX)))
    const py = Math.min(p.h - 1, Math.max(0, Math.floor(z0 + (Y - head + 0.5) / sY)))
    const i = (py * p.w + px) * 4
    return [p.data[i], p.data[i + 1], p.data[i + 2]]
  }

  // The ridge in output rows, column by column; beyond the picture it eases down with a little noise.
  const ridge = new Float32Array(cols)
  for (let X = 0; X < span; X++) {
    const a = Math.floor(X * sX)
    const c = Math.max(a + 1, Math.floor((X + 1) * sX))
    let m = p.h
    for (let px = a; px < c && px < p.w; px++) m = Math.min(m, line[px])
    ridge[x0 + X] = m >= p.h ? rows : rowOf(m)
  }
  const base = Math.max(head + 2, rows * 0.6)
  const wobble = Array.from({ length: cols }, () => random())
  const smoothNoise = X => (wobble[Math.max(0, X - 1)] + wobble[X] * 2 + wobble[Math.min(cols - 1, X + 1)]) / 4
  for (let X = 0; X < x0; X++) {
    const t = (x0 - X) / Math.max(1, x0)
    const ease = t * t * (3 - 2 * t)
    ridge[X] = ridge[x0] + (base - ridge[x0]) * ease + (smoothNoise(X) - 0.5) * rows * 0.12 * ease
  }
  for (let X = x0 + span; X < cols; X++) {
    const t = (X - (x0 + span - 1)) / Math.max(1, cols - (x0 + span))
    const ease = t * t * (3 - 2 * t)
    const edge = ridge[x0 + span - 1]
    ridge[X] = edge + (base - edge) * ease + (smoothNoise(X) - 0.5) * rows * 0.12 * ease
  }

  if (o.mode === 'silhouette') {
    const pal = PALETTES[o.palette] ?? PALETTES.dawn
    // Inks: 1..3 sky bands (1 is the page), then land in three tones: light rock, mid, deep.
    dayInks = [pal.day.sky[0], pal.day.sky[1], pal.day.sky[2], mixHex(pal.day.far, PAGE.day, 0.5), pal.day.far, pal.day.land]
    nightInks = [pal.night.sky[0], pal.night.sky[1], pal.night.sky[2], mixHex(pal.night.far, pal.night.sky[2], 0.45), pal.night.far, pal.night.land]
    // Land tones follow the picture's own light and shade, split into thirds.
    const lights = []
    for (let X = x0; X < x0 + span; X++) for (let Y = Math.max(0, Math.ceil(ridge[X])); Y < rows; Y++) lights.push(lum(pixelAt(X, Y)))
    lights.sort((a, c) => a - c)
    const t1 = lights[Math.floor(lights.length / 3)] ?? 0.2
    const t2 = lights[Math.floor((lights.length * 2) / 3)] ?? 0.4
    const peaks = Array.from(ridge).filter(v => v < rows)
    const horizon = Math.max(head + 1, peaks.length ? Math.min(...peaks) : rows * 0.6)
    for (let Y = 0; Y < rows; Y++) {
      for (let X = 0; X < cols; X++) {
        let ink
        if (Y >= ridge[X]) {
          if (X < x0 || X >= x0 + span) ink = Y - ridge[X] < 2 ? 5 : 6
          else {
            const L = lum(pixelAt(X, Y))
            // Near a threshold the tone is dithered, so cliff faces and forest keep their shape.
            const level = L > t2 ? 0 : L > t1 ? 1 : 2
            const edge = L > t2 ? (L - t2) / Math.max(0.01, 1 - t2) : L > t1 ? (L - t1) / Math.max(0.01, t2 - t1) : L / Math.max(0.01, t1)
            const nudge = level > 0 && edge > 0.6 + bayer(X, Y) * 0.4 ? -1 : 0
            ink = 4 + Math.max(0, level + nudge)
          }
        } else {
          // Sky: page at the top, warming to the horizon.
          const t = Math.min(1, Y / Math.max(1, horizon + 2))
          const level = t * t * 1.7
          const step = Math.floor(level)
          ink = 1 + Math.min(2, step + (level - step > bayer(X, Y) ? 1 : 0))
        }
        index[Y * cols + X] = ink === 1 ? 0 : ink
      }
    }
    if (o.lights) {
      const lit = []
      for (let X = 0; X < cols; X++) for (let Y = Math.max(Math.ceil(ridge[X]) + 2, low); Y < rows - 1; Y++) if (random() < 0.04 && (X + Y) % 2 === 0) lit.push([X, Y])
      nightOnly.push({ fill: pal.night.lights, cells: lit })
    }
  } else {
    // Photo: the same skyline, with the picture's own colours on the land and a soft sky of its own colour above.
    const k = 5
    const cells = []
    for (let X = x0; X < x0 + span; X++) for (let Y = Math.max(head, Math.ceil(ridge[X])); Y < rows; Y++) { const c = pixelAt(X, Y); cells.push(c[0], c[1], c[2], 255) }
    const palette = quantize(Uint8ClampedArray.from(cells.length ? cells : [128, 128, 128, 255]), k)
    const share = new Array(k).fill(0)
    const skyRgb = topColour(p)
    const peaks = Array.from(ridge).filter(v => v < rows)
    const horizon = Math.max(head + 1, peaks.length ? Math.min(...peaks) : rows * 0.6)
    // Inks 1..k the picture's colours; k+1 its brightest kept dim up high; k+2, k+3 the sky.
    for (let Y = 0; Y < rows; Y++) {
      for (let X = 0; X < cols; X++) {
        if (Y >= ridge[X]) {
          if (X >= x0 && X < x0 + span) {
            const c = ditherTo(pixelAt(X, Y), palette, X, Y)
            index[Y * cols + X] = c === k - 1 && Y < low ? k + 1 : c + 1
            share[c] += 1
          } else {
            index[Y * cols + X] = 2 // a middle colour of the picture carries the ridge on
          }
        } else {
          const t = Math.min(1, Y / Math.max(1, horizon + 2))
          const level = t * t * 1.7
          const step = Math.floor(level)
          const band = Math.min(2, step + (level - step > bayer(X, Y) ? 1 : 0))
          index[Y * cols + X] = band === 0 ? 0 : k + 1 + band
        }
      }
    }
    // The brightest colour may glow at night, if it is a small part of the picture.
    const brightest = k - 1
    // Only a sprinkle of bright pixels (lit windows, lamps) may glow at night; a bright cliff stays dark.
    const glow = share[brightest] / Math.max(1, span * rows) < 0.04
    const skyDay = toHex(pastel(skyRgb))
    const skyNight = toHex(deep(skyRgb, false))
    dayInks = [...palette.map(c => toHex(pastel(c))), toHex(pastel(palette[brightest])), mixHex(skyDay, PAGE.day, 0.55), skyDay]
    nightInks = [...palette.map((c, i) => toHex(deep(c, glow && i === brightest))), toHex(deep(palette[brightest], false)), mixHex(skyNight, PAGE.night, 0.5), skyNight]
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
  return { svg, colours: runs.size, found }
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
