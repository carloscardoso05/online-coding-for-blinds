import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["**/*.min.js", "node_modules/"] },
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      "no-undef": "off",        // cross-file globals are normal in this vanilla JS project
      "no-unused-vars": "warn",
      "no-console": "off",
    },
  },
];
