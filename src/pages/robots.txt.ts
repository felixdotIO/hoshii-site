import type { APIRoute } from 'astro';
import { absolute } from '~/lib/urls';

/**
 * robots.txt.
 *
 * Deliberately permissive, including to the answer engines: Hoshii is a new
 * domain with no authority, and being quotable in an AI answer is worth more
 * to it right now than withholding the text. The crawlers are named rather
 * than left to the wildcard so that the decision is visible and can be
 * reversed one line at a time.
 *
 * The two contract documents are excluded here as well as by their meta
 * robots tag, so a crawler that never fetches them is told the same thing as
 * one that does.
 */
export const GET: APIRoute = () => {
  const body = `# https://www.hoshii.ai/

User-agent: *
Allow: /
Disallow: /policies/msa/
Disallow: /policies/sls/

# Answer engines. Allowed on purpose — see the note in this file's source.
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: ${absolute('/sitemap.xml')}
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
