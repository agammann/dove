// Inference runs in a dedicated worker. Remote requests download executable
// model assets; prompts are sent only to this origin's local worker.
export const MODELS = [
  { id: 'Qwen3-1.7B-q4f16_1-MLC', label: 'Standard · Qwen 3 1.7B' },
  { id: 'Qwen3-4B-q4f16_1-MLC', label: 'Larger · Qwen 3 4B' },
];
let selected = MODELS[1].id;
let engine, worker, loading, loadController, active = false;
let state = { phase: 'idle', text: 'Download a model once. Generation runs on your device.', progress: 0, model: selected };
const listeners = new Set();
function publish(patch) {
  state = { ...state, ...patch };
  for (const listener of listeners) listener(state);
}
export function modelState() { return state; }
export function subscribeModel(listener) { listeners.add(listener); listener(state); return () => listeners.delete(listener); }
export function selectModel(id) {
  if (!MODELS.some(m => m.id === id)) throw Error('Choose a supported browser model.');
  if (active || loading) throw Error('Wait for the current task or stop it before changing models.');
  worker?.terminate(); engine = worker = undefined; selected = id;
  publish({ phase: 'idle', model: id, progress: 0, text: 'Download a model once. Generation runs on your device.' });
}
export function unloadModel(){if(active||loading)throw Error('Stop the text task before loading the image model.');worker?.terminate();worker=engine=undefined;publish({phase:'idle',progress:0,text:'Text model unloaded to free graphics memory. Reload it to write more text.'});}
export function stopDownload() { loadController?.abort(); }
function aborted(signal) {
  signal?.throwIfAborted();
}
function withAbort(promise, signal, cancel) {
  if (!signal) return promise;
  aborted(signal);
  return new Promise((resolve, reject) => {
    const stop = () => { cancel(); reject(signal.reason || new DOMException('Stopped.', 'AbortError')); };
    signal.addEventListener('abort', stop, { once: true });
    promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', stop));
  });
}
export async function loadModel({ signal } = {}) {
  aborted(signal);
  if (engine) return engine;
  if (!loading) {
    loadController = new AbortController();
    const loadingSignal = loadController.signal;
    publish({ phase: 'loading', text: 'Checking browser support…', progress: 0 });
    loading = (async () => {
      if (!globalThis.isSecureContext || !navigator.gpu) throw Error('This browser cannot run the model. Try an updated browser with WebGPU on a supported device. No paid service will be used.');
      const adapter = await navigator.gpu.requestAdapter();
      aborted(loadingSignal);
      if (!adapter) throw Error('A compatible graphics adapter is unavailable. Check browser hardware acceleration or try another device.');
      let model = selected;
      if (!adapter.features.has('shader-f16')) model = model.replace('q4f16', 'q4f32');
      const webllm = await withAbort(import(/* @vite-ignore */ 'https://esm.run/@mlc-ai/web-llm@0.2.85'), loadingSignal, () => {});
      aborted(loadingSignal);
      worker = new Worker('/browser-model-worker.mjs', { type: 'module' });
      const currentWorker = worker;
      let failed, timer;
      const workerFailure = new Promise((_, reject) => {
        failed = () => reject(Error('The browser model worker could not start. Check your connection and try again.'));
        currentWorker.addEventListener('error', failed, { once: true });
        timer = setTimeout(() => reject(Error('The model download timed out. Check your connection and try again.')), 900000);
      });
      let loaded;
      try { loaded = await withAbort(Promise.race([webllm.CreateWebWorkerMLCEngine(currentWorker, model, {
        initProgressCallback: info => { if (!loadingSignal.aborted) publish({ phase: 'loading', text: info.text, progress: Math.max(0, Math.min(1, info.progress || 0)) }); },
      }, { context_window_size: 16384 }), workerFailure]), loadingSignal, () => currentWorker.terminate()); }
      finally { clearTimeout(timer); currentWorker.removeEventListener('error', failed); }
      aborted(loadingSignal);
      engine = loaded;
      publish({ phase: 'ready', model, progress: 1, text: 'Model ready. Your prompts stay on this device.' });
      return engine;
    })().catch(error => {
      worker?.terminate(); worker = engine = undefined;
      publish({ phase: error.name === 'AbortError' ? 'idle' : 'error', progress: 0, text: error.name === 'AbortError' ? 'Download stopped. You can try again.' : error.message || 'The model could not load. Try the smaller model or another device.' });
      throw error;
    }).finally(() => { loading = undefined; loadController = undefined; });
  }
  return withAbort(loading, signal, stopDownload);
}
export async function generate(messages, { schema, maxTokens = 1600, signal } = {}) {
  if (active) throw Error('A browser model task is already running. Wait or stop it first.');
  active = true;
  let local;
  try {
    local = await loadModel({ signal });
    aborted(signal);
    publish({ phase: 'generating', text: 'Working on your device…' });
    const generationSignal = signal ? AbortSignal.any([signal, AbortSignal.timeout(300000)]) : AbortSignal.timeout(300000);
    const response = await withAbort(local.chat.completions.create({
      messages,
      temperature: 0.2,
      max_tokens: maxTokens,
      stream: false,
      ...(schema ? { response_format: { type: 'json_object', schema: JSON.stringify(schema) } } : {}),
      extra_body: { enable_thinking: false },
    }), generationSignal, () => local.interruptGenerate());
    aborted(signal);
    const choice = response.choices?.[0];
    if (!choice?.message?.content) throw Error('The model returned no result. Try a shorter input.');
    if (choice.finish_reason === 'length') throw Error('The result reached its length limit. Shorten the input and try again.');
    const text = choice.message.content.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
    return { text, value: schema ? JSON.parse(text) : text, model: state.model, usage: response.usage };
  } catch (error) {
    if (/context|token.*limit|exceed/i.test(error.message || '')) throw Error('This input is too long for the browser model. Use shorter excerpts and try again.');
    throw error;
  } finally {
    active = false;
    if (engine) publish({ phase: 'ready', text: 'Model ready. Your prompts stay on this device.' });
  }
}
