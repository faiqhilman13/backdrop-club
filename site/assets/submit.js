// The Submit page: check a theme as the gallery will, then hand it to GitHub.
import { check, forceScheme, slug } from './check.mjs'
import { measure } from './readability.js'

const site = await fetch(new URL('site.json', import.meta.url)).then(r => r.json())
const form = document.querySelector('.submit-form')
const drop = form.querySelector('.drop')
const file = drop.querySelector('input[type="file"]')
const paste = form.querySelector('.paste')
const report = document.querySelector('.report')
const after = document.querySelector('.after')
const submit = document.querySelector('[data-action="submit"]')
const [lightImg, darkImg] = document.querySelectorAll('.submit-preview img')

let svg = ''
let result = null
let score = null
let job = 0

const dataUrl = text => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(text)}`
const esc = text => String(text).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))

function tags() {
  return [...new Set(form.elements.tags.value.split(',').map(t => slug(t)).filter(Boolean))].slice(0, 5)
}

function ready() {
  const name = form.elements.name.value.trim()
  const missing = []
  if (!result?.ok) missing.push('a theme that passes the rules')
  if (!score?.ok) missing.push('enough contrast for chat text')
  if (!name) missing.push('a name')
  if (!form.elements.rights.checked) missing.push('the rights box ticked')
  submit.disabled = missing.length > 0
  submit.title = missing.length ? `Still needs ${missing.join(', ')}` : ''
}

async function load(text, label) {
  svg = text
  const mine = ++job
  result = check(svg)
  score = null
  drop.classList.toggle('has', result.ok)
  if (label) drop.querySelector('strong').textContent = label
  const items = [
    ...result.errors.map(e => `<li class="bad">${esc(e)}</li>`),
    ...result.warnings.map(w => `<li class="warn">${esc(w)}</li>`),
  ]
  if (result.ok) {
    items.unshift(`<li>Passes the gallery rules · <span class="score">${Math.round(result.svg.length / 1000)} KB</span>, ${result.stats.elements} elements</li>`)
    lightImg.src = dataUrl(forceScheme(result.svg, 'light'))
    darkImg.src = dataUrl(forceScheme(result.svg, 'dark'))
    items.push('<li class="warn" data-pending>Checking readability…</li>')
  }
  report.innerHTML = `<ul>${items.join('')}</ul>`
  ready()
  if (!result.ok) return
  try {
    score = await measure(result.svg)
  } catch (error) {
    score = { ok: false, light: { contrast: 0 }, dark: { contrast: 0 } }
  }
  if (mine !== job) return
  const line = score.ok
    ? `<li>Chat stays readable: <span class="score">${score.light.contrast}:1</span> in light, <span class="score">${score.dark.contrast}:1</span> in dark${score.grade === 'clean' ? ' · <span class="badge">Reads clean</span>' : ''}</li>`
    : `<li class="bad">Too little contrast where chat text sits: <span class="score">${score.light.contrast}:1</span> light, <span class="score">${score.dark.contrast}:1</span> dark. It needs 4.5:1 in both. Move the art lower, or make it paler by day and darker by night.</li>`
  report.querySelector('[data-pending]').outerHTML = line
  ready()
}

function readFile(f) {
  if (!f) return
  const reader = new FileReader()
  reader.onload = () => load(String(reader.result), f.name)
  reader.readAsText(f)
}

file.addEventListener('change', () => readFile(file.files[0]))
drop.addEventListener('click', event => { if (event.target.closest('[data-action="paste"]')) { event.preventDefault(); paste.hidden = false; paste.focus() } })
drop.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); file.click() } })
for (const type of ['dragenter', 'dragover']) drop.addEventListener(type, event => { event.preventDefault(); drop.classList.add('over') })
for (const type of ['dragleave', 'drop']) drop.addEventListener(type, () => drop.classList.remove('over'))
drop.addEventListener('drop', event => { event.preventDefault(); readFile(event.dataTransfer.files[0]) })
paste.addEventListener('input', () => { if (paste.value.trim().startsWith('<')) load(paste.value, 'Pasted code') })
form.addEventListener('input', event => { if (event.target !== paste) ready() })

submit.addEventListener('click', async () => {
  const name = form.elements.name.value.trim()
  const body = result.svg
  try { await navigator.clipboard.writeText(body) } catch {
    paste.hidden = false
    paste.value = body
    paste.select()
    document.execCommand('copy')
  }
  const params = new URLSearchParams({
    template: 'submit-theme.yml',
    title: `Theme: ${name}`,
    name,
    description: form.elements.description.value.trim(),
    tags: tags().join(', '),
  })
  // Small files fit in the link itself; bigger ones are pasted from the clipboard.
  const short = params.toString().length + encodeURIComponent(body).length < 6000
  if (short) params.set('svg', body)
  after.hidden = false
  after.querySelector('li').textContent = short ? 'Your theme is filled in on GitHub (and copied, just in case).' : 'Your theme is copied.'
  window.open(`https://github.com/${site.repo}/issues/new?${params}`, '_blank', 'noopener')
})

// Arriving from the maker brings its backdrop along.
let draft = null
try { draft = sessionStorage.getItem('bc-draft') } catch {}
if (draft) {
  try { sessionStorage.removeItem('bc-draft') } catch {}
  load(draft, 'From the maker')
}
