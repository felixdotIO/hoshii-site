import rss from '@astrojs/rss';
import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { SITE } from '~/data/site';
import { articlePath } from '~/lib/paths';

/**
 * The article feed.
 *
 * Summaries rather than full text: the summary is the answer the piece opens
 * with, so a reader in a feed reader gets the point and a link, not a second
 * copy of the article competing with the canonical one.
 */
export const GET: APIRoute = async (context) => {
  const articles = (await getCollection('articles', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.publishedAt.getTime() - a.data.publishedAt.getTime()
  );

  return rss({
    title: `${SITE.name} — articles`,
    description:
      'Guides and answers on B2B order processing, shared inboxes and ERP integration, from the team building Hoshii in Zürich.',
    site: context.site ?? SITE.origin,
    trailingSlash: true,
    items: articles.map((article) => ({
      title: article.data.title,
      description: article.data.summary,
      pubDate: article.data.publishedAt,
      link: articlePath(article),
      categories: [article.data.category, ...article.data.tags],
    })),
    customData: `<language>${SITE.lang}</language>`,
  });
};
