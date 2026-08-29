/**
 * Post-build checks, run by `npm run verify`.
 *
 * Everything here is something that broke, or nearly broke, at least once
 * during the migration, and none of it is caught by `astro check`:
 *
 *  - A social card URL that 404s because the file sits in `src/assets` and the
 *    tag points at `/assets`. Silent: the page looks fine and every share
 *    looks broken.
 *  - A duplicate title or description, which is how two pages start competing
 *    for the same query.
 *  - A heading level skipped on the way down.
 *  - React reaching a public page, which would undo the zero-JS property that
 *    the whole build is arranged around.
 *  - A redirect that does not resolve in one hop.
 *
 * Exits non-zero on any failure, so it can gate a deploy.
 */
import { readFile, readdir, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';
import { REDIRECTS } from '../src/data/redirects.ts';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const OUT = join(root, '.vercel', 'output', 'static');

const failures = [];
const fail = (msg) => failures.push(msg);

async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...(await walk(p)));
    else out.push(p);
  }
  return out;
}

const files = await walk(OUT);
const htmlFiles = files.filter((f) => f.endsWith('.html'));
const urlOf = (f) => '/' + relative(OUT, f).replace(/index\.html$/, '').replaceAll('\\', '/');

const titles = new Map();
const descriptions = new Map();
const assetRefs = new Set();
const jsBytes = new Map();

for (const file of htmlFiles) {
  const html = await readFile(file, 'utf8');
  const url = urlOf(file);

  const title = html.match(/<title>(.*?)<\/title>/s)?.[1];
  const desc = html.match(/<meta name="description" content="(.*?)"/s)?.[1];
  const canonical = html.match(/<link rel="canonical" href="(.*?)"/)?.[1];
  const h1s = html.match(/<h1[^>]*>/g) ?? [];

  if (!title) fail(`${url}: no <title>`);
  if (!desc) fail(`${url}: no meta description`);
  if (!canonical) fail(`${url}: no canonical`);
  if (h1s.length !== 1) fail(`${url}: ${h1s.length} <h1> elements, expected exactly 1`);

  const indexable = !/name="robots" content="noindex/.test(html);
  if (indexable) {
    if (title) {
      if (titles.has(title)) fail(`duplicate <title> on ${url} and ${titles.get(title)}`);
      else titles.set(title, url);
    }
    if (desc) {
      if (descriptions.has(desc)) fail(`duplicate description on ${url} and ${descriptions.get(desc)}`);
      else descriptions.set(desc, url);
    }
  }

  // Heading order: a level may never be skipped on the way down.
  let prev = 0;
  for (const m of html.matchAll(/<h([1-6])[^>]*>/g)) {
    const level = Number(m[1]);
    if (prev && level > prev + 1) {
      fail(`${url}: heading jumps h${prev} to h${level}`);
      break;
    }
    prev = level;
  }

  // Every <img> needs an alt, even an empty one.
  for (const img of html.match(/<img\b[^>]*>/g) ?? []) {
    if (!/\balt\b/.test(img)) fail(`${url}: <img> with no alt attribute`);
  }

  /**
   * A public page may carry a little inline script — the homepage needs one
   * for the scroll gate, the marquee and the typewriter — but it must never
   * pull in a framework runtime. React is installed for the Keystatic editor
   * and must stay there.
   *
   * The budget is on inline bytes, so the enhancement layer cannot quietly
   * grow into an application without someone deciding to raise the number.
   */
  for (const src of html.matchAll(/<script[^>]+src="(\/_astro\/[^"]+)"/g)) {
    fail(`${url}: loads a bundled script (${src[1]}) — public pages ship inline enhancements only`);
  }
  const inlineJs = [...html.matchAll(/<script type="module">(.*?)<\/script>/gs)]
    .reduce((n, m) => n + m[1].length, 0);
  if (inlineJs > 8000) {
    fail(`${url}: ${inlineJs} bytes of inline script, over the 8000 budget`);
  }
  jsBytes.set(url, inlineJs);

  /**
   * Pattern coverage. The decorative layer was injected by script in the
   * static build, so markup ported from it carried none — six of nine hosts
   * shipped bare and nothing complained, because a missing background looks
   * like a design choice rather than a fault.
   *
   * Every host element must therefore have a `.pat` child. `.askrow` is the
   * one that takes two, a left and a right half.
   *
   * `.doc__band` is deliberately NOT a host. The homepage's copy of the
   * original script listed it; every subpage's copy did not, and the subpages
   * are what the design was drawn against — a layer there sits in the outer
   * margin beside the content rather than behind it.
   */
  const PATTERN_HOSTS = [
    'doc__head', 'closer', 'pitch__panel', 'cap__art', 'shift__art--flow',
    'docend', 'book__pitch', 'pricehead', 'phero', 'pexplain',
  ];
  let expected = 0;
  for (const host of PATTERN_HOSTS) {
    expected += (html.match(new RegExp(`class="[^"]*\\b${host}\\b`, 'g')) ?? []).length;
  }
  // The ask row carries a half on each side.
  expected += 2 * (html.match(/class="[^"]*\baskrow\b/g) ?? []).length;
  const layers = (html.match(/class="pat[ "]/g) ?? []).length;
  if (layers !== expected) {
    fail(`${url}: ${layers} pattern layers for ${expected} hosts — a band is missing its pattern`);
  }

  for (const m of html.matchAll(/(?:src|href|content)="(\/[^"]+\.(?:jpg|jpeg|png|svg|webp|avif|woff2|xml|txt))"/g)) {
    assetRefs.add(m[1]);
  }
  for (const m of html.matchAll(/url\(&#39;(\/[^&]+)&#39;\)/g)) assetRefs.add(m[1]);
}

// Every referenced asset must exist in the output.
for (const ref of assetRefs) {
  if (!existsSync(join(OUT, ref.replace(/^\//, '')))) fail(`missing asset: ${ref}`);
}

// Internal links must resolve to a built page or a redirect.
const redirectFroms = new Set(REDIRECTS.map((r) => r.from.replace(/\/$/, '')));
for (const file of htmlFiles) {
  const html = await readFile(file, 'utf8');
  for (const m of html.matchAll(/<a\b[^>]*href="(\/[^"/][^"]*)"/g)) {
    const href = m[1].split('#')[0].split('?')[0];
    if (!href || href === '/') continue;
    const clean = href.replace(/\/$/, '');
    const ok =
      existsSync(join(OUT, clean, 'index.html')) ||
      existsSync(join(OUT, clean)) ||
      redirectFroms.has(clean);
    if (!ok) fail(`${urlOf(file)}: broken internal link ${href}`);
  }
}

// Redirects must not chain: no target may itself be a redirect source.
for (const r of REDIRECTS) {
  if (!r.to) continue;
  if (redirectFroms.has(r.to.replace(/\/$/, ''))) fail(`redirect chain: ${r.from} -> ${r.to} -> ...`);
  const target = r.to.replace(/^\//, '').replace(/\/$/, '');
  if (!existsSync(join(OUT, target, 'index.html')) && !existsSync(join(OUT, target))) {
    fail(`redirect ${r.from} points at ${r.to}, which this build does not serve`);
  }
}

// The sitemap must not list a noindex page.
const sitemap = await readFile(join(OUT, 'sitemap.xml'), 'utf8');
for (const m of sitemap.matchAll(/<loc>https?:\/\/[^/]+(\/[^<]*)<\/loc>/g)) {
  const path = m[1].replace(/^\//, '').replace(/\/$/, '');
  const file = join(OUT, path, 'index.html');
  if (!existsSync(file)) {
    fail(`sitemap lists ${m[1]}, which is not in the build`);
    continue;
  }
  if (/name="robots" content="noindex/.test(await readFile(file, 'utf8'))) {
    fail(`sitemap lists ${m[1]}, which is noindex`);
  }
}

// JSON-LD must parse, on every page that has any.
for (const file of htmlFiles) {
  const html = await readFile(file, 'utf8');
  for (const m of html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)) {
    try {
      JSON.parse(m[1]);
    } catch (err) {
      fail(`${urlOf(file)}: JSON-LD does not parse (${err.message})`);
    }
  }
}

/**
 * Walk the Vercel route table the way Vercel does, so the redirect and
 * trailing-slash behaviour is asserted rather than assumed.
 *
 * `handle: filesystem` is the important part to model: at that point Vercel
 * serves a matching file and stops, which is why /pricing/ ends there rather
 * than falling through to the 404 route below it.
 */
const vercelConfig = JSON.parse(
  await readFile(join(root, '.vercel', 'output', 'config.json'), 'utf8')
);

function resolve(path) {
  for (const route of vercelConfig.routes) {
    if (route.handle === 'filesystem') {
      const clean = path.replace(/^\//, '').replace(/\/$/, '');
      if (existsSync(join(OUT, clean, 'index.html')) || (clean && existsSync(join(OUT, clean)))) {
        return { kind: 'file', path };
      }
      continue;
    }
    if (!route.src) continue;
    let m;
    try {
      m = new RegExp(route.src).exec(path);
    } catch {
      continue;
    }
    if (!m) continue;
    if (route.continue) continue;
    if (route.headers?.Location) {
      return {
        kind: 'redirect',
        status: route.status,
        to: route.headers.Location.replace(/\$(\d)/g, (_, n) => m[Number(n)] ?? ''),
      };
    }
    if (route.dest === '_render') return { kind: 'function', path };
    if (route.status === 404) return { kind: '404' };
  }
  return { kind: 'unmatched' };
}

/** An old URL must reach its destination in one hop, in either slash form. */
for (const r of REDIRECTS) {
  for (const variant of [r.from.replace(/\/$/, ''), `${r.from.replace(/\/$/, '')}/`]) {
    const first = resolve(variant);
    if (first.kind !== 'redirect' || first.status !== 301) {
      fail(`${variant}: expected a 301, got ${first.kind}${first.status ? ' ' + first.status : ''}`);
      continue;
    }
    if (first.to !== r.to) fail(`${variant}: 301s to ${first.to}, expected ${r.to}`);
    const second = resolve(first.to);
    if (second.kind !== 'file') fail(`${variant}: lands on ${second.kind}, not a page (chain or 404)`);
  }
}

/** A page URL without its slash must be normalised, and with it must serve. */
for (const probe of ['/pricing', '/resources', '/customers/max-schwarz']) {
  const bare = resolve(probe);
  if (bare.kind !== 'redirect' || bare.status !== 308) {
    fail(`${probe}: expected a 308 to the trailing-slash form, got ${bare.kind}`);
  } else if (resolve(bare.to).kind !== 'file') {
    fail(`${probe}: 308s to ${bare.to}, which does not serve a page`);
  }
  if (resolve(`${probe}/`).kind !== 'file') fail(`${probe}/: does not serve a page`);
}

/** Keystatic must reach its function untouched — no slash normalisation. */
for (const probe of ['/api/keystatic/tree', '/keystatic', '/keystatic/collection/articles']) {
  const hit = resolve(probe);
  if (hit.kind !== 'function') {
    fail(`${probe}: expected the Keystatic function, got ${hit.kind} (the editor will not load)`);
  }
}

/** A real file keeps its exact path. */
for (const probe of ['/favicon.svg', '/robots.txt', '/sitemap.xml', '/rss.xml']) {
  if (resolve(probe).kind !== 'file') fail(`${probe}: does not serve as a file`);
}

/**
 * A keyframe nobody plays, and an animation nobody defined.
 *
 * Both halves of the same failure, and it has cost this build several rounds:
 * a block replacement in `global.css` slices between two anchors and silently
 * swallows whatever sits between them. CSS drops what it cannot match without
 * a word, so the build stays green, this script stayed green, and the only
 * symptom is a picture on the page that no longer moves. The order-processing
 * scene shipped twice with three of its four beats dead -- thirteen `desk-*`
 * keyframes defined and not one of them referenced.
 *
 * Runs on the built stylesheet, so it sees what the browser sees.
 */
{
  const cssFiles = files.filter((f) => f.endsWith('.css'));
  for (const file of cssFiles) {
    const css = await readFile(file, 'utf8');
    const defined = new Set([...css.matchAll(/@keyframes\s+([\w-]+)/g)].map((m) => m[1]));

    /* Strip the @keyframes bodies first: percentage selectors inside them can
       carry `animation-timing-function`, and a name must not count as used
       because it appears in its own definition. */
    const body = css.replace(/@keyframes\s+[\w-]+\s*\{(?:[^{}]|\{[^{}]*\})*\}/g, '');
    const used = new Set(
      [...body.matchAll(/animation(?:-name)?\s*:([^;}]*)/g)].flatMap((m) =>
        [...m[1].matchAll(/[\w-]+/g)].map((t) => t[0])
      )
    );

    /* `seq-scene-bc` is a documented spare: a scene shape kept for a host whose
       last two beats are one picture. Anything else unreferenced is a rule that
       has gone missing. */
    const SPARES = new Set(['seq-scene-bc']);
    for (const name of defined) {
      if (!used.has(name) && !SPARES.has(name)) {
        fail(`${relative(OUT, file)}: @keyframes ${name} is never referenced — the rule that played it has been deleted`);
      }
    }
    for (const name of used) {
      if (/^(?:desk|seq|lrn|hnd|mark|flow|sort|suck|learn)-/.test(name) && !defined.has(name)) {
        fail(`${relative(OUT, file)}: animation-name: ${name} has no @keyframes`);
      }
    }
  }
}

const pages = htmlFiles.length;
if (failures.length) {
  console.error(`\n${failures.length} problem(s) across ${pages} pages:\n`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}

console.log(
  `✓ ${pages} pages: titles, descriptions and canonicals unique and present; ` +
    `one h1 each; heading order intact; every image has alt; ` +
    `no framework runtime on any public page (max ${Math.max(...jsBytes.values())} bytes of inline script); ` +
    `${assetRefs.size} asset references resolve; ${REDIRECTS.length} redirects land in one hop; ` +
    `sitemap excludes noindex; JSON-LD parses; every pattern host has its layer; ` +
    `every keyframe is played and every animation is defined; ` +
    `route table resolves redirects, slashes, Keystatic and static files correctly.`
);
