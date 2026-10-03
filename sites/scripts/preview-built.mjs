import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { spawn } from "node:child_process";
import "./sites-env.mjs";

// Test only the compiled Worker and browser output, with no application secrets.
const directory = resolve(".sites-runtime", "built-preview");
mkdirSync(directory, { recursive: true });
const config = JSON.parse(readFileSync("dist/server/wrangler.json", "utf8"));
config.main = resolve("dist/server/index.js");
config.assets.directory = resolve("dist/client");
writeFileSync(resolve(directory, "wrangler.json"), JSON.stringify(config));
writeFileSync(resolve(directory, ".dev.vars"), "");
const port = process.argv[2] || "5174";
if (!/^[0-9]{1,5}$/.test(port) || Number(port) < 1024 || Number(port) > 65535) throw new Error("Use a valid local preview port.");
const child = spawn(process.execPath, ["node_modules/wrangler/bin/wrangler.js", "dev", "--config", resolve(directory, "wrangler.json"), "--local", "--persist-to", resolve(".wrangler/state"), "--ip", "127.0.0.1", "--port", port, "--inspector-port", "0"], { cwd: resolve("."), stdio: "inherit" });
child.on("error", () => { process.exitCode = 1; });
child.on("exit", code => { process.exitCode = code ?? 1; });
