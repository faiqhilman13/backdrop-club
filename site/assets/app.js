// Small behaviours shared by every page: copying, light/dark, previews, the gallery's filters.

const store = {
  get(key) { try { return localStorage.getItem(key) } catch { return null } },
  set(key, value) { try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value) } catch {} },
}

// Copy buttons: anything with data-copy.
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-copy]')
  if (!button) return
  const text = button.dataset.copy
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const area = Object.assign(document.createElement('textarea'), { value: text })
    document.body.append(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  const hint = button.querySelector('.cmd-hint') ?? button
  const before = hint.textContent
  button.classList.add('done')
  hint.textContent = button.dataset.done ?? 'Copied'
  setTimeout(() => { button.classList.remove('done'); hint.textContent = before }, 1600)
})

// Light and dark: follow the system until the reader picks one.
document.querySelector('.mode')?.addEventListener('click', () => {
  const root = document.documentElement
  const isDark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches
  const next = isDark ? 'light' : 'dark'
  root.dataset.theme = next
  store.set('bc-theme', next)
})

// Split / Light / Dark buttons change the nearest preview window.
for (const group of document.querySelectorAll('.views')) {
  group.addEventListener('click', event => {
    const button = event.target.closest('.view')
    if (!button) return
    const scope = group.closest('.theme-art, .tool-out') ?? document
    const win = scope.querySelector('.win')
    if (win) win.dataset.view = button.dataset.view
    for (const b of group.querySelectorAll('.view')) b.classList.toggle('on', b === button)
  })
}

// The hero's scene steps through the featured themes.
const cycle = document.querySelector('[data-cycle]')
if (cycle) {
  const list = JSON.parse(cycle.dataset.cycle)
  const win = document.querySelector('.hero-art .win')
  const name = document.querySelector('.hero-name')
  const base = new URL('.', document.querySelector('.logo').href).pathname
  let at = 0
  const show = i => {
    at = (i + list.length) % list.length
    const t = list[at]
    const [light, dark] = win.querySelectorAll('img')
    light.src = `${base}t/${t.id}/light.svg`
    dark.src = `${base}t/${t.id}/dark.svg`
    name.textContent = t.name
    name.href = `${base}t/${t.id}/`
  }
  for (const t of list) { new Image().src = `${base}t/${t.id}/light.svg`; new Image().src = `${base}t/${t.id}/dark.svg` }
  cycle.addEventListener('click', () => show(at + 1))
}

// The gallery page: search, tag chips, sort, ?tag= links from theme pages, and a page at a time.
const gallery = document.querySelector('[data-gallery]')
if (gallery) {
  const PAGE = 24
  const grid = gallery.querySelector('.grid')
  const cards = [...grid.querySelectorAll('.card')]
  const search = gallery.querySelector('.search input')
  const sort = gallery.querySelector('.sort')
  const empty = gallery.querySelector('.empty')
  const more = gallery.querySelector('.show-more')
  const chips = [...gallery.querySelectorAll('.chip')]
  let tag = new URLSearchParams(location.search).get('tag') ?? ''
  let limit = PAGE

  const apply = () => {
    const words = (search.value ?? '').toLowerCase().split(/\s+/).filter(Boolean)
    let matched = 0
    for (const card of grid.querySelectorAll('.card')) {
      const hay = `${card.dataset.name} ${card.dataset.tags} ${card.dataset.author} ${card.dataset.id}`
      const ok = (!tag || card.dataset.tags.split(' ').includes(tag)) && words.every(w => hay.includes(w))
      if (ok) matched += 1
      card.hidden = !ok || matched > limit
    }
    empty.hidden = matched > 0
    more.hidden = matched <= limit
    more.textContent = `Show more (${matched - Math.min(matched, limit)} left)`
    for (const chip of chips) chip.classList.toggle('on', chip.dataset.tag === tag)
  }
  const reset = () => { limit = PAGE; apply() }
  const order = () => {
    const by = sort.value
    const sorted = [...cards].sort((a, b) => by === 'name' ? a.dataset.name.localeCompare(b.dataset.name) : b.dataset.added.localeCompare(a.dataset.added) || a.dataset.name.localeCompare(b.dataset.name))
    grid.append(...sorted)
    reset()
  }
  search.addEventListener('input', reset)
  sort.addEventListener('change', order)
  more.addEventListener('click', () => { limit += PAGE; apply() })
  for (const chip of chips) chip.addEventListener('click', () => {
    tag = chip.dataset.tag === tag ? '' : chip.dataset.tag
    const url = new URL(location.href)
    if (tag) url.searchParams.set('tag', tag)
    else url.searchParams.delete('tag')
    history.replaceState(null, '', url)
    reset()
  })
  if (tag && !chips.some(c => c.dataset.tag === tag)) {
    const extra = Object.assign(document.createElement('button'), { className: 'chip', type: 'button', textContent: tag })
    extra.dataset.tag = tag
    chips.push(extra)
    gallery.querySelector('.chips').append(extra)
    extra.addEventListener('click', () => { tag = ''; reset() })
  }
  apply()
}
