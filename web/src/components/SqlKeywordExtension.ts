import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

const SQL_KEYWORDS = [
  "SELECT",
  "FROM",
  "WHERE",
  "AND",
  "OR",
  "NOT",
  "IN",
  "LIKE",
  "IS",
  "NULL",
  "ORDER",
  "BY",
  "GROUP",
  "HAVING",
  "LIMIT",
  "OFFSET",
  "AS",
  "JOIN",
  "LEFT",
  "RIGHT",
  "INNER",
  "OUTER",
  "ON",
  "UNION",
  "DISTINCT",
  "COUNT",
  "SUM",
  "AVG",
  "MIN",
  "MAX",
  "INSERT",
  "UPDATE",
  "DELETE",
  "CREATE",
  "DROP",
  "ALTER",
  "TABLE",
];

export const SqlKeywordExtension = Extension.create({
  name: "sqlKeyword",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("sqlKeyword"),
        props: {
          decorations(state) {
            const decorations: Decoration[] = [];
            const keywordRegex = new RegExp(
              `\\b(${SQL_KEYWORDS.join("|")})\\b`,
              "gi"
            );

            state.doc.descendants((node, pos) => {
              if (node.isText && node.text) {
                let match;
                keywordRegex.lastIndex = 0;

                while ((match = keywordRegex.exec(node.text)) !== null) {
                  const from = pos + match.index;
                  const to = from + match[0].length;

                  decorations.push(
                    Decoration.inline(from, to, {
                      class: "sql-keyword font-bold",
                    })
                  );
                }
              }
              return true;
            });

            return DecorationSet.create(state.doc, decorations);
          },
        },
      }),
    ];
  },
});
