import { defineMarkdocConfig } from '@astrojs/markdoc/config';

/**
 * Markdoc, which is the format Keystatic writes.
 *
 * Deliberately almost empty. The integration already slugs every heading with
 * github-slugger — the same slugger Astro's Markdown pipeline used — so the
 * anchor ids the table of contents links to are unchanged from before the
 * migration, and no already-shared deep link moves.
 *
 * Nothing is added here that authors cannot see in the editor. A Markdoc tag
 * that renders a component would be invisible in Keystatic's preview, so if
 * one is ever needed it belongs in `components` on the field, not here.
 */
export default defineMarkdocConfig({});
