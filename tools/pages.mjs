// The site's pages, as functions of the gallery's data. Plain HTML, no framework.

const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

export function pages(config) {
  const { base, origin, repo, plugin, command, title } = config
  const url = path => `${origin}${base}${path}`
  const install = `/plugin install ${plugin} --marketplace ${repo}`
  const use = id => `/${command} ${id}`
  const github = `https://github.com/${repo}`

  const icon = `<svg class="logo-mark" viewBox="0 0 16 16" aria-hidden="true" shape-rendering="crispEdges"><rect x="5" y="3" width="6" height="1"/><rect x="4" y="4" width="8" height="1"/><rect x="3" y="5" width="10" height="2"/><rect x="3" y="8" width="10" height="1"/><rect x="4" y="10" width="8" height="1"/><rect x="0" y="12" width="16" height="1"/><rect x="2" y="14" width="12" height="1"/></svg>`

  function layout({ path = '', pageTitle, description, image, body, scripts = [], jsonld }) {
    const full = pageTitle ? `${pageTitle} · ${title}` : `${title}: ${config.tagline}`
    const og = image ?? url('og/site.png')
    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(full)}</title>
<meta name="description" content="${esc(description)}">
<link rel="canonical" href="${esc(url(path))}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="${esc(title)}">
<meta property="og:title" content="${esc(pageTitle ?? title)}">
<meta property="og:description" content="${esc(description)}">
<meta property="og:url" content="${esc(url(path))}">
<meta property="og:image" content="${esc(og)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(pageTitle ?? title)}">
<meta name="twitter:description" content="${esc(description)}">
<meta name="twitter:image" content="${esc(og)}">
<meta name="theme-color" content="#f5f2ea" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0b0c14" media="(prefers-color-scheme: dark)">
<link rel="icon" href="${base}favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Silkscreen:wght@400;700&display=swap">
<link rel="stylesheet" href="${base}assets/style.css">
<script>try{var t=localStorage.getItem('bc-theme');if(t)document.documentElement.dataset.theme=t}catch(e){}</script>
${jsonld ? `<script type="application/ld+json">${JSON.stringify(jsonld).replace(/</g, '\\u003c')}</script>` : ''}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <a class="logo" href="${base}">${icon}<span>Backdrop Club</span></a>
  <nav class="nav" aria-label="Main">
    <a href="${base}#gallery">Gallery</a>
    <a href="${base}make/">Make one</a>
    <a href="${base}submit/">Submit</a>
    <a href="${base}guide/">Guide</a>
    <a href="${base}agents/">Agents</a>
    <a href="${github}" rel="noopener">GitHub</a>
  </nav>
  <button class="mode" type="button" aria-label="Switch light and dark" title="Switch light and dark"><span class="mode-sun"></span></button>
</header>
<main id="main">
${body}
</main>
<footer class="foot">
  <div class="foot-row">
    <a class="logo small" href="${base}">${icon}<span>Backdrop Club</span></a>
    <p>Community backdrops for the Claude desktop app. Free, open source, and built so your chat stays easy to read.</p>
  </div>
  <div class="foot-row fine">
    <span>An unofficial fan project, not affiliated with or endorsed by Anthropic. Claude is a trademark of Anthropic.</span>
    <span><a href="${github}">Source</a> · <a href="${github}/issues">Report a theme</a> · <a href="${base}guide/">How it works</a></span>
  </div>
</footer>
<script type="module" src="${base}assets/app.js"></script>
${scripts.map(s => `<script type="module" src="${base}assets/${s}"></script>`).join('\n')}
</body>
</html>
`
  }

  /** A window mock with the theme behind a chat: light on one side of a diagonal, dark on the other. */
  function win(theme, { view = 'split', size = '', eager = false, srcLight, srcDark } = {}) {
    const light = srcLight ?? `${base}t/${theme.id}/light.svg`
    const dark = srcDark ?? `${base}t/${theme.id}/dark.svg`
    const loading = eager ? '' : ' loading="lazy"'
    const chat = `<div class="chat" aria-hidden="true"><span class="bubble"><i style="width:62%"></i></span><i style="width:94%"></i><i style="width:88%"></i><i style="width:91%"></i><i style="width:46%"></i><span class="bubble short"><i style="width:70%"></i></span><i style="width:84%"></i><i style="width:58%"></i></div><div class="prompt" aria-hidden="true"><i></i></div>`
    return `<div class="win ${size}" data-view="${view}"><div class="half light"><img src="${esc(light)}" alt=""${loading} decoding="async">${chat}</div><div class="half dark"><img src="${esc(dark)}" alt=""${loading} decoding="async">${chat}</div></div>`
  }

  function grade(theme) {
    const s = theme.score
    if (!s) return ''
    const low = Math.min(s.light.contrast, s.dark.contrast)
    const label = low >= 7 ? 'Reads clean' : 'Readable'
    return `<span class="badge" title="Chat text keeps at least ${low}:1 contrast over this theme in light and dark mode">${label}</span>`
  }

  function card(theme) {
    const tags = theme.tags.slice(0, 3).map(t => `<span>${esc(t)}</span>`).join('')
    return `<article class="card" data-id="${esc(theme.id)}" data-name="${esc(theme.name.toLowerCase())}" data-tags="${esc(theme.tags.join(' '))}" data-author="${esc(theme.author.toLowerCase())}" data-added="${esc(theme.added)}">
  <a class="card-link" href="${base}t/${esc(theme.id)}/" aria-label="${esc(theme.name)}">${win(theme)}</a>
  <div class="card-body">
    <div class="card-title"><a href="${base}t/${esc(theme.id)}/">${esc(theme.name)}</a>${grade(theme)}</div>
    <div class="card-meta">by <a href="https://github.com/${esc(theme.author)}" rel="noopener">@${esc(theme.author)}</a><span class="tags">${tags}</span></div>
    <button class="cmd" type="button" data-copy="${esc(use(theme.id))}"><code>${esc(use(theme.id))}</code><span class="cmd-hint">Copy</span></button>
  </div>
</article>`
  }

  function steps() {
    return `<ol class="steps">
  <li><span class="step-n">1</span><div><h3>Install the loader, once</h3><p>Paste this into Claude Code. Say yes to adding the marketplace.</p><button class="cmd wide" type="button" data-copy="${esc(install)}"><code>${esc(install)}</code><span class="cmd-hint">Copy</span></button></div></li>
  <li><span class="step-n">2</span><div><h3>Pick a backdrop</h3><p>Any theme here, by name. It shows up behind your chat right away and follows light and dark mode.</p><button class="cmd wide" type="button" data-copy="${esc(use('tokyo'))}"><code>${esc(use('tokyo'))}</code><span class="cmd-hint">Copy</span></button></div></li>
  <li><span class="step-n">3</span><div><h3>Share your own</h3><p>Turn a photo into a dithered backdrop, or draw one by hand. Submit it and it joins the gallery for everyone.</p><a class="button" href="${base}make/">Make one</a></div></li>
</ol>`
  }

  function home(themes, featured) {
    const lead = featured[0] ?? themes[0]
    const tagCounts = new Map()
    for (const t of themes) for (const tag of t.tags) tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1)
    const chips = [...tagCounts].filter(([tag]) => tag !== 'dither').sort((a, b) => b[1] - a[1]).slice(0, 10)
      .map(([tag, n]) => `<button class="chip" type="button" data-tag="${esc(tag)}">${esc(tag)} <span>${n}</span></button>`).join('')
    const body = `
<section class="hero">
  <div class="hero-copy">
    <p class="eyebrow">${themes.length} free themes · light and dark</p>
    <h1>Backdrops for your <em>Claude</em> app.</h1>
    <p class="lede">Pixel-art scenes that live at the bottom of the window, so your chat stays easy to read. Install once, then switch with one command.</p>
    <div class="hero-actions">
      <button class="cmd hero-cmd" type="button" data-copy="${esc(install)}"><code>${esc(install)}</code><span class="cmd-hint">Copy</span></button>
      <div class="hero-links"><a class="button" href="#gallery">Browse the gallery</a><a class="button ghost" href="${base}make/">Make one from a photo</a></div>
      <p class="hero-agent">Using Codex, OpenCode or another agent? <a href="${base}agents/">Hand it one link</a> and it sets things up for you.</p>
    </div>
  </div>
  <div class="hero-art">
    ${win(lead, { size: 'big', eager: true })}
    <div class="hero-caption"><span>Showing <a class="hero-name" href="${base}t/${esc(lead.id)}/">${esc(lead.name)}</a></span><button class="link-button" type="button" data-cycle='${esc(JSON.stringify(featured.map(t => ({ id: t.id, name: t.name }))))}'>Next scene →</button></div>
  </div>
</section>

<section class="how" aria-labelledby="how-title">
  <h2 id="how-title" class="section-title">How it works</h2>
  ${steps()}
</section>

<section id="gallery" class="gallery" aria-labelledby="gallery-title">
  <div class="gallery-head">
    <h2 id="gallery-title" class="section-title">The gallery</h2>
    <div class="filters">
      <label class="search"><span class="visually-hidden">Search themes</span><input type="search" placeholder="Search: tokyo, desert, neon…" autocomplete="off"></label>
      <select class="sort" aria-label="Sort themes"><option value="new">Newest</option><option value="name">A to Z</option></select>
    </div>
  </div>
  <div class="chips"><button class="chip on" type="button" data-tag="">All <span>${themes.length}</span></button>${chips}</div>
  <div class="grid">
${themes.map(card).join('\n')}
  </div>
  <p class="empty" hidden>No theme matches that yet. <a href="${base}make/">Make it?</a></p>
</section>

<section class="cta">
  <div>
    <h2>Got a scene in mind?</h2>
    <p>Drop in a photo of your city, your coast, your favourite view. The maker turns it into a dithered backdrop with a light and a dark version, checks that chat stays readable over it, and helps you submit it.</p>
  </div>
  <div class="cta-actions"><a class="button" href="${base}make/">Open the maker</a><a class="button ghost" href="${base}guide/">Read the guide</a></div>
</section>`
    return layout({
      path: '',
      description: `${themes.length} free, open-source backdrop themes for the Claude desktop app: dithered pixel-art cities and landscapes in light and dark. Install once, switch with /${command}.`,
      body,
      jsonld: { '@context': 'https://schema.org', '@type': 'WebSite', name: title, url: url(''), description: config.tagline },
    })
  }

  function themePage(theme, more) {
    const s = theme.score
    const stats = [
      ['Author', `<a href="https://github.com/${esc(theme.author)}" rel="noopener">@${esc(theme.author)}</a>`],
      ['Added', esc(theme.added)],
      ['Tags', theme.tags.map(t => `<a href="${base}?tag=${encodeURIComponent(t)}#gallery">${esc(t)}</a>`).join(', ')],
      ['Licence', esc(theme.license)],
      ['Size', `${Math.round(theme.chars / 1000)} KB, vector`],
      ...(s ? [['Text contrast', `${s.light.contrast}:1 light · ${s.dark.contrast}:1 dark`]] : []),
    ]
    const shareText = `${theme.name}, a backdrop for the Claude app`
    const body = `
<section class="theme">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="${base}#gallery">Gallery</a> / <span>${esc(theme.name)}</span></nav>
  <div class="theme-grid">
    <div class="theme-art">
      ${win(theme, { size: 'big', eager: true })}
      <div class="views" role="group" aria-label="Preview mode">
        <button type="button" class="view on" data-view="split">Split</button><button type="button" class="view" data-view="light">Light</button><button type="button" class="view" data-view="dark">Dark</button>
      </div>
    </div>
    <div class="theme-info">
      <h1>${esc(theme.name)}</h1>
      <p class="lede">${esc(theme.description || 'A backdrop for the Claude app.')}</p>
      ${grade(theme)}
      <div class="use">
        <h2>Use it</h2>
        <p>Already have the loader? Paste this into Claude Code:</p>
        <button class="cmd wide" type="button" data-copy="${esc(use(theme.id))}"><code>${esc(use(theme.id))}</code><span class="cmd-hint">Copy</span></button>
        <p class="small">First time? Install the loader once:</p>
        <button class="cmd wide" type="button" data-copy="${esc(install)}"><code>${esc(install)}</code><span class="cmd-hint">Copy</span></button>
      </div>
      <div class="theme-actions">
        <a class="button ghost" href="${base}t/${esc(theme.id)}/backdrop.svg" download="${esc(theme.id)}.svg">Download SVG</a>
        <a class="button ghost" href="https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&amp;url=${encodeURIComponent(url(`t/${theme.id}/`))}" rel="noopener">Share on X</a>
        <button class="button ghost" type="button" data-copy="${esc(url(`t/${theme.id}/`))}" data-done="Link copied">Copy link</button>
      </div>
      <dl class="stats">${stats.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
    </div>
  </div>
</section>
${more.length ? `<section class="gallery more"><h2 class="section-title">More backdrops</h2><div class="grid">${more.map(card).join('\n')}</div></section>` : ''}`
    return layout({
      path: `t/${theme.id}/`,
      pageTitle: `${theme.name}: a Claude app backdrop`,
      description: `${theme.description || theme.name} A free backdrop theme for the Claude desktop app by @${theme.author}, with light and dark versions. Use it with ${use(theme.id)}.`,
      image: theme.hasOg ? url(`og/${theme.id}.png`) : undefined,
      body,
      jsonld: {
        '@context': 'https://schema.org', '@type': 'CreativeWork', name: theme.name, description: theme.description,
        author: { '@type': 'Person', name: theme.author, url: `https://github.com/${theme.author}` },
        dateCreated: theme.added, license: theme.license, url: url(`t/${theme.id}/`),
        ...(theme.hasOg ? { image: url(`og/${theme.id}.png`) } : {}),
      },
    })
  }

  function makePage() {
    const body = `
<section class="tool">
  <div class="tool-head">
    <p class="eyebrow">The maker</p>
    <h1>Turn a photo into a backdrop.</h1>
    <p class="lede">Your picture is dithered into chunky pixels along the bottom of the window, once for light mode and once for dark. Nothing is uploaded: it all happens in this page.</p>
  </div>
  <div class="tool-grid">
    <form class="panel maker-form" autocomplete="off">
      <label class="drop" tabindex="0"><input type="file" accept="image/*" hidden><strong>Choose a photo</strong><span>or drop one here. Wide shots of skylines, coasts and mountains work best.</span></label>
      <div class="field"><span class="label">Style</span><div class="seg" role="radiogroup"><label><input type="radio" name="mode" value="silhouette" checked><span>Silhouette</span></label><label><input type="radio" name="mode" value="photo"><span>Photo</span></label></div></div>
      <div class="field"><span class="label">Colours</span><div class="swatches" role="radiogroup"></div></div>
      <label class="field"><span class="label">Height <output data-for="height"></output></span><input type="range" name="height" min="22" max="42" value="32"></label>
      <label class="field"><span class="label">Framing <output data-for="focus"></output></span><input type="range" name="focus" min="0" max="100" value="60"></label>
      <label class="field silhouette-only"><span class="label">Skyline cut <output data-for="cut"></output></span><input type="range" name="cut" min="5" max="95" value="50"></label>
      <div class="field"><span class="label">Pixels</span><div class="seg" role="radiogroup"><label><input type="radio" name="detail" value="128"><span>Chunky</span></label><label><input type="radio" name="detail" value="256" checked><span>Fine</span></label></div></div>
      <label class="check"><input type="checkbox" name="stars" checked><span>Stars at night</span></label>
      <label class="check silhouette-only"><input type="checkbox" name="lights" checked><span>Window lights at night</span></label>
    </form>
    <div class="tool-out">
      <div class="maker-preview">${win({ id: 'preview' }, { size: 'big', eager: true, srcLight: `${base}t/${config.defaultTheme}/light.svg`, srcDark: `${base}t/${config.defaultTheme}/dark.svg` })}</div>
      <div class="views" role="group" aria-label="Preview mode"><button type="button" class="view on" data-view="split">Split</button><button type="button" class="view" data-view="light">Light</button><button type="button" class="view" data-view="dark">Dark</button></div>
      <div class="report" aria-live="polite"><p class="muted">Choose a photo to start. The example above is one of the gallery's scenes.</p></div>
      <div class="tool-actions"><button class="button" type="button" data-action="submit" disabled>Submit to the gallery</button><button class="button ghost" type="button" data-action="download" disabled>Download SVG</button><button class="button ghost" type="button" data-action="sample">Try a sample</button></div>
    </div>
  </div>
</section>`
    return layout({
      path: 'make/',
      pageTitle: 'Make a backdrop from a photo',
      description: 'Turn any photo into a dithered pixel-art backdrop for the Claude desktop app, with light and dark versions and a built-in readability check. Free, in your browser.',
      body,
      scripts: ['maker.js'],
    })
  }

  function submitPage() {
    const body = `
<section class="tool">
  <div class="tool-head">
    <p class="eyebrow">Submit</p>
    <h1>Add your backdrop to the gallery.</h1>
    <p class="lede">Check your theme here first. When it passes, the page copies it and opens a short form on GitHub. A bot turns your entry into a pull request, and once it is merged your theme is live for everyone.</p>
  </div>
  <div class="tool-grid">
    <form class="panel submit-form" autocomplete="off">
      <label class="drop" tabindex="0"><input type="file" accept=".svg,image/svg+xml" hidden><strong>Choose an SVG</strong><span>or drop it here, or <button type="button" class="link-button" data-action="paste">paste its code</button>.</span></label>
      <textarea class="paste" name="svg" rows="5" placeholder="&lt;svg xmlns=&quot;http://www.w3.org/2000/svg&quot; viewBox=&quot;0 0 512 160&quot; …" hidden></textarea>
      <label class="field"><span class="label">Name</span><input type="text" name="name" maxlength="40" placeholder="Harbour at dusk" required></label>
      <label class="field"><span class="label">One line about it</span><input type="text" name="description" maxlength="200" placeholder="Cranes and container ships under a pink sky."></label>
      <label class="field"><span class="label">Tags</span><input type="text" name="tags" placeholder="city, sea, sunset"></label>
      <label class="check"><input type="checkbox" name="rights"><span>I made this art, or have the right to share it, and I license it under CC BY 4.0.</span></label>
    </form>
    <div class="tool-out">
      <div class="submit-preview">${win({ id: 'preview' }, { size: 'big', eager: true, srcLight: `${base}t/${config.defaultTheme}/light.svg`, srcDark: `${base}t/${config.defaultTheme}/dark.svg` })}</div>
      <div class="views" role="group" aria-label="Preview mode"><button type="button" class="view on" data-view="split">Split</button><button type="button" class="view" data-view="light">Light</button><button type="button" class="view" data-view="dark">Dark</button></div>
      <div class="report" aria-live="polite"><p class="muted">Add a theme to check it. You need a GitHub account to submit.</p></div>
      <div class="tool-actions"><button class="button" type="button" data-action="submit" disabled>Copy and open GitHub</button></div>
      <ol class="after" hidden><li>Your theme is copied.</li><li>On GitHub, click into <strong>Theme file</strong> and paste.</li><li>Press <strong>Create</strong>. The bot replies within a minute or two.</li></ol>
    </div>
  </div>
</section>`
    return layout({
      path: 'submit/',
      pageTitle: 'Submit a backdrop',
      description: 'Share your backdrop theme for the Claude desktop app. Check it for readability in light and dark mode, then submit it to the Backdrop Club gallery.',
      body,
      scripts: ['submit.js'],
    })
  }

  function guidePage(starter) {
    const body = `
<article class="prose">
  <p class="eyebrow">Guide</p>
  <h1>How backdrops work, and how to make one.</h1>
  <p class="lede">A backdrop is one SVG file that the Claude desktop app draws behind your conversation. The loader mod from this site fetches the one you pick and keeps it across sessions.</p>

  <h2 id="install">Install</h2>
  <p>In Claude Code (the desktop app's Code tab, or a terminal), paste:</p>
  <button class="cmd wide" type="button" data-copy="${esc(install)}"><code>${esc(install)}</code><span class="cmd-hint">Copy</span></button>
  <p>Answer yes to adding the marketplace and pick where to install it. Start a new session and send a message: the default scene appears. Then:</p>
  <ul>
    <li><code>/${command} tokyo</code>: switch to a theme from the gallery, by its id or name.</li>
    <li><code>/${command} random</code>: a surprise.</li>
    <li><code>/${command} list</code>: every theme, or <code>/${command} list city</code> for one tag.</li>
    <li><code>/${command} off</code> and <code>/${command} on</code>: hide it and bring it back.</li>
  </ul>
  <p>Your pick is remembered across sessions. Only one backdrop shows at a time, so if you use another theme mod, turn one of them off.</p>

  <h2 id="rules">The rules every theme follows</h2>
  <p>The gallery exists because a busy backdrop makes a chat hard to read. Every submission is checked by machine, then by a person.</p>
  <ol>
    <li><strong>The middle stays clear.</strong> Put the scene in the bottom third of the window. Above that, only sky, haze and a few thin tops.</li>
    <li><strong>Text keeps its contrast.</strong> The check renders your theme at three window sizes and measures the darkest 1% of where chat text sits. It needs at least 4.5:1 in both modes; 7:1 earns <span class="badge">Reads clean</span>.</li>
    <li><strong>Light and dark.</strong> Use a <code>@media (prefers-color-scheme: dark)</code> rule to switch looks. Pale, soft colours for light mode; dark ones for dark mode, with bright colours only as small accents low down.</li>
    <li><strong>Still and self-contained.</strong> No animation, scripts, fonts, or links to other files. Vector shapes, gradients, patterns and filters are fine.</li>
    <li><strong>Small.</strong> At most 120,000 characters.</li>
    <li><strong>Yours.</strong> Only art you made or have the right to share. Themes are published under CC BY 4.0 unless you say otherwise.</li>
  </ol>

  <h2 id="by-hand">Make one by hand</h2>
  <p>Use a wide <code>viewBox</code> (512 by 160 works well) with <code>preserveAspectRatio="xMidYMax slice"</code>: the scene scales to the window's height, sits on its bottom edge, and the sides are cropped on narrow windows. Keep the subject between x 140 and 372 so it survives the crop. Start from this:</p>
  <div class="code"><button class="cmd-hint copy-code" type="button" data-copy="${esc(starter)}">Copy</button><pre><code>${esc(starter)}</code></pre></div>
  <p>Then check it on the <a href="${base}submit/">Submit page</a>, which previews it in both modes and runs the same check the gallery does.</p>

  <h2 id="faq">Questions</h2>
  <h3>Is this made by Anthropic?</h3>
  <p>No. It is a community project that uses the theme support built into Claude Code mods.</p>
  <h3>Is it safe to install?</h3>
  <p>The loader is a small open-source mod. Themes are data, not code: every file is checked against an allow-list of drawing elements before it is published, checked again by the loader before it is drawn, and the app draws it in a sandbox with scripts off.</p>
  <h3>Does it slow Claude down?</h3>
  <p>No. A theme is one still picture, drawn once.</p>
  <h3>Can I use a theme somewhere else?</h3>
  <p>Yes, each theme page has a Download SVG button. Keep the author's credit.</p>
</article>`
    return layout({
      path: 'guide/',
      pageTitle: 'Guide: install and make Claude app backdrops',
      description: 'How to install backdrop themes in the Claude desktop app, and how to make your own: the rules, a starter SVG, and the readability check.',
      body,
    })
  }

  function agentsPage() {
    const npx = `npx -y github:${repo}`
    const prompt = `Read ${url('llms.txt')} then show me the Backdrop Club backdrops with their preview images, and set up the one I pick in my Claude app.`
    const agents = [
      ['Claude Code', `<p>Install the loader once:</p><button class="cmd wide" type="button" data-copy="${esc(install)}"><code>${esc(install)}</code><span class="cmd-hint">Copy</span></button><p>Then just ask: <em>"find me a backdrop with mountains"</em>. Claude gets two tools for it, <code>find_backdrops</code> and <code>set_backdrop</code>. Or type <code>/${command} &lt;name&gt;</code>.</p>`],
      ['Codex', `<p>Paste the prompt above. Codex runs the <code>npx</code> commands in its shell; if its sandbox blocks network access, approve it for this command.</p>`],
      ['OpenCode', `<p>Paste the prompt above, or tell it to run <code>${esc(npx)} list</code>. It uses its bash tool, and asks before anything that needs permission.</p>`],
      ['Gemini CLI', `<p>Paste the prompt above. It reads the guide with its web fetch tool and runs the commands with its shell tool.</p>`],
      ['Cursor, Windsurf, Cline', `<p>Paste the prompt into the agent chat. The commands run in the editor's terminal.</p>`],
      ['Anything else', `<p>Any agent that can read a web page and run a shell command can do it. One without a shell can give you the two lines to paste into Claude Code.</p>`],
    ]
    const rows = [
      ['list [--tag city]', 'every theme, with preview links'],
      ['search mountains', 'themes matching some words'],
      ['show tokyo', 'one theme in detail'],
      ['setup', 'install the loader in Claude Code, once'],
      ['use tokyo', 'make it the backdrop; an open session switches in seconds'],
      ['use random', 'a surprise'],
      ['current / off / on', "what's showing; hide it; bring it back"],
      ['download tokyo --out .', 'save the SVG to use elsewhere'],
      ['check my.svg', "the gallery's rules and readability score"],
      ['submit my.svg --name "Harbour"', 'share it; shows a preview until you add --yes'],
    ]
    const body = `
<article class="prose wide">
  <p class="eyebrow">For agents</p>
  <h1>Let your agent do it.</h1>
  <p class="lede">Give any coding agent one link. It shows you the backdrops, installs the one you pick, and switches it whenever you ask. You never touch a file.</p>
  <div class="prompt-box">
    <p class="label">Paste this to your agent</p>
    <button class="cmd wide tall" type="button" data-copy="${esc(prompt)}"><code>${esc(prompt)}</code><span class="cmd-hint">Copy</span></button>
    <p class="small">The guide it reads: <a href="${base}llms.txt">llms.txt</a>. Plain text, written for agents.</p>
  </div>

  <h2 id="by-agent">By agent</h2>
  <div class="agent-grid">${agents.map(([n, b]) => `<section class="agent-card"><h3>${esc(n)}</h3>${b}</section>`).join('')}</div>

  <h2 id="cli">The command line</h2>
  <p>No install: Node 18 or newer runs it straight from GitHub. Every command takes <code>--json</code>.</p>
  <button class="cmd wide" type="button" data-copy="${esc(npx)} list"><code>${esc(npx)} list</code><span class="cmd-hint">Copy</span></button>
  <table class="cli-table"><thead><tr><th>Command</th><th>What it does</th></tr></thead><tbody>${rows.map(([c, d]) => `<tr><td><code>${esc(c)}</code></td><td>${esc(d)}</td></tr>`).join('')}</tbody></table>
  <p>The loader and the command line share one small file, <code>~/.config/backdrop-club/current.json</code>, so a pick made either way shows up in the app.</p>

  <h2 id="api">The JSON API</h2>
  <p>Read-only, no key, served from GitHub Pages:</p>
  <ul>
    <li><a href="${base}api/index.json"><code>api/index.json</code></a>: every theme's id, name, author, description and tags</li>
    <li><code>api/themes/&lt;id&gt;.json</code>: one theme, with its SVG</li>
    <li><code>t/&lt;id&gt;/backdrop.svg</code>, <code>light.svg</code>, <code>dark.svg</code>, and <code>og/&lt;id&gt;.png</code> for a preview</li>
  </ul>

  <h2 id="contributing">Agents that make themes</h2>
  <p>An agent can draw a theme, check it with <code>check</code>, and submit it with <code>submit</code> once you say yes. Working inside the repository? <a href="${github}/blob/main/AGENTS.md">AGENTS.md</a> has the details.</p>
</article>`
    return layout({
      path: 'agents/',
      pageTitle: 'Use Backdrop Club with Claude Code, Codex, OpenCode and other agents',
      description: 'Give your coding agent one link and it installs a Claude app backdrop for you. A no-install command line, an llms.txt guide and a JSON API, for Claude Code, Codex, OpenCode, Gemini CLI and Cursor.',
      body,
    })
  }

  function notFound() {
    return layout({ path: '404.html', pageTitle: 'Not found', description: 'This page is not here.', body: `<section class="prose"><h1>Nothing here.</h1><p>That page doesn't exist, or the theme was renamed. <a href="${base}#gallery">Back to the gallery</a>.</p></section>` })
  }

  return { home, themePage, makePage, submitPage, guidePage, agentsPage, notFound, layout }
}
