import type { APIRoute } from 'astro';
import { indexableRoutes } from '~/lib/routes';
import { absolute, isoDay } from '~/lib/urls';

/**
 * The sitemap, written by hand rather than by the integration, for one reason:
 * it has to be able to leave a page out. The two contract documents are
 * noindex, and a sitemap that lists a noindex URL is asking a crawler to fetch
 * a page whose only instruction is to leave.
 */
export const GET: APIRoute = async () => {
  const routes = await indexableRoutes();

  const urls = routes
    .map((route) => {
      const lastmod = route.lastmod ? `\n    <lastmod>${isoDay(route.lastmod)}</lastmod>` : '';
      return `  <url>\n    <loc>${absolute(route.path)}</loc>${lastmod}\n  </url>`;
    })
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
