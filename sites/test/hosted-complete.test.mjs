import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeDocumentsHosted } from '../lib/hosted-analysis.mjs';
import { hostedQuoteOptions } from '../lib/analysis-contract.mjs';

const apiKey = 'sk-test-only-not-a-real-credential';
const agreementId = '00000000-0000-4000-8000-000000000001';
const invoiceId = '00000000-0000-4000-8000-000000000002';
const work = {
  title: 'Brand Kit v1', customer: 'Harbor Market', description: 'Completed the final logo and style guide.',
  documents: [
    { id: agreementId, name: 'Agreement.pdf', pages: ['Agreed final fee: USD 2400.00.\n' + 'Unchanged project record. '.repeat(340), 'Written customer acceptance is required.\nSend billing to Morgan Reed.'] },
    { id: invoiceId, name: 'Invoice.txt', pages: ['Final invoice total:\nUSD 2800.00.'] },
  ],
  requirements: [{ existing: true }], revision: 3,
};

test('hosted analysis sends complete pages and work context in one request with two verified citations', async t => {
  const before = JSON.stringify(work);
  const evidence = [
    { documentId: agreementId, page: 1, quote: hostedQuoteOptions(work.documents[0].pages[0])[0] },
    { documentId: invoiceId, page: 1, quote: hostedQuoteOptions(work.documents[1].pages[0])[0] },
  ];
  const proposal = { title: 'Final billing amount', category: 'amount', status: 'conflict', reason: 'The agreed USD 2400.00 differs from the USD 2800.00 invoice.', evidence };
  const request = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/analyze/visitor');
    assert.equal(options.headers.Authorization, `Bearer ${apiKey}`);
    const payload = JSON.parse(options.body);
    assert.deepEqual(payload.batch.work, { title: work.title, customer: work.customer, description: work.description });
    assert.equal(payload.model, 'gpt-5.4');
    assert.equal(payload.batch.source.length, 3);
    assert.equal(payload.batch.source[0].text, work.documents[0].pages[0]);
    assert(payload.batch.source[0].text.length > 6000);
    assert.equal(payload.batch.source[1].page, 2);
    assert.equal(payload.batch.source[1].text, work.documents[0].pages[1]);
    assert.equal(payload.batch.source[2].text, work.documents[1].pages[0]);
    assert.equal('earlierProposals' in payload.batch, false);
    assert.equal(options.body.includes(apiKey), false);
    return Response.json({ value: { requirements: [proposal] }, model: 'gpt-5.4' });
  });
  assert.deepEqual(await analyzeDocumentsHosted(work, { apiKey }), [proposal]);
  assert.equal(request.mock.callCount(), 1);
  assert.equal(JSON.stringify(work), before);
});

test('hosted analysis rejects the entire oversized work before any request instead of truncating it', async t => {
  const request = t.mock.method(globalThis, 'fetch', async () => { throw Error('Unexpected paid request'); });
  const oversized = { ...work, documents: [{ ...work.documents[0], pages: ['x'.repeat(32001)] }] };
  const before = JSON.stringify(oversized);
  await assert.rejects(analyzeDocumentsHosted(oversized, { apiKey }), /32,000 extracted characters/);
  assert.equal(request.mock.callCount(), 0);
  assert.equal(JSON.stringify(oversized), before);
});
