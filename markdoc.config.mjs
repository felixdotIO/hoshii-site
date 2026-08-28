import { defineMarkdocConfig, nodes } from '@astrojs/markdoc/config';

/**
 * Markdoc, which is the format Keystatic writes.
 *
 * Deliberately almost empty. The integration already slugs every heading with
 * github-slugger — the same slugger Astro's Markdown pipeline used — so the
 * anchor ids the table of contents links to are unchanged from before the
 * migration, and no already-shared deep link moves.
 *
 * The one override: Markdoc wraps a document in an `<article>` of its own.
 * That put an `<article>` inside the `<article>` each template already
 * provides — a redundant landmark — and, less visibly, it broke every
 * `.case > p` and `.art__body > p` rule in the stylesheet, because the
 * paragraphs were no longer direct children. The prose silently lost its
 * measure and ran at about 95 characters a line. Rendering the document as
 * nothing puts the paragraphs back where the CSS expects them.
 */
export default defineMarkdocConfig({
  nodes: {
    document: { ...nodes.document, render: null },
  },
});
