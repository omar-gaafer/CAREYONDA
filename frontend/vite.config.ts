import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "production-fixture-boundary",
      generateBundle(_options, bundle) {
        const modules = new Set<string>();
        for (const item of Object.values(bundle)) {
          if (item.type !== "chunk") continue;
          for (const id of Object.keys(item.modules)) {
            const path = id.replaceAll("\\", "/");
            if (
              path.includes("/src/testing/") ||
              path.includes("/fixtures/") ||
              /\.(test|spec)\.[tj]sx?/.test(path)
            )
              this.error(
                "Production bundle attempted to include test-only code or fixtures",
              );
            const src = path.indexOf("/src/");
            if (src >= 0 && !path.includes("/node_modules/"))
              modules.add(path.slice(src + 1));
          }
        }
        this.emitFile({
          type: "asset",
          fileName: "production-modules.json",
          source: JSON.stringify([...modules].sort(), null, 2),
        });
      },
    },
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
          validation: ["zod"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    css: false,
  },
});
