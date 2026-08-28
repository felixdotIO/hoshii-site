import { defineCollection, reference, z } from 'astro:content';
import { glob } from 'astro/loaders';

/**
 * The content model.
 *
 * Four collections, because there are four genuinely different kinds of
 * content here and they carry different metadata: editorial articles, customer
 * stories, legal documents, and the question-and-answer sets that drive both
 * the FAQ pages and their structured data.
 *
 * Every field is validated. A schema that only describes the fields is
 * documentation; one that rejects a missing description or a bad date is the
 * thing that stops a page shipping without a meta description at four in the
 * afternoon.
 *
 * The file layout — one `.mdoc` per article, one `.json` per author and per
 * question group — is the shape Keystatic reads and writes. This file and
 * `keystatic.config.ts` describe the same content from two directions: the
 * editor decides what an author can type, and this decides what will build.
 * A change to one needs the matching change to the other, and a mismatch
 * fails the build rather than shipping.
 */

/**
 * An optional string that an empty value also satisfies.
 *
 * Keystatic writes `''` for a text field left blank rather than omitting the
 * key, so without this every unfilled optional field would arrive as an empty
 * string and read as present.
 */
const emptyToUndefined = z
  .string()
  .optional()
  .transform((value) => (value === undefined || value.trim() === '' ? undefined : value));

/** Shared across every collection: what the <head> needs. */
const seo = {
  title: z.string().min(1).max(70),
  /**
   * Written for a search result, so it is capped. Google truncates around
   * 155-160 characters and an answer engine wants one clean sentence anyway.
   */
  description: z.string().min(50).max(170),
  /** Set only where this page is a duplicate of one that lives elsewhere. */
  canonical: z.string().url().optional(),
  draft: z.boolean().default(false),
};

const articles = defineCollection({
  loader: glob({ base: './src/content/articles', pattern: '**/*.mdoc' }),
  schema: ({ image }) =>
    z.object({
      ...seo,
      /**
       * The answer, in one or two sentences, before the argument for it. It is
       * rendered at the top of the piece and reused as the card blurb, so an
       * answer engine and a reader meet the same summary.
       */
      summary: z.string().min(40),
      publishedAt: z.coerce.date(),
      updatedAt: z.coerce.date().optional(),
      author: reference('authors'),
      category: z.enum(['Operations', 'Industry', 'AI & Automation', 'Product']),
      tags: z.array(z.string()).default([]),
      heroImage: image().optional(),
      /**
       * Required whenever heroImage is set, and allowed to be the empty
       * string. Empty means "decorative": the art on these cards is an
       * abstract gradient that carries no information, so it is announced to
       * nobody rather than described at a reader who cannot see it. Making
       * the field mandatory forces that to be a decision rather than an
       * oversight.
       */
      heroImageAlt: z.string().optional(),
      /** Roughly how long the piece takes to read, as published. */
      readingMinutes: z.number().int().positive().optional(),
      /**
       * Where a factual claim rests on something outside this page, the
       * something is named here and printed under the article.
       */
      sources: z
        .array(
          z.object({
            title: z.string(),
            publisher: z.string().optional(),
            url: z.string().url().optional(),
            /** When the source was consulted, so a reader can judge freshness. */
            retrieved: z.coerce.date().optional(),
          })
        )
        .default([]),
      /** Hand-picked. Falls back to same-category articles when empty. */
      relatedArticles: z.array(reference('articles')).default([]),
    })
    // An image with no alt decision at all is an image a screen reader
    // cannot use. An explicit empty string is a decision; a missing field
    // is not.
    .refine((data) => !data.heroImage || data.heroImageAlt !== undefined, {
      message: 'heroImage requires heroImageAlt (use "" for decorative art)',
      path: ['heroImageAlt'],
    }),
});

const customers = defineCollection({
  loader: glob({ base: './src/content/customers', pattern: '**/*.mdoc' }),
  schema: ({ image }) =>
    z.object({
      ...seo,
      /** The customer this story is about. Used in the Article `about`. */
      company: z.string(),
      /** The line that runs on the card and as the page's own claim. */
      headline: z.string(),
      excerpt: z.string(),
      industry: z.string(),
      /** The system Hoshii writes into. Stated on the page, so also on the card. */
      erp: z.string(),
      year: z.string().regex(/^\d{4}$/),
      publishedAt: z.coerce.date(),
      updatedAt: z.coerce.date().optional(),
      coverImage: image().optional(),
      coverImageAlt: z.string().optional(),
      /**
       * The video and the quote are flat fields rather than two nested
       * objects, and that is a deliberate simplification. An optional nested
       * object has to be encoded somehow when it is absent, and every
       * encoding is worse than not nesting: Keystatic writes a
       * `discriminant`/`value` wrapper, which leaks the editor's internals
       * into the content, and a plain optional object silently fails to load
       * in the editor instead. Flat optional fields need no encoding at all
       * and read better in the file.
       *
       * `emptyToUndefined` is what makes that work in both directions: the
       * editor writes an empty string for a field nobody filled in, and this
       * treats that as absent, so `videoId && ...` in the template is true
       * only when there is really a video.
       */
      videoId: emptyToUndefined,
      videoTitle: emptyToUndefined,
      quoteText: emptyToUndefined,
      quoteName: emptyToUndefined,
      quoteRole: emptyToUndefined,
      quotePhoto: image().optional(),
      /** Figures the prose already states. The rail restates them, nothing more. */
      figures: z.array(z.object({ value: z.string(), label: z.string() })).default([]),
      /** A sentence lifted out of the piece and set large. Never attributed. */
      lift: z.string().optional(),
      /** Ordering on the index. Lower runs first. */
      order: z.number().int().default(50),
    })
    .refine((data) => !data.coverImage || Boolean(data.coverImageAlt), {
      message: 'coverImage requires coverImageAlt',
      path: ['coverImageAlt'],
    }),
});

const policies = defineCollection({
  loader: glob({ base: './src/content/policies', pattern: '**/*.mdoc' }),
  schema: z.object({
    ...seo,
    /** The page's own name, which is also its h1 and its nav label. */
    name: z.string(),
    /** The descriptive line under the h1. A document gets one of these. */
    standfirst: z.string(),
    /**
     * Contract documents live at a stable URL because an order form links to
     * them, but they are not part of the site: no footer link, no sitemap
     * entry, and a robots directive keeping them out of the index.
     */
    index: z.boolean().default(true),
    updatedAt: z.coerce.date(),
    order: z.number().int().default(50),
  }),
});

/**
 * Questions and answers as data rather than prose, so one source drives the
 * rendered accordion and the FAQPage JSON-LD. They cannot disagree, which is
 * the only way FAQ structured data is worth having.
 */
const faqs = defineCollection({
  loader: glob({ base: './src/content/faqs', pattern: '**/*.json' }),
  schema: z.object({
    /** Which page renders this set. */
    page: z.enum(['faq', 'pricing', 'order-processing', 'home']),
    /** The H2 this group sits under on the page. */
    group: z.string(),
    order: z.number().int(),
    items: z
      .array(
        z.object({
          question: z.string().min(5),
          /** Markdown-free plain text: it is rendered and put in the schema. */
          answer: z.array(z.string().min(20)).min(1),
        })
      )
      .min(1),
  }),
});

const authors = defineCollection({
  loader: glob({ base: './src/content/authors', pattern: '**/*.json' }),
  schema: z.object({
    name: z.string(),
    role: z.string(),
    bio: z.string(),
    url: z.string(),
  }),
});

export const collections = { articles, customers, policies, faqs, authors };
