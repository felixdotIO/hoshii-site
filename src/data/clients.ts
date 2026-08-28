import casadelvino from '~/assets/clients/n-casadelvino.png';
import staempfli from '~/assets/clients/n-staempfli.png';
import chiefs from '~/assets/clients/n-chiefs.png';
import stutzer from '~/assets/clients/n-stutzer.png';
import igp from '~/assets/clients/n-igp.png';
import schuetzengarten from '~/assets/clients/n-schuetzengarten.png';
import egger from '~/assets/clients/n-egger.png';
import safruits from '~/assets/clients/n-safruits.png';

/**
 * The client marks on the logo belt.
 *
 * `ink` is how the file arrives, not a style choice: `paper` is dark artwork on
 * white, `alpha` has real transparency, and `solid` is a knockout logo where
 * the lettering is white inside a filled shape. Each needs different handling
 * to render as one flat ink, which is what the per-treatment CSS does.
 */
export const CLIENTS = [
  { key: 'casadelvino', name: 'Casa del Vino', src: casadelvino, ink: 'paper' },
  { key: 'staempfli', name: 'Stämpfli', src: staempfli, ink: 'paper' },
  { key: 'chiefs', name: 'Chiefs', src: chiefs, ink: 'paper' },
  { key: 'stutzer', name: 'Stutzer', src: stutzer, ink: 'alpha' },
  { key: 'igp', name: 'IGP Powder Coatings', src: igp, ink: 'paper' },
  { key: 'schuetzengarten', name: 'Schützengarten', src: schuetzengarten, ink: 'solid' },
  { key: 'egger', name: 'Egger Gemüsebau', src: egger, ink: 'paper' },
  { key: 'safruits', name: 'Safruits', src: safruits, ink: 'paper' },
] as const;
