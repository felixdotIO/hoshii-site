import { SITE } from '~/data/site';

/**
 * A site path turned into the absolute URL that goes in a canonical tag, an
 * og:url or a sitemap entry.
 *
 * Every indexable URL on this site is a directory with a trailing slash, so
 * one function owns that shape. Two URLs that differ only by a trailing slash
 * are two URLs to a crawler, and the whole point of a canonical is to say
 * which one is meant.
 */
export function absolute(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  const clean = path.startsWith('/') ? path : `/${path}`;
  const withSlash = clean.endsWith('/') || /\.[a-z0-9]+$/i.test(clean) ? clean : `${clean}/`;
  return SITE.origin + withSlash;
}

/** The path Astro handed us, normalised the same way. */
export function pathOf(url: URL): string {
  return url.pathname.endsWith('/') || /\.[a-z0-9]+$/i.test(url.pathname)
    ? url.pathname
    : `${url.pathname}/`;
}

/**
 * A date as an ISO day, for `datetime` attributes and structured data.
 * Dates are authored as `YYYY-MM-DD` and read back in UTC, so a build running
 * in Zürich cannot shift one onto the previous day.
 */
export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** The same date, spelled out for a reader. */
export function readableDate(date: Date): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}
