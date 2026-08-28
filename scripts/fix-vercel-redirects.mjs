/**
 * Rewrites the route table in .vercel/output/config.json after the build.
 *
 * Two things have to be true at once, and the adapter cannot express both:
 *
 *   1. Every public URL ends in a slash. That is the shape the live site
 *      serves and the shape every canonical tag on this build emits, so
 *      /pricing must 308 to /pricing/ rather than answering 200 as a second
 *      copy of the same page.
 *
 *   2. /keystatic and /api/keystatic must NOT be normalised. Keystatic's
 *      editor calls its own API at `/api/keystatic/tree`, with no trailing
 *      slash and no way to configure one. Normalising that request breaks
 *      every collection in the editor.
 *
 * Astro's `trailingSlash: 'always'` gives (1) and breaks (2) — in dev as well
 * as production. `'ignore'` gives (2) and drops (1). So the config is set to
 * `'ignore'` and (1) is put back here, as a rule placed after the Keystatic
 * routes so those are already answered by the time it is reached.
 *
 * The redirect map is also repaired here. The adapter strips the trailing
 * slash from each 301 pattern, which under a normalise-first order would send
 * /blog to /blog/ and then match nothing. Making each pattern slash-tolerant
 * and putting the 301s first means every migrated URL resolves in one hop
 * whichever form arrives.
 *
 * Vercel's `src` patterns are RE2: no lookahead, which is why the Keystatic
 * exemption is expressed as ordering rather than as a negative match.
 *
 * The script asserts the shape it expects and exits non-zero if it is not
 * there, so an adapter upgrade that changes any of this fails loudly rather
 * than silently double-applying or doing nothing.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { REDIRECTS } from '../src/data/redirects.ts';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const configPath = join(root, '.vercel', 'output', 'config.json');

const config = JSON.parse(await readFile(configPath, 'utf8'));
const routes = config.routes ?? [];

const isRedirect = (r) => r.status === 301 && r.headers?.Location;
const isRender = (r) => r.dest === '_render';
const isFilesystem = (r) => r.handle === 'filesystem';

const redirects = routes.filter(isRedirect);
if (redirects.length !== REDIRECTS.length) {
  console.error(
    `Expected ${REDIRECTS.length} redirect routes, found ${redirects.length}. ` +
      `The adapter's output shape has changed — re-check this script.`
  );
  process.exit(1);
}
if (!routes.some(isFilesystem)) {
  console.error('No `handle: filesystem` route found; the ordering assumption no longer holds.');
  process.exit(1);
}

/**
 * 1. Rebuild every redirect pattern from the map, escaped.
 *
 * The adapter interpolates `from` into a regex without escaping it, and one
 * of these paths really does contain brackets — Framer slugged the
 * parenthesised subtitle straight into the URL. Unescaped, `(it-still-...)`
 * is read as a capture group, so the pattern matches the bracket-less string
 * and never matches the actual live URL. That URL then falls through to the
 * trailing-slash rule and 404s, silently, while the route looks present in
 * the config.
 *
 * Rebuilding rather than patching also fixes the missing `/?`, so each old
 * URL is answered in one hop whichever slash form arrives.
 */
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const rebuilt = REDIRECTS.flatMap((r) => {
  const from = r.from.replace(/\/$/, '');
  const route = (path) => ({
    src: `^${escapeRe(path)}/?$`,
    headers: { Location: r.to },
    status: r.status,
  });

  const routes = [route(from)];

  /**
   * Parentheses are legal unencoded in a path and that is how the live URL is
   * written, but some clients percent-encode them anyway. Both forms are the
   * same page, so both are answered rather than gambling on which arrives.
   */
  const encoded = from.replaceAll('(', '%28').replaceAll(')', '%29');
  if (encoded !== from) routes.push(route(encoded));

  return routes;
});

/**
 * 2. Add the trailing slash to anything that is a page rather than a file.
 *    `[^/.]+` at the end excludes /favicon.svg and /_astro/x.css, which are
 *    files and must keep their exact path.
 */
const normalise = {
  src: '^/((?:[^/]+/)*[^/.]+)$',
  headers: { Location: '/$1/' },
  status: 308,
};

// Order: migrated URLs, then the on-demand routes (so Keystatic is answered
// before anything can normalise it), then the slash rule, then the filesystem.
const renders = routes.filter(isRender);
const rest = routes.filter((r) => !isRedirect(r) && !isRender(r));
const filesystemAt = rest.findIndex(isFilesystem);

config.routes = [
  ...rest.slice(0, filesystemAt),
  ...rebuilt,
  ...renders,
  normalise,
  ...rest.slice(filesystemAt),
];

await writeFile(configPath, JSON.stringify(config, null, 2), 'utf8');
console.log(
  `Vercel routes rewritten: ${rebuilt.length} redirects rebuilt and escaped, ` +
    `${renders.length} on-demand routes exempted, trailing-slash rule added before the filesystem.`
);
