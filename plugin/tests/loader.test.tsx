import { expect, mock, test } from 'claude-code/testing'

import { DEFAULT } from '../hooks/default.js'

const SITE = 'https://faiqhilman13.github.io/backdrop-club/'
const BACKDROP = {
  plugin: 'backdrop-club',
  component: 'Backdrop',
  props: { scene: 'backdrop-club', plugin: 'backdrop-club', glass: { blur: 0, opacity: 0.6 } },
} as const
const RUN = { origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 120 } } as const

const TOKYO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 160" width="100%" height="100%" preserveAspectRatio="xMidYMax slice"><style>:root{color-scheme:light dark}</style><rect y="140" width="512" height="20" fill="#a8cac4"/></svg>'
const BAD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 160"><script>alert(1)</script></svg>'

type On = Parameters<Extract<Parameters<typeof test>[1], (...args: never[]) => unknown>>[1]

/** Stands in for the engine and the gallery's website. */
const PICK = '/home/test/.config/backdrop-club/current.json'

function engine(on: On, kept: Record<string, unknown> = {}, site: Record<string, unknown> = {}, files: Record<string, string> = {}) {
  const themes: unknown[] = []
  const fetched: string[] = []
  const stamps: Record<string, number> = {}
  let cleared = 0
  const clock = mock.clock(on, { now: 0 })

  mock.env(on, { HOME: '/home/test' })
  // Files live in memory: the pick file the CLI and the loader share.
  on('fs.read', (_, e) => (e.path in files ? { value: files[e.path]! } : { deny: 'ENOENT' }))
  on('fs.write', (_, e) => {
    files[e.path] = e.text
    stamps[e.path] = (stamps[e.path] ?? 0) + 1
    return { value: undefined }
  })
  on('fs.stat', (_, e) => (e.path in files ? { value: { kind: 'file' as const, size: files[e.path]!.length, mtimeMs: stamps[e.path] ?? 1, isLink: false } } : { deny: 'ENOENT' }))

  on('theme.set', (_, e) => {
    themes.push(e)
    return { value: { isDrawn: true, requestId: 'backdrop' } }
  })
  on('theme.clear', () => {
    cleared += 1
    return { value: { isDrawn: false, reason: 'cleared' } }
  })
  on('command.register', () => ({ value: { command: 'backdrop' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('store.get', (_, e) => ({ value: kept[e.key] }))
  on('store.set', (_, e) => {
    kept[e.key] = e.value
    return { value: undefined }
  })
  on('store.delete', (_, e) => {
    delete kept[e.key]
    return { value: undefined }
  })
  on('http.fetch', (_, e) => {
    fetched.push(e.url)
    const path = e.url.startsWith(SITE) ? e.url.slice(SITE.length) : e.url
    const answer = (status: number, text: string) => ({ value: { status, ok: status >= 200 && status < 300, headers: {} as Record<string, string>, text } })
    if (site.down) return answer(503, '')
    const body = site[path]
    return body === undefined ? answer(404, 'not found') : answer(200, JSON.stringify(body))
  })

  /** What the CLI does: writes the pick file. */
  const cli = (pick: Record<string, unknown>) => {
    files[PICK] = JSON.stringify(pick)
    stamps[PICK] = (stamps[PICK] ?? 0) + 1
  }
  return { themes, fetched, kept, files, clock, cli, cleared: () => cleared }
}

const INDEX = {
  'api/v1/index.json': {
    version: 1,
    themes: [
      { id: 'tokyo', name: 'Tokyo', author: 'someone', tags: ['city'], hash: 'tokyo-1' },
      { id: 'island-bay', name: 'Island bay', author: 'someone', tags: ['sea'], hash: 'bay-1' },
      { id: 'broken', name: 'Broken', author: 'someone', tags: [], hash: 'broken-1' },
    ],
    revoked: [],
  },
  'api/v1/themes/tokyo.json': { id: 'tokyo', name: 'Tokyo', author: 'someone', hash: 'tokyo-1', svg: TOKYO_SVG },
  'api/v1/themes/broken.json': { id: 'broken', name: 'Broken', author: 'someone', hash: 'broken-1', svg: BAD_SVG },
}

async function drawn($: Parameters<Extract<Parameters<typeof test>[1], (...args: never[]) => unknown>>[0]) {
  const ui = await $.ui.mount({ ...BACKDROP, surface: 'desktop' })
  const svg = await ui.find({ type: 'Svg' })
  await ui.unmount()
  return svg?.props.source
}

test('the bundled scene shows at the start, named as the app reads it', async ($, on) => {
  const { themes } = engine(on)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(themes).toEqual([{ backdrop: { scene: 'backdrop-club', id: 'backdrop-club', glass: { blur: 0, opacity: 0.6 } } }])
  expect(await drawn($)).toBe(DEFAULT.svg)
  // The bundled scene passes the same rules every gallery theme does.
  expect(DEFAULT.svg.length).toBeLessThanOrEqual(131072)
  expect(/<script|\son[a-z]+=|<animate/.test(DEFAULT.svg)).toBe(false)
})

test('a theme picked by name is fetched, checked, drawn and kept for the next session', async ($, on) => {
  const { kept, fetched } = engine(on, {}, INDEX)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const reply = await $.command.run({ command: 'backdrop', args: 'TOKYO', ...RUN })
  expect(reply.text).toContain('Now showing Tokyo by @someone')
  expect(fetched).toEqual([`${SITE}api/v1/index.json`, `${SITE}api/v1/themes/tokyo.json`])
  expect(await drawn($)).toBe(TOKYO_SVG)
  expect((kept.theme as { id: string }).id).toBe('tokyo')
})

test('a pick from another session shows at the start', async ($, on) => {
  engine(on, { theme: { id: 'tokyo', name: 'Tokyo', author: 'someone', svg: TOKYO_SVG } })

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(await drawn($)).toBe(TOKYO_SVG)
})

test('a theme that breaks the rules is refused, and the backdrop stays', async ($, on) => {
  const { kept } = engine(on, {}, INDEX)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const reply = await $.command.run({ command: 'backdrop', args: 'broken', ...RUN })
  expect(reply.text).toContain('was refused')
  expect(await drawn($)).toBe(DEFAULT.svg)
  expect(kept.theme).toBe(undefined)
})

test('unknown names, a closed gallery and a stored file that breaks the rules all leave a sensible backdrop', async ($, on) => {
  const site: Record<string, unknown> = { ...INDEX }
  engine(on, { theme: { id: 'x', name: 'X', author: 'y', svg: BAD_SVG } }, site)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  // A kept file that fails the rules is never drawn.
  expect(await drawn($)).toBe(DEFAULT.svg)

  const unknown = await $.command.run({ command: 'backdrop', args: 'atlantis', ...RUN })
  expect(unknown.text).toContain('No theme called "atlantis"')

  site.down = true
  const down = await $.command.run({ command: 'backdrop', args: 'tokyo', ...RUN })
  expect(down.text).toContain("Couldn't reach the gallery")
  expect(await drawn($)).toBe(DEFAULT.svg)
})

test('list, off and on', async ($, on) => {
  const { kept, cleared, themes } = engine(on, {}, INDEX)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const listed = await $.command.run({ command: 'backdrop', args: 'list city', ...RUN })
  expect(listed.text).toContain('1 theme tagged city')
  expect(listed.text).toContain('tokyo  (Tokyo by @someone)')

  const off = await $.command.run({ command: 'backdrop', args: 'off', ...RUN })
  expect(off.text).toContain('Backdrop off')
  expect(cleared()).toBe(1)
  expect(kept.off).toBe(true)

  const back = await $.command.run({ command: 'backdrop', args: 'on', ...RUN })
  expect(back.text).toContain(`Showing ${DEFAULT.name}`)
  expect(kept.off).toBe(undefined)
  expect(themes.length).toBe(2)
})

test('a pick made with the CLI shows in an open session within seconds, and a pick here reaches the CLI', async ($, on) => {
  const { clock, cli, files } = engine(on, {}, INDEX)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(await drawn($)).toBe(DEFAULT.svg)

  cli({ id: 'tokyo', name: 'Tokyo', author: 'someone', svg: TOKYO_SVG, off: false })
  await clock.advance(3100)
  expect(await drawn($)).toBe(TOKYO_SVG)

  // A file that breaks the rules is never drawn.
  cli({ id: 'broken', name: 'Broken', author: 'someone', svg: BAD_SVG })
  await clock.advance(3100)
  expect(await drawn($)).toBe(DEFAULT.svg)

  await $.command.run({ command: 'backdrop', args: 'tokyo', ...RUN })
  expect(JSON.parse(files[PICK]!).id).toBe('tokyo')
})

test('Claude can find backdrops and set the one the person picks', async ($, on) => {
  const { files } = engine(on, {}, INDEX)

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const found = await $.tool.call({ tool: 'mcp__backdrop-club__find_backdrops', query: 'city' })
  expect(String(found.result)).toContain('tokyo: Tokyo by @someone [city]')
  expect(String(found.result)).not.toContain('island-bay')

  const set = await $.tool.call({ tool: 'mcp__backdrop-club__set_backdrop', theme: 'Tokyo' })
  expect(String(set.result)).toContain('Now showing Tokyo')
  expect(await drawn($)).toBe(TOKYO_SVG)
  expect(JSON.parse(files[PICK]!).id).toBe('tokyo')
})

const TOKYO_V2 = TOKYO_SVG.replace('#a8cac4', '#b5d3cd')

test('when an author updates a theme, machines that kept the old copy get the new one', async ($, on) => {
  const site = {
    ...INDEX,
    'api/v1/index.json': { version: 1, themes: [{ id: 'tokyo', name: 'Tokyo', author: 'someone', tags: ['city'], hash: 'tokyo-2' }], revoked: [] },
    'api/v1/themes/tokyo.json': { id: 'tokyo', name: 'Tokyo', author: 'someone', hash: 'tokyo-2', svg: TOKYO_V2 },
  }
  const { clock, files, cli } = engine(on, {}, site)
  cli({ id: 'tokyo', name: 'Tokyo', author: 'someone', svg: TOKYO_SVG, hash: 'tokyo-1', off: false })

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(await drawn($)).toBe(TOKYO_SVG)
  await clock.advance(1600)
  expect(await drawn($)).toBe(TOKYO_V2)
  expect(JSON.parse(files[PICK]!).hash).toBe('tokyo-2')
})

test('a theme taken down from the gallery leaves the machines that kept a copy', async ($, on) => {
  const site = { ...INDEX, 'api/v1/index.json': { version: 1, themes: [], revoked: ['tokyo'] } }
  const { clock, cli } = engine(on, {}, site)
  cli({ id: 'tokyo', name: 'Tokyo', author: 'someone', svg: TOKYO_SVG, hash: 'tokyo-1', off: false })

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  expect(await drawn($)).toBe(TOKYO_SVG)
  await clock.advance(1600)
  expect(await drawn($)).toBe(DEFAULT.svg)
})

test('the gallery is asked at most every few hours, and an offline machine keeps its copy', async ($, on) => {
  const site: Record<string, unknown> = { ...INDEX, down: true }
  const { clock, cli, fetched } = engine(on, { checkedAt: 0 }, site)
  cli({ id: 'tokyo', name: 'Tokyo', author: 'someone', svg: TOKYO_SVG, hash: 'tokyo-1', off: false })

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  await clock.advance(1600)
  // Checked moments ago (time 0 in this test's clock): no request goes out.
  expect(fetched.length).toBe(0)
  expect(await drawn($)).toBe(TOKYO_SVG)
})
