import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

// The frontend's unit tests cover the pure decision seams in lib/ — which kind
// of file was picked, what the person is told when it cannot be read, and how
// many pages a PDF had. Browser plumbing (canvas, pdf.js, sessionStorage) is
// injected at those seams rather than emulated, so no jsdom is needed.
export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
