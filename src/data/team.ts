import daniel from '~/assets/team/daniel-nydegger.jpg';
import joel from '~/assets/team/joel-heller.jpg';
import philipp from '~/assets/team/philipp-kuprecht.jpg';
import alexander from '~/assets/team/alexander-sucur.jpg';
import antonio from '~/assets/team/antonio-stano.jpg';
import francesco from '~/assets/team/francesco-intoci.jpg';

/**
 * The people with a photograph on the site.
 *
 * Names, roles and quotes as they were given to us. Nothing is inferred here:
 * no titles are invented, and nobody appears who has not agreed to.
 *
 * `gtm` are the three who take demo calls, which is why the booking page shows
 * that subset — a visitor about to book sees who they will be talking to.
 */
export type TeamMember = {
  name: string;
  role: string;
  photo: ImageMetadata;
  quote?: string;
  gtm?: boolean;
};

export const TEAM: TeamMember[] = [
  {
    name: 'Daniel Nydegger',
    role: 'Head of GTM',
    photo: daniel,
    quote: 'If you cannot say what it does in one sentence, you do not understand it yet.',
    gtm: true,
  },
  {
    name: 'Joël Heller',
    role: 'GTM Executive',
    photo: joel,
    quote: 'My job is making sure customers feel the difference on day one.',
    gtm: true,
  },
  {
    name: 'Philipp Kuprecht',
    role: 'GTM Executive',
    photo: philipp,
    quote: 'Every account is somebody’s working day, not a line in a pipeline.',
    gtm: true,
  },
  {
    name: 'Francesco Intoci',
    role: 'Founding Software Engineer',
    photo: francesco,
    quote: 'We build the unglamorous infrastructure so the magic looks effortless.',
  },
  {
    name: 'Antonio Stano',
    role: 'Founding Software Engineer',
    photo: antonio,
  },
  {
    name: 'Alexander Sucur',
    role: 'Founder’s Associate',
    photo: alexander,
    quote: 'Whatever moves us to the next milestone, that is my to‑do list.',
  },
];

export const GTM_TEAM = TEAM.filter((member) => member.gtm);
