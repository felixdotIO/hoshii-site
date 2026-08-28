/**
 * Open roles, as listed on join.com.
 *
 * The application flow lives there, so each entry links out. Kept as data
 * because roles change often and a page edit should not be needed to add one —
 * and because a JobPosting node would have to be built from exactly these
 * fields if one is ever added. It is not added today: a valid JobPosting wants
 * a salary, a description and a validThrough date, and inventing any of those
 * to earn a rich result would be a lie in the markup.
 */
export type Job = {
  title: string;
  location: string;
  url: string;
};

export const JOBS: Job[] = [
  {
    title: 'Forward Deployed Software Engineer',
    location: 'Zürich',
    url: 'https://join.com/companies/hoshii/16577727-forward-deployed-software-engineer?pid=d73d1a20e99ab4ced633',
  },
  {
    title: 'Account Executive',
    location: 'Zürich',
    url: 'https://join.com/companies/hoshii/16599890-account-executive?pid=d73d1a20e99ab4ced633',
  },
];
