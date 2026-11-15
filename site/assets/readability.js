// Draws a theme the way a window would and reads its pixels: the gallery's readability check.
import { READING, forceScheme, scorePixels } from './check.mjs'

/** The theme at a fixed window size, so the browser lays it out as that window would. */
function sized(svg, width, height) {
  const end = svg.indexOf('>')
  const head = svg.slice(0, end).replace(/\swidth\s*=\s*("[^"]*"|'[^']*')/, '').replace(/\sheight\s*=\s*("[^"]*"|'[^']*')/, '')
  return `${head} width="${width}" height="${height}"${svg.slice(end)}`
}

function draw(svg, width, height, page) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d', { willReadFrequently: true })
      context.fillStyle = `rgb(${page.join(',')})`
      context.fillRect(0, 0, width, height)
      context.drawImage(image, 0, 0, width, height)
      resolve(context.getImageData(0, 0, width, height).data)
    }
    image.onerror = () => reject(new Error('This browser could not draw the SVG.'))
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(sized(svg, width, height))}`
  })
}

/**
 * @returns {Promise<{ light: { contrast: number, busy: number }, dark: { contrast: number, busy: number }, ok: boolean, grade: 'clean' | 'readable' | 'fails' }>}
 */
export async function measure(svg) {
  const result = {}
  for (const scheme of ['light', 'dark']) {
    const forced = forceScheme(svg, scheme)
    let contrast = 21
    let busy = 0
    for (const [width, height] of READING.sizes) {
      const data = await draw(forced, width, height, READING[scheme].page)
      const score = scorePixels(data, width, height, scheme)
      contrast = Math.min(contrast, score.contrast)
      busy = Math.max(busy, score.busy)
    }
    result[scheme] = { contrast, busy }
  }
  const low = Math.min(result.light.contrast, result.dark.contrast)
  result.ok = low >= READING.minContrast
  result.grade = low >= 7 ? 'clean' : result.ok ? 'readable' : 'fails'
  return result
}
