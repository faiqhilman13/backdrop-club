#!/usr/bin/env node
// Serves dist/ under the site's base path, as GitHub Pages will.
//   node tools/serve.mjs [port]
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.xml': 'application/xml', '.txt': 'text/plain; charset=utf-8', '.jpg': 'image/jpeg',
}

export function createServer(dist, base) {
  return http.createServer((req, res) => {
    const url = new URL(req.url, 'http://local')
    let rel = decodeURIComponent(url.pathname)
    if (!rel.startsWith(base)) { res.writeHead(302, { location: base }); res.end(); return }
    rel = rel.slice(base.length)
    let file = path.join(dist, rel)
    if (!file.startsWith(dist)) { res.writeHead(403); res.end(); return }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html')
    if (!fs.existsSync(file)) { res.writeHead(404, { 'content-type': TYPES['.html'] }); res.end(fs.existsSync(path.join(dist, '404.html')) ? fs.readFileSync(path.join(dist, '404.html')) : 'Not found'); return }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream', 'cache-control': 'no-store' })
    fs.createReadStream(file).pipe(res)
  })
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const config = JSON.parse(fs.readFileSync(path.join(ROOT, 'site/config.json'), 'utf8'))
  const port = Number(process.argv[2] ?? 4173)
  createServer(path.join(ROOT, 'dist'), config.base).listen(port, '127.0.0.1', () => console.log(`http://127.0.0.1:${port}${config.base}`))
}
