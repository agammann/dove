export type ModelState = { phase: string; text: string; progress: number; model: string };
export const MODELS: { id: string; label: string }[];
export function modelState(): ModelState;
export function subscribeModel(listener: (state: ModelState) => void): () => void;
export function selectModel(id: string): void;
export function stopDownload(): void;
export function loadModel(options?: { signal?: AbortSignal }): Promise<unknown>;
export function generate(messages: { role: string; content: string }[], options?: { schema?: unknown; maxTokens?: number; signal?: AbortSignal }): Promise<{ text: string; value: any; model: string; usage?: { prompt_tokens?: number; completion_tokens?: number } }>;
