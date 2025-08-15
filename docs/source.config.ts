import { rehypeCode } from "fumadocs-core/mdx-plugins";
import { defineConfig, defineDocs, frontmatterSchema, metaSchema } from "fumadocs-mdx/config";
import { remarkTemplateReplacement } from "./lib/template-replacement";

// You can customise Zod schemas for frontmatter and `meta.json` here
// see https://fumadocs.vercel.app/docs/mdx/collections#define-docs
export const docs = defineDocs({
  docs: {
    schema: frontmatterSchema,
  },
  meta: {
    schema: metaSchema,
  },
});

export default defineConfig({
  mdxOptions: {
    // MDX options
    rehypePlugins: [rehypeCode],
    // run remarkTemplateReplacement first
    remarkPlugins: (v) => [remarkTemplateReplacement, ...v],
  },
});
