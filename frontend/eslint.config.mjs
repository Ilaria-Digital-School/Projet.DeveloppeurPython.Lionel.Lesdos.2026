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
        getCSRFToken: "readonly",
        showConfirmDialog: "readonly",
      },
    },
  },
  {
    // Scripts classiques chargés par <script> (sauf le menu, en module ES)
    files: ["static/js/**/*.js"],
    ignores: ["static/js/menu/**"],
    languageOptions: { sourceType: "script" },
  },
  {
    // utils.js définit les fonctions globales partagées
    files: ["static/js/utils.js"],
    languageOptions: {
      globals: { escapeHtml: "off", getCSRFToken: "off", showConfirmDialog: "off" },
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
