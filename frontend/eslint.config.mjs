import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        Chart: "readonly",
        flatpickr: "readonly",
        bootstrap: "readonly",
        escapeHtml: "readonly",
        showConfirmDialog: "readonly",
      },
    },
  },
  {
    ignores: [
      "static/js/bootstrap.bundle.min.js",
      "static/js/chart.umd.js",
      "static/js/flatpickr.min.js",
      "static/js/flatpickr-fr.js",
      "node_modules/",
    ],
  },
];
