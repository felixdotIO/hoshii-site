/**
 * Navigation, in one place so the header, the mobile menu and the footer
 * cannot drift apart. They did on the static build, which is why the old
 * generator carried a `check-chrome.py` to catch it.
 *
 * Every label here is also the h1 of the page it points at, so a visitor
 * always knows which page they landed on. The one exception is Product, which
 * is an anchor to the capabilities band on the homepage rather than a page of
 * its own — that is what it has always pointed at.
 */

export type NavLink = {
  href: string;
  label: string;
  /** Set where the link text alone would not describe the destination. */
  title?: string;
};

/** The primary bar. Deliberately three items: this is a sales site. */
export const PRIMARY_NAV: NavLink[] = [
  // Product is the capabilities band on the homepage, not the order-processing
  // page. The two are different things and the nav has always meant the first.
  { href: '/#product', label: 'Product' },
  { href: '/customers/', label: 'Customer stories' },
  { href: '/pricing/', label: 'Pricing' },
];

export const PRIMARY_CTA = { href: '/demo/', label: 'Book a demo' };

/** On the booking page itself the CTA would link to the page it is on. */
export const PRIMARY_CTA_ALT = { href: '/demo/', label: 'Let’s chat' };

export const FOOTER_NAV: { heading: string; links: NavLink[] }[] = [
  {
    heading: 'Product',
    links: [
      { href: '/#product', label: 'Product' },
      { href: '/pricing/', label: 'Pricing' },
      { href: '/customers/', label: 'Customer stories' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { href: '/resources/', label: 'Resources' },
      { href: '/faq/', label: 'Questions' },
      { href: '/careers/', label: 'Careers' },
      { href: '/partners/', label: 'Become a partner' },
      { href: '/about/', label: 'About' },
      { href: '/demo/', label: 'Book a demo' },
    ],
  },
  {
    heading: 'Legal',
    links: [
      { href: '/policies/imprint/', label: 'Imprint' },
      { href: '/policies/privacy-policy/', label: 'Privacy' },
      { href: '/policies/cookies-policy/', label: 'Cookies' },
    ],
  },
];
