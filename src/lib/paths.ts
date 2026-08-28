import type { CollectionEntry } from 'astro:content';

/**
 * Where each kind of content lives.
 *
 * One function per collection, so a URL is never spelled out twice. Every path
 * here is lowercase, hyphenated, one folder deep, and ends in a slash, which
 * is the shape `absolute()` and the sitemap both assume.
 *
 * Articles sit under `/resources/` rather than `/blog/`, because that is what
 * the nav, the footer and the index page all call the section. The live
 * `/blog/…` URLs are 301'd onto these in `~/data/redirects`.
 */
export function articlePath(article: CollectionEntry<'articles'>): string {
  return `/resources/${article.id}/`;
}

export function customerPath(story: CollectionEntry<'customers'>): string {
  return `/customers/${story.id}/`;
}

export function policyPath(policy: CollectionEntry<'policies'>): string {
  return `/policies/${policy.id}/`;
}
