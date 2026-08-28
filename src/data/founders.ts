/**
 * The three founders, as they are introduced on the about page.
 *
 * No photographs exist for them, so the card falls back to initials — which is
 * what `doc__portrait--none` is for. Nothing here is inferred: the roles and
 * the lines are the ones they gave.
 */
export const FOUNDERS = [
  {
    name: 'Jiir Awdir',
    role: 'Co‑founder & CEO',
    quote: 'The inbox is where B2B commerce actually happens. That is where the work belongs.',
  },
  {
    name: 'Ayoub Chouak',
    role: 'Co‑founder & CTO',
    quote: 'Reliability first. An order desk cannot run on something that works most of the time.',
  },
  {
    name: 'Chihiro Okuyama',
    role: 'Co‑founder & CAIO',
    quote: 'Models are the easy part. Earning the right to act on somebody’s orders is the work.',
  },
] as const;
