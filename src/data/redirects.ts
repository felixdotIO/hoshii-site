/**
 * The migration map: every URL the live site answers on today, and what this
 * build does with it.
 *
 * Inventory taken 2026-08-27 by crawling both live sitemaps (`sitemap_en.xml`
 * and `sitemap_de.xml`): 68 URLs, all 200, last published 8 July 2026. This
 * file is the record of what happened to each one, and it is the source the
 * `.htaccess` redirect block is generated from, so the two cannot disagree.
 *
 * Rules this map follows:
 *  - A 301 only where the old page has a genuine replacement covering the same
 *    subject. A rename is a replacement; "vaguely related" is not.
 *  - No blanket catch-all to the homepage. Fifty indexed URLs pointed at `/`
 *    is a soft-404 pattern: the rankings are lost either way and the crawler
 *    is told something false in the process.
 *  - No chains. Every `to` below is a URL this build actually serves, never
 *    another entry's `from`.
 */

export type RedirectStatus = 301 | 410;

export type Redirect = {
  /** Path as the live site serves it, without the origin. */
  from: string;
  /** Path this build serves. Null means nothing replaces it. */
  to: string | null;
  status: RedirectStatus;
  notes: string;
};

/**
 * Live URLs whose content has a real home in this build. These become 301s.
 */
export const REDIRECTS: Redirect[] = [
  {
    from: '/blog',
    to: '/resources/',
    status: 301,
    notes: 'The blog index is the resources index here: same list, plus the documents. The five posts themselves are 301d individually below.',
  },
  /**
   * The five articles that were on the live blog and are now in the content
   * collection. The live paths are kept working rather than dropped: they are
   * the only URLs on this site with any accumulated authority.
   *
   * Note the first one. Framer slugged the parenthesis in the headline into
   * the URL, so the live path really does contain brackets — they have to be
   * escaped where this becomes a rewrite pattern.
   */
  {
    from: '/blog/how-b2b-wholesale-actually-works-in-2026-(it-still-starts-in-an-inbox)',
    to: '/resources/how-b2b-wholesale-actually-works-in-2026/',
    status: 301,
    notes: 'Same article. The bracketed subtitle is dropped from the slug.',
  },
  {
    from: '/blog/what-happens-when-an-ai-agent-reads-your-customer-orders',
    to: '/resources/what-happens-when-an-ai-agent-reads-your-customer-orders/',
    status: 301,
    notes: 'Same article, same slug, new section.',
  },
  {
    from: '/blog/partnership-announcement-csb-system-x-hoshii',
    to: '/resources/partnership-announcement-csb-system-x-hoshii/',
    status: 301,
    notes: 'Same article, same slug, new section.',
  },
  {
    from: '/blog/how-order-errors-drive-customer-churn-in-wholesale-distribution',
    to: '/resources/how-order-errors-drive-customer-churn-in-wholesale-distribution/',
    status: 301,
    notes: 'Same article, same slug, new section.',
  },
  {
    from: '/blog/the-hidden-cost-of-manual-order-processing-in-b2b',
    to: '/resources/the-hidden-cost-of-manual-order-processing-in-b2b/',
    status: 301,
    notes: 'Same article, same slug, new section.',
  },
  {
    from: '/policies/privacy',
    to: '/policies/privacy-policy/',
    status: 301,
    notes: 'Rename only. Same document.',
  },
  {
    from: '/policies/impressum',
    to: '/policies/imprint/',
    status: 301,
    notes: 'Rename only. Same document, English slug.',
  },
  {
    from: '/policies/cookies',
    to: '/policies/cookies-policy/',
    status: 301,
    notes: 'Rename only. Same document.',
  },
  {
    from: '/policies/faq',
    to: '/faq/',
    status: 301,
    notes: 'The FAQ was never a policy. It is a landing page here and sits at the root.',
  },
  {
    from: '/book-a-demo',
    to: '/demo/',
    status: 301,
    notes: 'Rename only. Same booking form, same HubSpot form id.',
  },
  {
    from: '/contact',
    to: '/demo/',
    status: 301,
    notes:
      'Contact was a form that booked a call. That is what /demo/ is, and it carries the sales address as the alternative.',
  },
  {
    from: '/become-a-partner',
    to: '/partners/',
    status: 301,
    notes: 'Rename only. Same partner form.',
  },
  {
    from: '/order-processing-skill',
    to: '/order-processing/',
    status: 301,
    notes:
      'Live nav’s primary product link. Framer had already renamed the node to /order-processing-agent without publishing it, so the live path is the one that has to keep working.',
  },
  {
    from: '/customers/adank-davos',
    to: '/customers/',
    status: 301,
    notes:
      'No page of its own: the Framer Content field is empty, so a page could only repeat the headline. The video plays on the customers index instead.',
  },
  {
    from: '/customers/marinello',
    to: '/customers/',
    status: 301,
    notes: 'Same as adank-davos. The video plays on the customers index.',
  },
];

/**
 * Live URLs with no replacement here. Recorded rather than redirected.
 *
 * These must be answered before hoshii.ai is pointed at this build: today they
 * would 404. A 404 is the correct answer for a page that is genuinely gone,
 * and the wrong answer for one that simply has not been written yet, which is
 * what all of these are.
 */
export const UNMIGRATED: Redirect[] = [
  ...[
    'email-triage-skill',
    'skill-library',
    'unibox',
    'outlook-add-in',
    'collaborate',
    'ai-coworker',
    'continuous-learning',
    'signals',
    'analytics',
    'erp-integration',
  ].map<Redirect>((slug) => ({
    from: `/${slug}`,
    to: null,
    status: 410,
    notes:
      'Product page not yet written for this build. Do not redirect it to the homepage: write the page, or accept losing the URL.',
  })),
  {
    from: '/de/',
    to: null,
    status: 410,
    notes:
      'The whole /de/ tree, 34 URLs, is the main traffic on the live site and has no counterpart here. German is a writing project, not a translation pass, so nothing is faked. The tree must not be 301’d to English: that is a different language, not a replacement.',
  },
];

/**
 * The Apache/LiteSpeed rewrite block, generated so it cannot drift from the
 * map above.
 *
 * `from` is a literal path, not a pattern, so every regex metacharacter in it
 * is escaped before it becomes one. Without that the brackets in the wholesale
 * article's live URL would be read as a character class and the rule would
 * silently never match the URL it was written for.
 */
function escapeRe(path: string): string {
  return path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function toHtaccess(): string {
  const patterns = REDIRECTS.map((r) => `^${escapeRe(r.from).replace(/^\\?\//, '')}/?$`);
  const width = Math.max(...patterns.map((p) => p.length)) + 2;
  return REDIRECTS.map(
    (r, i) => `  RewriteRule ${patterns[i]!.padEnd(width)} ${r.to} [R=${r.status},L]`
  ).join('\n');
}
