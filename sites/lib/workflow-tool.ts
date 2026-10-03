export function parseWorkflowStep(input: unknown): number {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("Choose step 1, 2 or 3.");
  }
  const keys = Reflect.ownKeys(input);
  const step = (input as { step?: unknown }).step;
  if (keys.length !== 1 || keys[0] !== "step" || typeof step !== "number" || !Number.isInteger(step) || step < 1 || step > 3) {
    throw new Error("Choose step 1, 2 or 3.");
  }
  return step;
}
