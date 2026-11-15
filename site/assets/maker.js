// The Make page: a photo in, a backdrop out, checked as the gallery checks it.
import { check, forceScheme, LIMIT } from './check.mjs'
import { PALETTES, autoCut, makeBackdrop, sample, sampleImage, W, H } from './dither.js'
import { measure } from './readability.js'

const form = document.querySelector('.maker-form')
const drop = form.querySelector('.drop')
const file = drop.querySelector('input[type="file"]')
const swatches = form.querySelector('.swatches')
const report = document.querySelector('.report')
const [lightImg, darkImg] = document.querySelectorAll('.maker-preview img')
const buttons = Object.fromEntries([...document.querySelectorAll('[data-action]')].map(b => [b.dataset.action, b]))

let picture = null
let current = ''
let job = 0

for (const [key, p] of Object.entries(PALETTES)) {
  const label = document.createElement('label')
  label.className = 'swatch'
  label.innerHTML = `<input type="radio" name="palette" value="${key}"${key === 'dawn' ? ' checked' : ''}><span></span><em>${p.label}</em>`
  label.querySelector('span').style.setProperty('--sw', `linear-gradient(135deg, ${p.day.sky[2]} 0 25%, ${p.day.land} 25% 50%, ${p.night.sky[2]} 50% 75%, ${p.night.lights} 75%)`)
  swatches.append(label)
}
swatches.closest('.field').classList.add('silhouette-only')

const value = name => {
  const el = form.elements[name]
  if (el instanceof RadioNodeList) return el.value
  return el.type === 'checkbox' ? el.checked : el.value
}

function outputs() {
  form.querySelector('[data-for="height"]').textContent = `${value('height')}% of the window`
  form.querySelector('[data-for="focus"]').textContent = Number(value('focus')) < 34 ? 'top of photo' : Number(value('focus')) > 66 ? 'bottom of photo' : 'middle'
  form.querySelector('[data-for="cut"]').textContent = value('cut')
  const isSilhouette = value('mode') === 'silhouette'
  for (const el of form.querySelectorAll('.silhouette-only')) el.hidden = !isSilhouette
}

function options() {
  const cols = Number(value('detail'))
  const s = W / cols
  const rows = Math.max(6, Math.round((H * Number(value('height'))) / 100 / s))
  return { cols, rows, mode: value('mode'), palette: value('palette'), cut: Number(value('cut')), stars: value('stars'), lights: value('lights'), focus: Number(value('focus')) / 100 }
}

const dataUrl = svg => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`

async function draw({ recut = false } = {}) {
  outputs()
  if (!picture) return
  const mine = ++job
  const o = options()
  const pixels = sample(picture, o.cols, o.rows, o.focus)
  if (recut && o.mode === 'silhouette') {
    form.elements.cut.value = String(Math.min(90, Math.max(10, autoCut(pixels))))
    o.cut = Number(form.elements.cut.value)
    outputs()
  }
  const { svg, colours } = makeBackdrop(pixels, o)
  current = svg
  lightImg.src = dataUrl(forceScheme(svg, 'light'))
  darkImg.src = dataUrl(forceScheme(svg, 'dark'))
  buttons.download.disabled = false

  const rules = check(svg)
  report.innerHTML = `<ul><li class="${rules.ok ? '' : 'bad'}">${rules.ok ? 'Passes the gallery rules' : rules.errors[0]}</li><li class="${svg.length > LIMIT ? 'bad' : ''}"><span><span class="score">${Math.round(svg.length / 1000)} KB</span> · ${colours} colours</span></li><li class="warn">Checking readability…</li></ul>`
  const score = await measure(svg)
  if (mine !== job) return
  const line = score.ok
    ? `<li>Chat stays readable: <span class="score">${score.light.contrast}:1</span> in light, <span class="score">${score.dark.contrast}:1</span> in dark${score.grade === 'clean' ? ' · <span class="badge">Reads clean</span>' : ''}</li>`
    : `<li class="bad">Too little contrast behind chat text (<span class="score">${score.light.contrast}:1</span> light, <span class="score">${score.dark.contrast}:1</span> dark; needs 4.5:1). Lower the height or try Silhouette.</li>`
  report.querySelector('li.warn').outerHTML = line
  buttons.submit.disabled = !(rules.ok && score.ok)
}

let pending = 0
const later = (opts) => { cancelAnimationFrame(pending); pending = requestAnimationFrame(() => draw(opts)) }
form.addEventListener('input', event => later({ recut: event.target.name === 'focus' && false }))
form.addEventListener('change', event => { if (event.target.name === 'mode' || event.target.name === 'detail') later({ recut: true }) })

function use(image, name) {
  picture = image
  drop.classList.add('has')
  drop.querySelector('strong').textContent = name
  drop.querySelector('span').textContent = 'Choose another, or drop one here.'
  draw({ recut: true })
}

function open(fileObject) {
  if (!fileObject || !fileObject.type.startsWith('image/')) return
  const url = URL.createObjectURL(fileObject)
  const image = new Image()
  image.onload = () => use(image, fileObject.name)
  image.onerror = () => { report.innerHTML = '<p>That file could not be opened as a picture.</p>' }
  image.src = url
}

file.addEventListener('change', () => open(file.files[0]))
drop.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); file.click() } })
for (const type of ['dragenter', 'dragover']) drop.addEventListener(type, event => { event.preventDefault(); drop.classList.add('over') })
for (const type of ['dragleave', 'drop']) drop.addEventListener(type, () => drop.classList.remove('over'))
drop.addEventListener('drop', event => { event.preventDefault(); open(event.dataTransfer.files[0]) })

buttons.sample.addEventListener('click', () => use(sampleImage(), 'Sample skyline'))
buttons.download.addEventListener('click', () => {
  const link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([current], { type: 'image/svg+xml' })), download: 'backdrop.svg' })
  link.click()
})
buttons.submit.addEventListener('click', () => {
  try { sessionStorage.setItem('bc-draft', current) } catch {}
  location.href = new URL('../submit/', location.href).href
})

outputs()
