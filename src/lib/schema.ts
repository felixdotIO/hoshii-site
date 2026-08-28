import { SITE, AUTHORS, type AuthorId } from '~/data/site';
import { absolute } from '~/lib/urls';

/**
 * schema.org JSON-LD, built from the same values the page renders.
 *
 * The rule this file exists to enforce: structured data restates what a
 * visitor can see, and never adds to it. There are no ratings, no review
 * counts, no employee numbers and no award claims here, because none of those
 * appear on any page. Where a value would have to be guessed, the property is
 * left out instead.
 */

type Json = Record<string, unknown>;

const ORG_ID = `${SITE.origin}/#organization`;
const SITE_ID = `${SITE.origin}/#website`;

/** The company. Emitted once per page, referenced by @id from everything else. */
export function organization(): Json {
  return {
    '@type': 'Organization',
    '@id': ORG_ID,
    name: SITE.name,
    legalName: SITE.legalName,
    url: `${SITE.origin}/`,
    logo: absolute(SITE.logo),
    description: SITE.description,
    foundingDate: SITE.foundingDate,
    address: {
      '@type': 'PostalAddress',
      addressLocality: SITE.city,
      addressCountry: SITE.country,
    },
    contactPoint: [
      {
        '@type': 'ContactPoint',
        contactType: 'sales',
        email: SITE.email.sales,
        availableLanguage: ['en', 'de'],
      },
      {
        '@type': 'ContactPoint',
        contactType: 'customer support',
        email: SITE.email.support,
        availableLanguage: ['en', 'de'],
      },
    ],
    knowsAbout: [...SITE.knowsAbout],
  };
}

export function website(): Json {
  return {
    '@type': 'WebSite',
    '@id': SITE_ID,
    url: `${SITE.origin}/`,
    name: SITE.name,
    publisher: { '@id': ORG_ID },
    inLanguage: SITE.lang,
  };
}

/**
 * The product. `offers` carries no price because no price is published: the
 * page says it is quoted per workspace, and the schema says the same.
 */
export function softwareApplication(): Json {
  return {
    '@type': 'SoftwareApplication',
    '@id': `${SITE.origin}/#product`,
    name: SITE.name,
    applicationCategory: 'BusinessApplication',
    applicationSubCategory: 'AI inbox for B2B operations',
    operatingSystem: 'Web',
    url: `${SITE.origin}/`,
    publisher: { '@id': ORG_ID },
    description:
      'An AI-native shared inbox for order desks, sales, service and finance teams. It classifies inbound mail, pulls context from the ERP, and prepares the order or reply for approval.',
    offers: {
      '@type': 'Offer',
      availability: 'https://schema.org/InStock',
      priceSpecification: {
        '@type': 'PriceSpecification',
        priceCurrency: 'EUR',
        valueAddedTaxIncluded: false,
        description:
          'Quoted per workspace, based on mail volume, number of inboxes and which systems Hoshii writes into.',
      },
      url: absolute('/pricing/'),
    },
  };
}

export type Crumb = { label: string; href: string };

/**
 * BreadcrumbList. Emitted only where the page actually shows a breadcrumb
 * trail, since the schema is meant to describe the visible one.
 */
export function breadcrumbs(trail: Crumb[]): Json {
  return {
    '@type': 'BreadcrumbList',
    itemListElement: trail.map((crumb, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: crumb.label,
      item: absolute(crumb.href),
    })),
  };
}

export type QA = { question: string; answer: string };

/**
 * FAQPage, from the question and answer pairs the page renders.
 *
 * Google restricts rich results for FAQPage to authoritative government and
 * health sites, so this is not here for a rich result. It is here because it
 * is an accurate machine description of a page that genuinely is a list of
 * questions and answers, and answer engines read it as one. It is emitted
 * only on the pages that visibly are that, never bolted onto a page with a
 * couple of questions at the bottom.
 */
export function faqPage(pairs: QA[]): Json {
  return {
    '@type': 'FAQPage',
    mainEntity: pairs.map((pair) => ({
      '@type': 'Question',
      name: pair.question,
      acceptedAnswer: { '@type': 'Answer', text: pair.answer },
    })),
  };
}

export function person(id: AuthorId): Json {
  const author = AUTHORS[id];
  return {
    '@type': 'Person',
    '@id': `${SITE.origin}/#author-${id}`,
    name: author.name,
    description: author.bio,
    url: absolute(author.url),
    worksFor: { '@id': ORG_ID },
  };
}

export type ArticleSchemaInput = {
  headline: string;
  description: string;
  path: string;
  published: Date;
  updated?: Date | undefined;
  author: AuthorId;
  image?: string | undefined;
  section?: string | undefined;
  keywords?: readonly string[] | undefined;
};

export function blogPosting(input: ArticleSchemaInput): Json {
  const schema: Json = {
    '@type': 'BlogPosting',
    '@id': `${absolute(input.path)}#article`,
    headline: input.headline,
    description: input.description,
    url: absolute(input.path),
    mainEntityOfPage: absolute(input.path),
    datePublished: input.published.toISOString(),
    dateModified: (input.updated ?? input.published).toISOString(),
    author: { '@id': `${SITE.origin}/#author-${input.author}` },
    publisher: { '@id': ORG_ID },
    inLanguage: SITE.lang,
    isPartOf: { '@id': SITE_ID },
  };
  if (input.image) schema.image = absolute(input.image);
  if (input.section) schema.articleSection = input.section;
  if (input.keywords?.length) schema.keywords = [...input.keywords];
  return schema;
}

/**
 * A customer story. Article rather than BlogPosting: these are cases we
 * publish about a named company, not dated editorial, and `about` names the
 * organisation the piece is about.
 */
export function caseStudy(input: {
  headline: string;
  description: string;
  path: string;
  company: string;
  published: Date;
  updated?: Date | undefined;
  image?: string | undefined;
}): Json {
  const schema: Json = {
    '@type': 'Article',
    '@id': `${absolute(input.path)}#article`,
    headline: input.headline,
    description: input.description,
    url: absolute(input.path),
    mainEntityOfPage: absolute(input.path),
    datePublished: input.published.toISOString(),
    dateModified: (input.updated ?? input.published).toISOString(),
    author: { '@id': ORG_ID },
    publisher: { '@id': ORG_ID },
    inLanguage: SITE.lang,
    about: { '@type': 'Organization', name: input.company },
  };
  if (input.image) schema.image = absolute(input.image);
  return schema;
}

/** Wraps whatever a page emits into the single @graph it ships. */
export function graph(nodes: Json[]): string {
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': nodes });
}
