import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import hostingConfig from "./.openai/hosting.json" with { type: "json" };
import { sites } from "./build/sites-vite-plugin.ts";
import { prerenderPages } from "./build/prerender-pages.mjs";

const root = fileURLToPath(new URL(".", import.meta.url));
const { d1, r2 } = hostingConfig;
const isCodexSeatbeltSandbox = process.env.CODEX_SANDBOX === "seatbelt";

export default defineConfig(async () => {
  process.env.CLOUDFLARE_CF_FETCH_ENABLED ??= "false";
  process.env.WRANGLER_SEND_METRICS ??= "false";
  process.env.WRANGLER_WRITE_LOGS ??= "false";
  process.env.WRANGLER_LOG_PATH ??= ".wrangler/logs";
  process.env.WRANGLER_REGISTRY_PATH ??= ".wrangler/dev-registry";
  process.env.MINIFLARE_REGISTRY_PATH ??= ".wrangler/registry";
  const { cloudflare } = await import("@cloudflare/vite-plugin");

  return {
    resolve: { alias: { "@": root } },
    server: {
      port: 5173,
      watch: {
        ignored: ["**/.sites-runtime/**", "**/.wrangler/**"],
        ...(isCodexSeatbeltSandbox ? { useFsEvents: false, usePolling: true } : {}),
      },
    },
    environments: {
      client: {
        build: {
          outDir: "dist/client",
          rolldownOptions: { input: { home: path.join(root, "index.html"), workspace: path.join(root, "workspace/index.html") } },
        },
      },
      server: { build: { outDir: "dist/server", rolldownOptions: { output: { entryFileNames: "index.js" } } } },
    },
    plugins: [
      prerenderPages(),
      react(),
      sites(),
      cloudflare({
        viteEnvironment: { name: "server" },
        inspectorPort: false,
        remoteBindings: false,
        config: {
          name: "site-creator-vinext-starter",
          main: "./worker/index.ts",
          compatibility_date: "2026-10-01",
          compatibility_flags: ["nodejs_compat"],
          assets: { binding: "ASSETS", run_worker_first: true, html_handling: "none", not_found_handling: "none" },
          d1_databases: d1 ? [{ binding: d1, database_name: "site-creator-d1", database_id: "00000000-0000-4000-8000-000000000000" }] : [],
          r2_buckets: r2 ? [{ binding: r2, bucket_name: "site-creator-r2" }] : [],
        },
      }),
    ],
  };
});
