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
        let expressionContent = node.value;
        for (const key in variables) {
          expressionContent = expressionContent.replace(`{{${key}}}`, variables[key as keyof typeof variables]);
        }

        node.value = expressionContent;
      }
    });
  };
}
