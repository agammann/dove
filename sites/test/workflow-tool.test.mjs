import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";

const bundled = await build({
  entryPoints: ["lib/workflow-tool.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  write: false,
  target: "es2022",
});
const { parseWorkflowStep } = await import("data:text/javascript;base64," + Buffer.from(bundled.outputFiles[0].text).toString("base64"));
const invalid = { name: "Error", message: "Choose step 1, 2 or 3." };

test("workflow tool preserves each supported step", () => {
  for (const step of [1, 2, 3]) assert.equal(parseWorkflowStep({ step }), step);
});

test("workflow tool enforces its object and additionalProperties contract", () => {
  const arrayWithStep = Object.assign([], { step: 2 });
  for (const input of [null, undefined, 2, "2", [], arrayWithStep, {}, Object.create({ step: 2 }), { step: 2, unexpected: true }, { step: 2, [Symbol("extra")]: true }]) {
    assert.throws(() => parseWorkflowStep(input), invalid);
  }
});

test("workflow tool rejects noninteger and out-of-range steps", () => {
  for (const step of [undefined, null, "2", true, NaN, Infinity, 0, 4, 1.5]) {
    assert.throws(() => parseWorkflowStep({ step }), invalid);
  }
});
