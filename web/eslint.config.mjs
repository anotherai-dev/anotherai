import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      "no-restricted-imports": [
        "error",
        // Import should be next/navigation
        "next/router",
        // Clerk should not be imported unless explicitly needed
        "@clerk/nextjs",
        "@clerk/nextjs/server",
        // Stripe should not be imported unless explicitly needed
        "@stripe/react-stripe-js",
        "@stripe/stripe-js",
      ],
    },
  },
];

export default eslintConfig;
