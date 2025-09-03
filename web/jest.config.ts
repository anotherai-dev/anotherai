import type { Config } from "jest";
import nextJest from "next/jest.js";

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: "./",
});

// Add any custom config to be passed to Jest
const customJestConfig: Config = {
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jsdom",
  moduleNameMapper: {
    // Handle module aliases (this will be automatically configured for Next.js)
    "^@/auth/(.*)$": "<rootDir>/src/auth/noauth/$1",
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  testMatch: ["**/__tests__/**/*.(js|jsx|ts|tsx)", "**/*.(test|spec).(js|jsx|ts|tsx)"],
  testPathIgnorePatterns: [
    "<rootDir>/.next/",
    "<rootDir>/node_modules/",
    "<rootDir>/src/auth/clerk/", // Clerk auth files have runtime issues in Jest environment
    "<rootDir>/src/auth/noauth/", // Auth files have Node.js/browser compatibility issues
  ],
  collectCoverageFrom: [
    "src/**/*.(js|jsx|ts|tsx)",
    "!src/**/*.d.ts",
    "!src/app/api/**/*", // Exclude API routes from coverage
    "!**/node_modules/**",
  ],
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov", "html"],
  moduleDirectories: ["node_modules", "<rootDir>/"],
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
const finalConfig = createJestConfig(customJestConfig);

export default finalConfig;
