import { z } from 'zod';
import { HostedAnalysisInput, hostedAnalysisInstructions, hostedAnalysisSchema, validateHostedResult } from '../analysis-contract.mjs';

const bodyLimit = 320 * 1024;
const VisitorInput = z.object({ batch: HostedAnalysisInput, model: z.enum(['gpt-5.4', 'gpt-5.4-mini']).default('gpt-5.4') }).strict();
class VisitorError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}
async function readLimited(response, maximum) {
  const reader = response.body?.getReader();
  if (!reader) throw new VisitorError('The request or response body was empty.');
  const parts = []; let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) throw new VisitorError('The analysis request or response is too large.', 413);
      parts.push(value);
    }
    const bytes = new Uint8Array(size); let offset = 0;
    for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
    return new TextDecoder().decode(bytes);
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
function providerFailure(status) {
  if (status === 401) return new VisitorError('OpenAI rejected this API key. Check the key and try again.', 401);
  if (status === 403 || status === 404) return new VisitorError('This key cannot access the selected model. Check its permissions or choose another model.', 403);
  if (status === 429) return new VisitorError('OpenAI reported a usage or rate limit. Check your API billing and limits, then try again.', 429);
  return new VisitorError('OpenAI could not analyze these documents. Try again later.', 502);
}

// Credentials exist only for this request. Do not add environment defaults,
// persistence, automatic retries, arbitrary provider URLs or request logging.
export async function visitorAnalysis(request, { fetchImpl = fetch } = {}) {
  let signal;
  const json = (body, status = 200) => Response.json(body, { status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' } });
  try {
    if (request.method !== 'POST') throw new VisitorError('Method not allowed.', 405);
    if (request.headers.get('Origin') !== new URL(request.url).origin) throw new VisitorError('Open Dove to analyze documents.', 403);
    const apiKey = /^Bearer (sk-[A-Za-z0-9_-]{16,512})$/.exec(request.headers.get('Authorization') || '')?.[1];
    if (!apiKey) throw new VisitorError('Enter your own valid OpenAI API key to use hosted analysis.', 401);
    if (!/^application\/json(?:;|$)/i.test(request.headers.get('Content-Type') || '')) throw new VisitorError('Send a JSON analysis request.');
    const raw = await readLimited(request, bodyLimit);
    let payload;
    try { payload = VisitorInput.parse(JSON.parse(raw)); }
    catch { throw new VisitorError('Provide a valid source section and a supported model within the analysis limits.'); }
    if (raw.includes(apiKey)) throw new VisitorError('Keep your API key in the key field, not in document text.');
    const schema = hostedAnalysisSchema(payload.batch.source);
    if (!schema) throw new VisitorError('This source section does not contain enough readable text.');
    signal = AbortSignal.any([request.signal, AbortSignal.timeout(180000)]);
    signal.throwIfAborted();
    const response = await fetchImpl('https://api.openai.com/v1/responses', {
      method: 'POST', redirect: 'manual', signal,
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: payload.model, store: false, max_output_tokens: 18000, reasoning: { effort: 'medium' },
        instructions: hostedAnalysisInstructions, input: JSON.stringify(payload.batch),
        text: { format: { type: 'json_schema', name: 'dove_requirements', strict: true, schema } },
      }),
    });
    if (!response.ok) { await response.body?.cancel(); throw providerFailure(response.status); }
    let completion;
    try { completion = JSON.parse(await readLimited(response, 2 * 1024 * 1024)); }
    catch { throw new VisitorError('OpenAI returned an unreadable analysis. Your checklist is unchanged.', 502); }
    signal.throwIfAborted();
    if (completion.status !== 'completed') throw new VisitorError('The analysis did not finish. Your checklist is unchanged. Try again.', 502);
    const content = (completion.output || []).flatMap(item => item.type === 'message' ? item.content || [] : []);
    if (content.some(part => part.type === 'refusal')) throw new VisitorError('The model could not analyze this source section. Review it manually or revise the documents.', 422);
    const text = content.filter(part => part.type === 'output_text').map(part => part.text).join('');
    if (!text || text.includes(apiKey)) throw new VisitorError('The analysis could not be returned safely. Your checklist is unchanged.', 502);
    let value;
    try { value = validateHostedResult(payload.batch.source, JSON.parse(text)); }
    catch { throw new VisitorError('The model returned proposals that did not pass source and status checks. Your checklist is unchanged.', 502); }
    return json({ value, model: payload.model });
  } catch (error) {
    if (request.signal.aborted) return json({ error: 'Analysis canceled.' }, 499);
    if (signal?.aborted) return json({ error: 'The analysis timed out. Your checklist is unchanged. Try again.' }, 504);
    return json({ error: error instanceof VisitorError ? error.message : 'The analysis could not be completed. Your checklist is unchanged. Try again.' }, error instanceof VisitorError ? error.status : 502);
  }
}
