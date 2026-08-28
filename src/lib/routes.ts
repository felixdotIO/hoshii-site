import { getCollection } from 'astro:content';
import { articlePath, customerPath, policyPath } from '~/lib/paths';

/**
 * Every URL this build serves, and the last date each one genuinely changed.
 *
 * One list, used by the sitemap. It is built from the collections rather than
 * written out by hand, so a new article is in the sitemap the moment it is in
 * the repository — nobody has to remember a second step.
 *
 * `lastmod` is deliberately absent on the pages that have no content date.
 * Stamping the build time on them would tell a crawler that every page on the
 * site changed on every deploy, which is both false and the fastest way to
 * have the signal ignored.
 */
export type Route = {
  path: string;
  lastmod?: Date;
};

/** The hand-built pages, in the order a reader would meet them. */
const STATIC_ROUTES: string[] = [
  '/',
  '/order-processing/',
  '/customers/',
  '/pricing/',
  '/resources/',
  '/faq/',
  '/about/',
  '/careers/',
  '/partners/',
  '/demo/',
];

export async function indexableRoutes(): Promise<Route[]> {
  const articles = await getCollection('articles', ({ data }) => !data.draft);
  const customers = await getCollection('customers', ({ data }) => !data.draft);
  // The two contract documents opt out: they are noindex, so listing them
  // would ask a crawler to fetch a page that tells it to go away.
  const policies = await getCollection('policies', ({ data }) => data.index);

  return [
    ...STATIC_ROUTES.map((path) => ({ path })),
    ...articles.map((entry) => ({
      path: articlePath(entry),
      lastmod: entry.data.updatedAt ?? entry.data.publishedAt,
    })),
    ...customers.map((entry) => ({
      path: customerPath(entry),
      lastmod: entry.data.updatedAt ?? entry.data.publishedAt,
    })),
    ...policies.map((entry) => ({
      path: policyPath(entry),
      lastmod: entry.data.updatedAt,
    })),
  ];
}
