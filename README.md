# hoshii.ai

The Hoshii website: Astro, TypeScript, static output, Keystatic for authoring.

Every public page is HTML generated at build time and ships **no JavaScript**
except two small inline enhancements on the homepage and the resources index —
both on content that is already in the initial response. Nothing important
needs a script to appear.

```bash
npm install
npm run dev       # site on :4321, editor on :4321/keystatic
npm run build     # static build + Vercel route table
npm run verify    # post-build checks (see below)
npm run check     # TypeScript and Astro diagnostics
```

---

## Publishing

Content lives in `src/content/` as files in the repository. There is no
database and no content API: a save is a git commit, a push is a deploy.

**In production**, open `https://www.hoshii.ai/keystatic`, sign in with GitHub,
write, and press Save. That commits to this repository, which triggers a Vercel
build, and the page is live about a minute later.

**Locally**, `npm run dev` then `http://localhost:4321/keystatic`. No login and
no GitHub app: the editor reads and writes the files on disk directly, so you
can draft, look at the real page next door, and commit when you are happy.

| What you are writing | Where it goes in the editor | URL it publishes to |
| --- | --- | --- |
| Blog post | Articles | `/resources/<slug>/` |
| Case study | Customer stories | `/customers/<slug>/` |
| A question and its answer | Questions & answers | whichever page the group names |
| Legal document | Policies | `/policies/<slug>/` |

Tick **Draft** on anything not ready. A draft is not built at all, so its URL
cannot be reached or indexed — it is not a hidden page, it is no page.

### Two rules worth knowing

**Changing a slug breaks links.** The slug is the URL. Renaming one on a
published piece orphans every link and every ranking it has. If it genuinely
has to move, add the old path to `src/data/redirects.ts` in the same commit.

**The meta description is required and must be unique.** The schema enforces
50–170 characters, and `npm run verify` fails the build if two pages share one.
Write it for a search result: one sentence, saying what the page is.

---

## How it is put together

```
src/
  components/    Header, Footer, Breadcrumbs, Seo, cards, CTAs, FAQ, TOC…
  layouts/       BaseLayout (the document) → DocLayout (the page shape) → ArticleLayout
  pages/         one file per route; [slug].astro for the collections
  content/       the content itself, and the only thing an author edits
  data/          site facts, nav, team, jobs, clients, the redirect map
  lib/           schema.org builders, URL helpers, the route list
  styles/        one stylesheet, one request
```

Three layers, each wrapping the last, so a page supplies content and nothing
else. `DocLayout` is why "one masthead everywhere" holds: the trail, the head
metadata, the Organization and WebSite nodes and the BreadcrumbList are all
built there from the same values, and a page cannot forget one.

### Structured data

`src/lib/schema.ts` builds the JSON-LD, under one rule: **it restates what a
visitor can see and never adds to it.** There are no ratings, review counts,
employee numbers or award claims anywhere, because none appear on any page.
Where a value would have to be guessed, the property is left out.

`FAQPage` is emitted on exactly three pages — `/faq/`, `/pricing/` and
`/order-processing/` — each of which visibly is a list of questions and
answers, and it is built from the same collection entries the page renders, so
the two cannot disagree.

### The redirect map

`src/data/redirects.ts` is the record of what happened to every URL the live
site answers on, and it is also what serves the redirects: `astro.config.mjs`
imports it. The two cannot drift because they are one file.

Fifty live URLs — eleven product pages and the whole 34-URL German tree — have
**no page here** and are listed as unmigrated rather than redirected. Sending
them to the homepage would be a soft-404 pattern: the rankings are lost either
way and the crawler is told something false in the process. They need pages
written, or accepting as lost. **German is the main traffic**, so that tree is
the largest single piece of work outstanding.

---

## Checks

`npm run verify` runs after a build and fails on anything below. Every one of
these is something that broke, or nearly broke, during the migration, and none
is caught by `astro check`:

- a missing or duplicated title, description or canonical
- more than one `<h1>`, or a heading level skipped on the way down
- an `<img>` with no `alt` (an empty one is fine and means decorative)
- a social-card or asset URL that 404s
- a broken internal link
- **any JavaScript on a public page**
- a redirect that chains, points at a page this build does not serve, or fails
  to resolve in one hop in either slash form
- a `noindex` page listed in the sitemap
- JSON-LD that does not parse

It also walks the generated Vercel route table the way Vercel does — including
the filesystem phase — and asserts that old URLs 301 in one hop, that page URLs
without a slash 308 to the slashed form, that the Keystatic routes are reached
untouched, and that real files keep their exact path.

Run it before every deploy.

---

## Deployment

Vercel, building on push. `output: 'static'` with the Vercel adapter: every
public page is a file on the CDN, and the only functions are Keystatic's editor
and its GitHub API routes.

Set these environment variables in the Vercel project (all three are secrets,
and none is needed for local development):

```
KEYSTATIC_GITHUB_CLIENT_ID
KEYSTATIC_GITHUB_CLIENT_SECRET
KEYSTATIC_SECRET
PUBLIC_KEYSTATIC_GITHUB_APP_SLUG
```

They come from a GitHub App created for this repository; Keystatic's setup flow
at `/keystatic` walks through making one. Also set `repo` in
`keystatic.config.ts` to the repository this actually deploys from.

### Two things to know about the config

**`trailingSlash` is `'ignore'`, not `'always'`.** Keystatic calls its own API
at `/api/keystatic/tree`, with no trailing slash and no way to configure one;
under `'always'` Astro refuses those requests and every collection in the
editor fails to load. So the canonical trailing slash is enforced one layer out
instead — `scripts/fix-vercel-redirects.mjs` writes a 308 into the Vercel route
table, placed after the Keystatic routes so those are already answered. Public
URLs behave exactly as they did.

**`scripts/fix-vercel-redirects.mjs` is load-bearing.** It rebuilds the
redirect routes from the map with regex escaping, because the adapter
interpolates paths into patterns unescaped — and one live URL really does
contain brackets, which unescaped are read as a capture group so the rule never
matches the URL it was written for. The script asserts the shape it expects and
exits non-zero if the adapter's output changes, rather than silently doing
nothing.

---

## Not done

- **The German tree.** 34 live URLs, and the main traffic. Astro's i18n routing
  plus a `de` variant of each collection is the shape; the writing is the work,
  and it is writing rather than translation given the works-council and GDPR
  nuance in the copy.
- **Eleven product pages** that exist live and not here (`/unibox`,
  `/erp-integration`, `/analytics` and the rest). Listed in
  `src/data/redirects.ts`.
- **Analytics.** Nothing is installed. Plausible or Fathom rather than GA4,
  given the DACH audience.
