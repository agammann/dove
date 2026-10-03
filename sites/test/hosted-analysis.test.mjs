import test from 'node:test';
import assert from 'node:assert/strict';
import { visitorAnalysis } from '../lib/server/visitor-analysis.mjs';
import { analyzeDocumentsHosted } from '../lib/hosted-analysis.mjs';
import { analyzeDocumentsBrowser } from '../lib/browser-analysis.mjs';
import { hostedAnalysisSchema, validateHostedResult } from '../lib/analysis-contract.mjs';

// Synthetic credential syntax only; tests never call a provider.
const key = 'sk-test-only-not-a-real-credential';
const id = '00000000-0000-4000-8000-000000000001';
const source = [{ documentId: id, name: 'Agreement.txt', page: 1, text: 'Purchase order PO-1042 must accompany the invoice. The customer supplied PO-1042.' }];
const batch = { source, work: { title: 'Logo handoff', customer: 'Example Customer', description: 'Completed logo and style guide.' } };
const hostedWork = { ...batch.work, documents: [{ id, name: source[0].name, pages: [source[0].text] }] };
const proposal = { title: 'Purchase order', category: 'purchase_order', status: 'received', reason: 'The customer supplied the required purchase order.', evidence: [{ documentId: id, page: 1, quote: source[0].text }] };
const sourceReview = [{ documentId: id, pages: [1] }];
const completion = requirements => Response.json({ status: 'completed', output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify({ sourceReview, requirements: requirements.map(item => ({ ...item, missingInformation: null })) }) }] }] });
const request = (payload = { batch }, options = {}) => new Request('https://dove.example/api/analyze/visitor', {
  method: 'POST', headers: { Origin: 'https://dove.example', 'Content-Type': 'application/json', Authorization: `Bearer ${key}` }, body: JSON.stringify(payload), ...options,
});

test('visitor analysis uses only the supplied key and a fixed nonpersistent provider request', async () => {
  let calls = 0;
  const response = await visitorAnalysis(request(), { fetchImpl: async (url, options) => {
    calls++;
    assert.equal(url, 'https://api.openai.com/v1/responses');
    assert.equal(options.headers.Authorization, `Bearer ${key}`);
    assert.equal(options.redirect, 'manual');
    const payload = JSON.parse(options.body);
    assert.equal(payload.model, 'gpt-5.4');
    assert.equal(payload.store, false);
    assert.equal(payload.reasoning.effort, 'medium');
    assert.equal(JSON.stringify(payload).includes(key), false);
    assert.deepEqual(JSON.parse(payload.input), batch);
    assert.deepEqual(payload.text.format.schema.properties.requirements.items.properties.evidence.items.properties.quote.enum, [source[0].text]);
    return completion([proposal]);
  } });
  assert.equal(response.status, 200); assert.equal(calls, 1);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.deepEqual((await response.json()).value, { sourceReview, requirements: [{ ...proposal, missingInformation: null }] });
});

test('missing keys, foreign origins and unsupported payloads never reach a provider', async () => {
  const headers = { Origin: 'https://dove.example', 'Content-Type': 'application/json' };
  const cases = [
    [request({ batch }, { headers }), 401],
    [request({ batch }, { headers: { ...headers, Origin: 'https://elsewhere.example', Authorization: `Bearer ${key}` } }), 403],
    [request({ batch, model: 'unsupported-model' }), 400],
    [request({ batch, provider: 'https://elsewhere.example' }), 400],
    [request({ batch: { ...batch, source: [...source, { ...source[0], text: 'x'.repeat(16000) }, { ...source[0], text: 'x'.repeat(16000) }] } }), 400],
    [request({ batch: { ...batch, source: [{ ...source[0], text: key }] } }), 400],
    [request({ batch, padding: 'x'.repeat(320 * 1024) }), 413],
  ];
  for (const [input, status] of cases) {
    const response = await visitorAnalysis(input, { fetchImpl: () => { throw Error('Unexpected provider request'); } });
    assert.equal(response.status, status);
    assert.equal((await response.text()).includes(key), false);
  }
});

test('provider proposals cannot invent quotes, change source attribution or approve work', async () => {
  const invalid = [
    { ...proposal, status: 'satisfied' }, { ...proposal, status: 'waived' },
    { ...proposal, evidence: [{ ...proposal.evidence[0], quote: 'Invented customer acceptance.' }] },
    { ...proposal, evidence: [{ ...proposal.evidence[0], page: 2 }] },
    { ...proposal, evidence: [{ ...proposal.evidence[0], documentId: '00000000-0000-4000-8000-000000000002' }] },
    { ...proposal, reason: key },
  ];
  for (const value of invalid) {
    const response = await visitorAnalysis(request(), { fetchImpl: async () => completion([value]) });
    assert.equal(response.status, 502); assert.equal((await response.text()).includes(key), false);
  }
});

test('provider failure details are not returned to the browser', async () => {
  for (const status of [401, 429, 500]) {
    const response = await visitorAnalysis(request(), { fetchImpl: async () => new Response(`private provider detail ${key}`, { status }) });
    assert.equal(response.status, status === 500 ? 502 : status);
    assert.doesNotMatch(await response.text(), /private provider detail|sk-test-only/);
  }
});

test('canceling an in-flight provider request propagates its signal', async () => {
  const controller = new AbortController();
  let started;
  const start = new Promise(resolve => { started = resolve; });
  const result = visitorAnalysis(request({ batch }, { signal: controller.signal }), { fetchImpl: async (_url, { signal }) => {
    started();
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(signal.reason), { once: true }));
  } });
  await start; controller.abort();
  assert.equal((await result).status, 499);
});

test('provider redirects are rejected without forwarding the visitor credential', async () => {
  let calls = 0;
  const response = await visitorAnalysis(request(), { fetchImpl: async (url, options) => {
    calls++;
    assert.equal(url, 'https://api.openai.com/v1/responses');
    assert.equal(options.redirect, 'manual');
    return new Response(null, { status: 302, headers: { Location: 'https://elsewhere.example' } });
  } });
  assert.equal(response.status, 502);
  assert.equal(calls, 1);
  assert.equal((await response.text()).includes(key), false);
});

test('hosted PDF quote enums normalize whitespace while retaining document and page validation', () => {
  const sections = [{ ...source[0], text: 'The agreed amount is USD 2400.00.\n\tThe work was accepted.' }];
  const quote = 'The agreed amount is USD 2400.00. The work was accepted.';
  const schema = hostedAnalysisSchema(sections);
  assert.deepEqual(schema.properties.requirements.items.properties.evidence.items.properties.quote.enum, [quote]);
  const value = { sourceReview, requirements: [{ ...proposal, missingInformation: null, evidence: [{ documentId: id, page: 1, quote }] }] };
  assert.deepEqual(validateHostedResult(sections, value), value);
  assert.throws(() => validateHostedResult(sections, { requirements: [{ ...proposal, evidence: [{ documentId: id, page: 2, quote }] }] }));
});

test('the client rejects invalid input before requesting paid analysis', async t => {
  const requestMock = t.mock.method(globalThis, 'fetch', async () => { throw Error('Unexpected request'); });
  await assert.rejects(analyzeDocumentsHosted({ ...hostedWork, documents: [] }, { apiKey: key }), /Upload readable documents/);
  assert.equal(requestMock.mock.callCount(), 0);
});

test('the client preserves response-body cancellation and rejects invalid proposals', async t => {
  const aborted = new DOMException('Stopped.', 'AbortError');
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({ start(stream) { stream.error(aborted); } })));
  await assert.rejects(analyzeDocumentsHosted(hostedWork, { apiKey: key }), error => error === aborted);
  fetchMock.mock.mockImplementation(async () => Response.json({ value: { requirements: [{ ...proposal, status: 'satisfied' }] } }));
  await assert.rejects(analyzeDocumentsHosted(hostedWork, { apiKey: key }), /source and status checks/);
});

test('generation errors and cancellation leave the original work unchanged', async () => {
  const work = { documents: [{ id, name: source[0].name, pages: [source[0].text] }], requirements: [{ existing: true }], revision: 3 };
  const before = JSON.stringify(work);
  await assert.rejects(analyzeDocumentsBrowser(work, { runGeneration: async () => ({ value: { requirements: [{ ...proposal, status: 'satisfied' }] } }) }), /human review/);
  const controller = new AbortController();
  await assert.rejects(analyzeDocumentsBrowser(work, { signal: controller.signal, runGeneration: async () => { controller.abort(); return { value: { requirements: [proposal] } }; } }), { name: 'AbortError' });
  assert.equal(JSON.stringify(work), before);
});


test('a conflict from a later source batch replaces the earlier reassuring explanation', async () => {
  const firstText = 'The agreed fee is USD 2400.00. ' + 'Routine delivery record. '.repeat(360);
  const laterText = 'The final invoice is USD 2800.00. No revised agreement is supplied.';
  const laterId = '00000000-0000-4000-8000-000000000002';
  const work = { documents: [{ id, name: 'Agreement.txt', pages: [firstText] }, { id: laterId, name: 'Invoice.txt', pages: [laterText] }] };
  let calls = 0;
  const result = await analyzeDocumentsBrowser(work, { runGeneration: async (messages) => {
    const { source } = JSON.parse(messages.find(message => message.role === 'user').content);
    const invoice = source.find(section => section.documentId === laterId);
    const section = invoice || source[0]; calls++;
    return { value: { requirements: [{ title: 'Final billing amount', category: 'amount', status: invoice ? 'conflict' : 'received', reason: invoice ? 'The invoice says USD 2800.00 but the agreed fee is USD 2400.00.' : 'The agreed fee is supported by the source.', evidence: [{ documentId: section.documentId, page: section.page, quote: section.text.slice(0, 480).trim() }] }] } };
  } });
  assert.equal(calls, 2);
  assert.equal(result.length, 1);
  assert.equal(result[0].status, 'conflict');
  assert.equal(result[0].reason, 'The invoice says USD 2800.00 but the agreed fee is USD 2400.00.');
  assert.deepEqual(result[0].evidence.map(item => item.documentId), [id, laterId]);
});
