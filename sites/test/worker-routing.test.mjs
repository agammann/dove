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

function assets(response = new Response("asset")) {
  const requests = [];
  return {
    requests,
    env: { ASSETS: { async fetch(request) { requests.push(request); return response; } } },
  };
}

test("Worker preserves the asset service's URL, status, headers and body", async () => {
  for (const [path, status, headers, body] of [
    ["/workspace", 307, { Location: "/workspace/" }, null],
    ["/workspace/", 200, { "Cache-Control": "public, max-age=0, must-revalidate" }, "page"],
    ["/missing", 404, { "X-Asset-Response": "missing" }, "missing"],
  ]) {
    for (const method of ["GET", "HEAD"]) {
      const supplied = new Response(method === "HEAD" ? null : body, { status, headers });
      const { env, requests } = assets(supplied);
      const request = new Request(origin + path + "?probe=1", { method });
      const response = await worker.fetch(request, env);
      assert.equal(response, supplied);
      assert.deepEqual(requests, [request]);
    }
  }
  const { env, requests } = assets();
  assert.equal((await worker.fetch(new Request(origin + "/workspace/", { method: "POST" }), env)).status, 405);
  assert.equal(requests.length, 0);
});

test("Worker normalizes API slashes without rewriting asset paths", async () => {
  const { env, requests } = assets();
  const response = await worker.fetch(new Request(origin + "//api//access///?probe=1", { method: "POST" }), env);
  assert.equal(response.status, 308);
  assert.equal(response.headers.get("Location"), "/api/access?probe=1");
  assert.equal(requests.length, 0);
  assert.equal((await worker.fetch(new Request(origin + "/%invalid"), env)).status, 400);
  const request = new Request(origin + "//workspace///?probe=1");
  await worker.fetch(request, env);
  assert.equal(requests[0], request);
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
