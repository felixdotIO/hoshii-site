// @ts-check
import { defineConfig, envField } from 'astro/config';
import markdoc from '@astrojs/markdoc';
import react from '@astrojs/react';
import keystatic from '@keystatic/astro';
import vercel from '@astrojs/vercel';
import { REDIRECTS } from './src/data/redirects.ts';

/**
 * Static by default, with exactly two exceptions.
 *
 * Every page a visitor or a crawler sees is prerendered to HTML at build time
 * and ships no framework runtime. The adapter is here only so that Keystatic's
 * editor and its GitHub API routes — `/keystatic` and `/api/keystatic/*` —
 * can run on demand. Those are the only routes that are not static, they are
 * behind a login, and they are `noindex`.
 *
 * React is likewise present only for the editor. It is never imported by a
 * public page, so nothing on the marketing site ships it. `npm run verify`
 * asserts that, because it is the kind of thing that silently stops being
 * true.
 */
export default defineConfig({
  site: 'https://www.hoshii.ai',

  // Static output; individual routes opt out with `prerender = false`. The
  // adapter turns those into Vercel functions and leaves everything else as
  // files on the CDN.
  output: 'static',
  adapter: vercel({ imageService: false }),

  integrations: [markdoc(), react(), keystatic()],

  /**
   * The three secrets Keystatic's GitHub mode needs, declared rather than read
   * loose off `process.env`.
   *
   * Declaring them is not optional housekeeping: `@keystatic/astro` imports
   * `astro:env/server`, and without a schema that virtual module does not
   * exist, so the editor fails to build with an unresolved-import error that
   * names esbuild rather than the real cause.
   *
   * All three are `context: 'server', access: 'secret'`, so none is ever
   * bundled into anything a browser receives. They are optional because local
   * development runs Keystatic in `local` mode and needs none of them; they
   * are required only once it is talking to GitHub.
   */
  env: {
    schema: {
      KEYSTATIC_GITHUB_CLIENT_ID: envField.string({
        context: 'server',
        access: 'secret',
        optional: true,
      }),
      KEYSTATIC_GITHUB_CLIENT_SECRET: envField.string({
        context: 'server',
        access: 'secret',
        optional: true,
      }),
      KEYSTATIC_SECRET: envField.string({
        context: 'server',
        access: 'secret',
        optional: true,
      }),
      PUBLIC_KEYSTATIC_GITHUB_APP_SLUG: envField.string({
        context: 'client',
        access: 'public',
        optional: true,
      }),
    },
  },

  /**
   * The migration map, straight from `src/data/redirects.ts`.
   *
   * The adapter turns these into real 308/301 routes at the edge, so there is
   * no meta-refresh page and no second hop. Importing the map rather than
   * restating it here is the point: the record of what happened to each live
   * URL and the thing that actually serves the redirect are one file.
   *
   * `from` is written with the trailing slash to match, because the trailing
   * -slash rule runs first and a redirect defined without one would never be
   * reached.
   */
  redirects: Object.fromEntries(
    REDIRECTS.map((r) => [
      r.from.endsWith('/') ? r.from : `${r.from}/`,
      { status: r.status, destination: r.to },
    ])
  ),

  /**
   * Every indexable URL still ends in a slash — `build.format: 'directory'`
   * writes `pricing/index.html`, every link in the markup is written with the
   * slash, and every canonical tag emits it. That is the shape the live site
   * serves and none of it moves.
   *
   * What is *not* set is `trailingSlash: 'always'`, and that is deliberate.
   * Keystatic's editor calls its own API at `/api/keystatic/tree`, with no
   * trailing slash and no way to configure one. Under `'always'` Astro
   * refuses those requests outright, so the editor loads and then fails to
   * read any collection — in dev as well as in production.
   *
   * So the canonical shape is enforced one layer out instead:
   * `scripts/fix-vercel-redirects.mjs` writes a 308 into the Vercel config
   * that adds the slash to everything except the two Keystatic routes. The
   * public site behaves exactly as before; the editor is exempt.
   */
  trailingSlash: 'ignore',
  build: { format: 'directory' },

  image: {
    // Only local files are ever optimised; nothing is fetched at build time.
    domains: [],
  },

  // The stylesheet is one file and is needed by every page, so leaving it as a
  // single request beats splitting it per route.
  vite: {
    build: {
      cssCodeSplit: false,
    },
    optimizeDeps: {
      // `@keystatic/astro` imports `astro:env/server`, a virtual module
      // esbuild cannot resolve while pre-bundling. Excluding it leaves that
      // import to Vite, which is the only thing that knows what it is.
      //
      // Only that package. `@keystatic/core` must stay in the pre-bundle: it
      // depends on CommonJS packages (lodash among them), and excluding it too
      // leaves those unconverted, so the editor fails to hydrate on a missing
      // default export instead.
      exclude: ['@keystatic/astro'],
    },
  },
});
