/**
 * The facts about Hoshii that more than one page needs, in one place.
 *
 * Everything here is used to render visible page content, structured data, or
 * both. Nothing in this file is invented: each value either appears on the
 * page that uses it or restates something the page states in prose.
 */

export const SITE = {
  /** No trailing slash: paths are joined onto it and they all start with one. */
  origin: 'https://www.hoshii.ai',
  name: 'Hoshii',
  legalName: 'Hoshii AG',
  locale: 'en_GB',
  lang: 'en',
  tagline: 'The AI-native inbox for B2B operations',
  description:
    "Hoshii is the AI-native inbox for B2B operations. It reads what lands in a team's shared mailboxes, connects to the systems the answers live in, and prepares the reply, the order or the follow-up for a human to approve.",
  foundingDate: '2024',
  city: 'Zürich',
  country: 'CH',
  /**
   * The default social card, and the Organization logo below it.
   *
   * Both live in `public/`, not `src/assets/`, and that is deliberate: a
   * card URL is quoted verbatim in an og:image tag and in JSON-LD, and is
   * fetched by a crawler that has never rendered the page. It therefore needs
   * a stable, unhashed path. Everything a browser lays out goes through
   * `astro:assets` instead, for the WebP and the intrinsic dimensions.
   *
   * The card is a real photograph at 1672x941, comfortably over the 1200x630
   * that the platforms want.
   */
  ogImage: '/assets/img/hero-slot.jpg',
  logo: '/assets/logo/wordmark-a.png',
  email: {
    sales: 'contact@hoshii.ai',
    support: 'support@hoshii.ai',
    partners: 'partners@hoshii.ai',
    jobs: 'jobs@hoshii.ai',
  },
  /** Stated on the FAQ and the about page, so the schema may state it too. */
  knowsAbout: [
    'B2B order processing',
    'ERP order entry',
    'shared inbox automation',
    'wholesale distribution operations',
  ],
} as const;

/**
 * The one author the articles have. Team Hoshii is how the posts are bylined
 * on the live site; no individual is credited, so none is invented here.
 */
export const AUTHORS = {
  'team-hoshii': {
    name: 'Team Hoshii',
    role: 'Hoshii',
    bio: 'Written by the team building Hoshii in Zürich, from what the order desks running it tell us.',
    url: '/about/',
  },
} as const;

export type AuthorId = keyof typeof AUTHORS;
