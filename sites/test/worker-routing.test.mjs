import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";

const bundled = await build({
  entryPoints: ["worker/index.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  write: false,
  target: "es2022",
});
const { default: worker } = await import("data:text/javascript;base64," + Buffer.from(bundled.outputFiles[0].text).toString("base64"));
const origin = "https://dove.example";

function assets() {
  const requests = [];
  return {
    requests,
    env: {
      ASSETS: {
        async fetch(request) {
          requests.push({ pathname: new URL(request.url).pathname, method: request.method });
          const known = ["/index.html", "/workspace/index.html", "/favicon.svg"].includes(new URL(request.url).pathname);
          return new Response(request.method === "HEAD" ? null : known ? "asset" : "missing", { status: known ? 200 : 404 });
        },
      },
    },
  };
}

test("Worker maps both pages explicitly and retains asset 404s", async () => {
  const { env, requests } = assets();
  for (const [page, pathname] of [["/", "/index.html"], ["/workspace", "/workspace/index.html"]]) {
    for (const method of ["GET", "HEAD"]) {
      const response = await worker.fetch(new Request(origin + page, { method }), env);
      assert.equal(response.status, 200);
      assert.equal(response.headers.get("Cache-Control"), "no-cache");
      assert.equal(await response.text(), method === "HEAD" ? "" : "asset");
      assert.deepEqual(requests.at(-1), { pathname, method });
    }
  }
  assert.equal((await worker.fetch(new Request(origin + "/missing"), env)).status, 404);
  assert.equal((await worker.fetch(new Request(origin + "/workspace", { method: "POST" }), env)).status, 405);
});

test("Worker normalizes slashes without a protocol-relative redirect", async () => {
  const { env, requests } = assets();
  const response = await worker.fetch(new Request(origin + "//workspace///?probe=1", { method: "POST" }), env);
  assert.equal(response.status, 308);
  assert.equal(response.headers.get("Location"), "/workspace?probe=1");
  assert.equal(requests.length, 0);
  assert.equal((await worker.fetch(new Request(origin + "/%invalid"), env)).status, 400);
});

test("Worker keeps retired APIs and visitor validation ahead of asset serving", async () => {
  const { env, requests } = assets();
  for (const path of ["/api/access", "/api/dove/work"]) {
    for (const method of ["GET", "HEAD", "POST", "PUT", "DELETE"]) {
      const response = await worker.fetch(new Request(origin + path, { method }), env);
      assert.equal(response.status, 410);
      assert.equal(response.headers.get("Cache-Control"), "no-store");
      if (method === "HEAD") assert.equal(await response.text(), "");
      else assert.match((await response.json()).error, /stores work in your browser/);
    }
    const options = await worker.fetch(new Request(origin + path, { method: "OPTIONS" }), env);
    assert.equal(options.status, 204);
    assert.equal(options.headers.get("Allow"), "DELETE, GET, HEAD, OPTIONS, POST, PUT");
    assert.equal((await worker.fetch(new Request(origin + path, { method: "PATCH" }), env)).status, 405);
  }
  const visitor = origin + "/api/analyze/visitor";
  assert.equal((await worker.fetch(new Request(visitor), env)).status, 405);
  const options = await worker.fetch(new Request(visitor, { method: "OPTIONS" }), env);
  assert.equal(options.status, 204);
  assert.equal(options.headers.get("Allow"), "OPTIONS, POST");
  const missingKey = await worker.fetch(new Request(visitor, { method: "POST", headers: { "Content-Type": "application/json", Origin: origin }, body: "{}" }), env);
  assert.equal(missingKey.status, 401);
  assert.equal(missingKey.headers.get("Cache-Control"), "no-store");
  assert.equal((await worker.fetch(new Request(origin + "/api/unknown"), env)).status, 404);
  assert.equal(requests.length, 0);
});
