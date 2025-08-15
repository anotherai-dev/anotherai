import fs from "fs";
import type { Root } from "mdast";
import path from "path";
import { visit } from "unist-util-visit";

interface Config {
  environments?: {
    [key: string]: {
      API_URL?: string;
      WEB_APP_URL?: string;
    };
  };
  default?: {
    API_URL?: string;
    WEB_APP_URL?: string;
  };
}

// Load configuration from config.json
const configPath = path.join(process.cwd(), "config.json");
let config: Config = {};

try {
  const configFile = fs.readFileSync(configPath, "utf8");
  config = JSON.parse(configFile);
} catch {
  console.warn("Could not load config.json, using defaults");
}

// Determine environment (default to production for builds)
const environment = process.env.NODE_ENV === "development" ? "local" : "production";

// Get environment variables or fallback to config
const getTemplateVariables = () => {
  const envConfig = config.environments?.[environment] || config.default || {};

  return {
    API_URL: process.env.NEXT_PUBLIC_API_URL || envConfig.API_URL || "https://api.anotherai.dev",
    WEB_APP_URL: process.env.NEXT_PUBLIC_WEB_APP_URL || envConfig.WEB_APP_URL || "https://anotherai.dev",
  };
};

// Plugin to replace template variables in MDX content
export function remarkTemplateReplacement() {
  const variables = getTemplateVariables();
  return (tree: Root) => {
    visit(tree, (node) => {
      if ("value" in node && typeof node.value === "string") {
        const expressionContent = node.value;

        // Check if this is a template variable (with single braces like {API_URL})
        Object.entries(variables).forEach(([key, value]) => {
          if (expressionContent.trim() === `{${key}}`) {
            console.log(`Replacing MDX expression {${key}} with text node containing ${value}`);
            // Convert the mdxTextExpression to a regular text node
            (node as { type: string; value: string }).type = "text";
            node.value = value as string;
          }
        });
      }
    });
  };
}
