import { config, collection, fields } from '@keystatic/core';

/**
 * The editor, at /keystatic.
 *
 * This file describes the same content that `src/content.config.ts` validates,
 * one collection at a time. The two have to agree: Keystatic decides what an
 * author can type, and the Zod schema decides what will build. Where they
 * disagree the build fails, which is the right way round — a bad field is
 * caught in CI rather than shipped — but it still means any change here needs
 * the matching change there.
 *
 * `local` mode is used in development, so `npm run dev` opens a working editor
 * with no GitHub app and no login. In production it runs in `github` mode:
 * Save commits to the repository, the push triggers a Vercel build, and the
 * article is live a minute later. There is no database and no content API.
 */

const seoFields = {
  title: fields.slug({
    name: {
      label: 'Title',
      description: 'The headline, and the basis of the URL. Aim for under 70 characters.',
      validation: { length: { min: 1, max: 70 } },
    },
    slug: {
      label: 'URL slug',
      description: 'Lowercase and hyphenated. Changing this on a published piece breaks its links.',
    },
  }),
  description: fields.text({
    label: 'Meta description',
    description:
      'One sentence, written for a search result. Must be unique across the site. 50–170 characters.',
    multiline: true,
    validation: { length: { min: 50, max: 170 } },
  }),
  draft: fields.checkbox({
    label: 'Draft',
    description: 'Drafts are not built at all, so the URL cannot be reached or indexed.',
    defaultValue: false,
  }),
};

export default config({
  // `import.meta.env.DEV` rather than `process.env`: this file is bundled into
  // the admin UI and runs in a browser, where there is no `process`.
  storage:
    import.meta.env.DEV
      ? { kind: 'local' }
      : {
          kind: 'github',
          // Set to the repository this deploys from before the first
          // production save. Keystatic writes commits here.
          repo: { owner: 'felixdotIO', name: 'hoshii-site' },
        },

  ui: {
    brand: { name: 'Hoshii' },
    navigation: {
      Editorial: ['articles'],
      Customers: ['customers'],
      Reference: ['faqs', 'authors'],
      Legal: ['policies'],
    },
  },

  collections: {
    /** Blog posts. Published at /resources/<slug>/. */
    articles: collection({
      label: 'Articles',
      path: 'src/content/articles/*',
      slugField: 'title',
      format: { contentField: 'body' },
      entryLayout: 'content',
      columns: ['title', 'category', 'publishedAt'],
      schema: {
        ...seoFields,
        summary: fields.text({
          label: 'Summary',
          description:
            'The answer, in one or two sentences, before the argument for it. Printed at the top of the piece and reused as the card blurb.',
          multiline: true,
          validation: { length: { min: 40 } },
        }),
        publishedAt: fields.date({
          label: 'Published',
          validation: { isRequired: true },
        }),
        updatedAt: fields.date({
          label: 'Updated',
          description:
            'Set only on a real revision. It drives dateModified, which is how freshness is judged.',
        }),
        author: fields.relationship({
          label: 'Author',
          collection: 'authors',
          validation: { isRequired: true },
        }),
        category: fields.select({
          label: 'Category',
          options: [
            { label: 'Operations', value: 'Operations' },
            { label: 'Industry', value: 'Industry' },
            { label: 'AI & Automation', value: 'AI & Automation' },
            { label: 'Product', value: 'Product' },
          ],
          defaultValue: 'Operations',
        }),
        tags: fields.array(fields.text({ label: 'Tag' }), {
          label: 'Tags',
          itemLabel: (props) => props.value,
        }),
        heroImage: fields.image({
          label: 'Hero image',
          directory: 'src/assets/posts',
          publicPath: '../../assets/posts/',
        }),
        heroImageAlt: fields.text({
          label: 'Hero image alt text',
          description:
            'Describe what the picture shows. Leave empty only when the art is decorative and carries no information.',
        }),
        readingMinutes: fields.integer({
          label: 'Reading time (minutes)',
        }),
        sources: fields.array(
          fields.object({
            title: fields.text({ label: 'Title', validation: { isRequired: true } }),
            publisher: fields.text({ label: 'Publisher' }),
            url: fields.url({ label: 'URL' }),
            retrieved: fields.date({ label: 'Retrieved on' }),
          }),
          {
            label: 'Sources',
            description:
              'Where a factual claim rests on something outside this page, name it here. Printed under the article.',
            itemLabel: (props) => props.fields.title.value || 'Source',
          }
        ),
        relatedArticles: fields.array(
          fields.relationship({ label: 'Article', collection: 'articles' }),
          {
            label: 'Related articles',
            description: 'Leave empty to fall back to the newest in the same category.',
            itemLabel: (props) => props.value ?? 'Article',
          }
        ),
        body: fields.markdoc({ label: 'Body' }),
      },
    }),

    /** Case studies. Published at /customers/<slug>/. */
    customers: collection({
      label: 'Customer stories',
      path: 'src/content/customers/*',
      slugField: 'title',
      format: { contentField: 'body' },
      entryLayout: 'content',
      columns: ['title', 'erp', 'publishedAt'],
      schema: {
        ...seoFields,
        company: fields.text({
          label: 'Company',
          description: 'The legal name. Used as the h1 and as the subject in the structured data.',
          validation: { isRequired: true },
        }),
        headline: fields.text({
          label: 'Headline',
          description: 'The claim. Runs under the company name and on the card.',
          multiline: true,
          validation: { isRequired: true },
        }),
        excerpt: fields.text({
          label: 'Card blurb',
          multiline: true,
          validation: { isRequired: true },
        }),
        industry: fields.text({ label: 'Industry', validation: { isRequired: true } }),
        erp: fields.text({
          label: 'ERP',
          description: 'The system Hoshii writes into. Printed on the card and in the meta row.',
          validation: { isRequired: true },
        }),
        year: fields.text({ label: 'Year', validation: { length: { min: 4, max: 4 } } }),
        publishedAt: fields.date({ label: 'Published', validation: { isRequired: true } }),
        updatedAt: fields.date({ label: 'Updated' }),
        coverImage: fields.image({
          label: 'Cover image',
          directory: 'src/assets/customers',
          publicPath: '../../assets/customers/',
        }),
        coverImageAlt: fields.text({ label: 'Cover image alt text' }),
        // Flat rather than two nested optional objects, for the reason set
        // out in src/content.config.ts: any encoding of "this object is
        // absent" is worse than not nesting. Leave them blank and neither
        // the video nor the quote renders.
        videoId: fields.text({
          label: 'Wistia video id',
          description: 'Leave blank if this customer is not on camera.',
        }),
        videoTitle: fields.text({ label: 'Video title' }),
        quoteText: fields.text({
          label: 'Quote',
          description: 'Said on the record by a named person at the company. Leave blank if there is none.',
          multiline: true,
        }),
        quoteName: fields.text({ label: 'Quoted person' }),
        quoteRole: fields.text({ label: 'Their role' }),
        quotePhoto: fields.image({
          label: 'Their photo',
          directory: 'src/assets/img',
          publicPath: '../../assets/img/',
        }),
        figures: fields.array(
          fields.object({
            value: fields.text({ label: 'Figure' }),
            label: fields.text({ label: 'Label' }),
          }),
          {
            label: 'Figures',
            description: 'Only numbers the piece itself already states. Do not add new claims here.',
            itemLabel: (props) => `${props.fields.value.value} ${props.fields.label.value}`,
          }
        ),
        lift: fields.text({
          label: 'Pulled sentence',
          description: 'One sentence lifted out of the piece and set large. Never attributed.',
          multiline: true,
        }),
        order: fields.integer({ label: 'Order on the index', defaultValue: 50 }),
        body: fields.markdoc({ label: 'Body' }),
      },
    }),

    /** Legal documents. */
    policies: collection({
      label: 'Policies',
      path: 'src/content/policies/*',
      slugField: 'name',
      format: { contentField: 'body' },
      entryLayout: 'content',
      schema: {
        name: fields.slug({ name: { label: 'Name' } }),
        title: fields.text({ label: 'Title', validation: { length: { min: 1, max: 70 } } }),
        description: fields.text({
          label: 'Meta description',
          multiline: true,
          validation: { length: { min: 50, max: 170 } },
        }),
        standfirst: fields.text({ label: 'Standfirst', multiline: true }),
        index: fields.checkbox({
          label: 'Indexable',
          description:
            'Uncheck for contract documents. They keep a stable URL but leave the sitemap and carry a noindex.',
          defaultValue: true,
        }),
        updatedAt: fields.date({ label: 'Last updated', validation: { isRequired: true } }),
        order: fields.integer({ label: 'Order', defaultValue: 50 }),
        draft: fields.checkbox({ label: 'Draft', defaultValue: false }),
        body: fields.markdoc({ label: 'Body' }),
      },
    }),


    /**
     * The question sets. One file per group, because that is what they are:
     * each file drives both the rendered accordion and the FAQPage JSON-LD on
     * whichever page it names, and the two are generated from the same array
     * so they cannot disagree.
     *
     * A collection rather than a singleton, matching the files on disk. As a
     * singleton it read as empty and a save would have written a new file and
     * orphaned all seven.
     */
    faqs: collection({
      label: 'Questions & answers',
      path: 'src/content/faqs/*',
      slugField: 'group',
      format: { data: 'json' },
      columns: ['group', 'page', 'order'],
      schema: {
        group: fields.slug({
          name: {
            label: 'Group heading',
            description: 'The h2 this set sits under on the page.',
          },
        }),
        page: fields.select({
          label: 'Shown on',
          description: 'Which page renders this set.',
          options: [
            { label: 'Questions page', value: 'faq' },
            { label: 'Pricing', value: 'pricing' },
            { label: 'Order processing', value: 'order-processing' },
            { label: 'Homepage', value: 'home' },
          ],
          defaultValue: 'faq',
        }),
        order: fields.integer({ label: 'Order on the page', defaultValue: 1 }),
        items: fields.array(
          fields.object({
            question: fields.text({ label: 'Question' }),
            answer: fields.array(fields.text({ label: 'Paragraph', multiline: true }), {
              label: 'Answer',
              description:
                'Plain text, no formatting: it is rendered on the page and copied into the structured data.',
              itemLabel: (props) => props.value.slice(0, 60),
            }),
          }),
          {
            label: 'Questions',
            itemLabel: (props) => props.fields.question.value,
          }
        ),
      },
    }),

    authors: collection({
      label: 'Authors',
      path: 'src/content/authors/*',
      slugField: 'name',
      schema: {
        name: fields.slug({ name: { label: 'Name' } }),
        role: fields.text({ label: 'Role' }),
        bio: fields.text({ label: 'Bio', multiline: true }),
        url: fields.text({ label: 'Profile URL', defaultValue: '/about/' }),
      },
    }),
  },

});
