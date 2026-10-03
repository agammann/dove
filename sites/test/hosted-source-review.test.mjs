import test from 'node:test';
import assert from 'node:assert/strict';
import { HostedAnalysisInput, hostedAnalysisSchema, validateHostedResult, hostedRequirements, validateBatchResult } from '../lib/analysis-contract.mjs';
import { visitorAnalysis } from '../lib/server/visitor-analysis.mjs';
import { analyzeDocumentsHosted } from '../lib/hosted-analysis.mjs';

const agreement = '00000000-0000-4000-8000-000000000001';
const invoice = '00000000-0000-4000-8000-000000000002';
const unknown = '00000000-0000-4000-8000-000000000003';
const source = [
  { documentId: agreement, name: 'Agreement.txt', page: 1, text: 'Payment is due 30 days after the invoice date.' },
  { documentId: invoice, name: 'Invoice.pdf', page: 1, text: 'Invoice date: October 2, 2026.' },
  { documentId: invoice, name: 'Invoice.pdf', page: 2, text: 'Due date: October 25, 2026.' },
  { documentId: invoice, name: 'Invoice.pdf', page: 3, text: 'PO-1042. Completed website handoff.' },
];
const sourceReview = [{ documentId: agreement, pages: [1] }, { documentId: invoice, pages: [1, 2, 3] }];
const quote = section => ({ documentId: section.documentId, page: section.page, quote: section.text });
const conflict = { title: 'Invoice payment timing', category: 'custom', status: 'conflict',
  reason: 'October 2 plus 30 days implies November 1; the invoice instead states October 25.',
  evidence: source.slice(0, 3).map(quote), missingInformation: null };
const value = requirements => ({ sourceReview, requirements });
const details = { title: 'Website handoff', customer: 'Fictional customer', description: 'Completed website.' };
const work = { ...details, documents: [
  { id: agreement, name: source[0].name, pages: [source[0].text] },
  { id: invoice, name: source[1].name, pages: source.slice(1).map(section => section.text) },
] };
const key = ['sk', 'synthetic-not-a-real-credential'].join('-');
const request = batch => new Request('https://dove.example/api/analyze/visitor', {
  method: 'POST', headers: { Origin: 'https://dove.example', 'Content-Type': 'application/json', Authorization: `Bearer ${key}` },
  body: JSON.stringify({ batch, model: 'gpt-5.4' }),
});
const completion = raw => Response.json({ status: 'completed', output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(raw) }] }] });

test('three distinct timing citations survive the actual visitor handler and client boundary', async t => {
  let providerCalls = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/analyze/visitor');
    return visitorAnalysis(new Request('https://dove.example' + url, { ...options, headers: { ...options.headers, Origin: 'https://dove.example' } }), {
      fetchImpl: async (_url, providerOptions) => {
        providerCalls++;
        const body = JSON.parse(providerOptions.body);
        assert.deepEqual(JSON.parse(body.input).source, source);
        assert.equal(body.text.format.schema.properties.requirements.items.properties.evidence.maxItems, 3);
        return completion(value([conflict]));
      },
    });
  });
  const result = await analyzeDocumentsHosted(work, { apiKey: key });
  const { missingInformation, ...saved } = conflict;
  assert.equal(missingInformation, null);
  assert.deepEqual(result, [{ ...saved, title: 'Review conflicting source information' }]);
  assert.equal(providerCalls, 1);
  assert.throws(() => validateHostedResult(source, value([{ ...conflict, evidence: source.map(quote) }])));
  assert.throws(() => validateHostedResult(source, value([{ ...conflict, evidence: [quote(source[0]), quote(source[1]), { ...quote(source[2]), page: 3 }] }])));
});

test('the complete declared source scope rejects omissions, duplicate pages, and invented documents', () => {
  const invalidScopes = [
    [], sourceReview.slice(0, 1),
    [sourceReview[0], { documentId: invoice, pages: [1, 3] }],
    [sourceReview[0], { documentId: invoice, pages: [1, 2, 2, 3] }],
    [...sourceReview, sourceReview[0]],
    [sourceReview[0], { documentId: unknown, pages: [1, 2, 3] }],
    [sourceReview[0], { documentId: invoice, pages: [1, 2, 4] }],
  ];
  for (const scope of invalidScopes) assert.throws(() => validateHostedResult(source, { sourceReview: scope, requirements: [conflict] }));
  assert.doesNotThrow(() => validateHostedResult(source, { sourceReview: [{ documentId: invoice, pages: [3, 1, 2] }, sourceReview[0]], requirements: [conflict] }));
  assert.equal(hostedAnalysisSchema(source).properties.sourceReview.minItems, 2);
});

test('duplicate input pages and incomplete returned scope fail at the request boundaries', async t => {
  const batch = { work: details, source };
  assert.equal(HostedAnalysisInput.safeParse(batch).success, true);
  const duplicate = { ...batch, source: [...source, source[0]] };
  const response = await visitorAnalysis(request(duplicate), { fetchImpl: () => { throw Error('No provider request allowed'); } });
  assert.equal(response.status, 400);
  const incomplete = { sourceReview: sourceReview.slice(0, 1), requirements: [conflict] };
  const rejected = await visitorAnalysis(request(batch), { fetchImpl: async () => completion(incomplete) });
  assert.equal(rejected.status, 502);
  t.mock.method(globalThis, 'fetch', async () => Response.json({ value: incomplete }));
  await assert.rejects(analyzeDocumentsHosted(work, { apiKey: key }), /source and status checks/);
});

test('a real context quote never turns a false absence assertion into a saved factual claim', () => {
  // The dates are present on pages 1 and 2. This is a deliberately wrong model judgment.
  const missing = { title: 'Invoice dates are absent', category: 'custom', status: 'missing',
    reason: 'The invoice has no issue date or due date.', evidence: [quote(source[3])],
    missingInformation: { field: 'invoice_dates', documentId: invoice } };
  const [saved] = hostedRequirements(source, value([missing]));
  assert.equal(saved.title, 'Confirm invoice dates');
  assert.equal(saved.status, 'missing');
  assert.match(saved.reason, /The model did not identify invoice and due dates/);
  assert.match(saved.reason, /which it identified as an invoice/);
  assert.match(saved.reason, /2 document\(s\), 4 extracted page\(s\)/);
  assert.match(saved.reason, /This is not proof of absence/);
  assert.match(saved.reason, /original documents/);
  assert.doesNotMatch(saved.reason, /The invoice has no/);
  assert.deepEqual(saved.evidence, missing.evidence);
  assert.deepEqual(Object.keys(saved).sort(), ['category', 'evidence', 'reason', 'status', 'title']);
  const [other] = hostedRequirements(source, value([{ ...missing, missingInformation: { field: 'other', documentId: null } }]));
  assert.equal(other.title, 'Review possible missing information');
  assert.match(other.reason, /model flagged possible missing information/);
  assert.doesNotMatch(other.reason, /The invoice has no/);
});

test('missing-information metadata cannot approve work, invent a target, or bypass context evidence', () => {
  const missing = { ...conflict, status: 'missing', missingInformation: { field: 'invoice_date', documentId: invoice } };
  for (const item of [
    { ...missing, missingInformation: null },
    { ...missing, category: 'amount' },
    { ...missing, missingInformation: { field: 'invoice_date', documentId: null } },
    { ...missing, missingInformation: { field: 'invoice_date', documentId: unknown } },
    { ...missing, evidence: [quote(source[0])] },
    { ...missing, status: 'satisfied' }, { ...missing, status: 'waived' },
    { ...missing, status: 'received' }, { ...missing, status: 'conflict' },
  ]) assert.throws(() => hostedRequirements(source, value([item])));
  const { missingInformation, ...device } = { ...conflict, evidence: [quote(source[0])] };
  assert.equal(missingInformation, null);
  assert.deepEqual(validateBatchResult(source, { requirements: [device] }), { requirements: [device] });
  assert.throws(() => validateBatchResult(source, { requirements: [{ ...device, evidence: source.slice(0, 2).map(quote) }] }));
});

test('an affirmative conflict title cannot survive hosted normalization with three genuine source quotes', () => {
  const observed = {
  "title": "Printed due date matches the 30-day payment term",
  "category": "custom",
  "reason": "The contract implies payment due 2026-11-01 from the stated invoice date, but the invoice prints 2026-10-25.",
  "status": "conflict",
  "evidence": [
    {
      "documentId": "6c36f0a0-d1e4-472a-a5d8-e5f9fb21f4ea",
      "page": 2,
      "quote": "Service agreement - completion and billing Fictional QA document. Harbor Market / Brand Kit v1. Written customer acceptance of the final logo and style guide is required before billing. The authorized billing recipient is Morgan Reed at accounts@harbor.example.invalid. Payment is due 30 days after the invoice date. Fictional verification record | Page 2 of 2"
    },
    {
      "documentId": "9d4efa5f-339b-482b-be8b-43aa29102776",
      "page": 1,
      "quote": "FICTIONAL INVOICE DV-1042 - page 1 of 3 Cedar Studio to Harbor Market For: Final logo and style guide for Brand Kit v1. Final invoice total: USD 2400.00, including all applicable taxes. Invoice date: 2026-10-02."
    },
    {
      "documentId": "9d4efa5f-339b-482b-be8b-43aa29102776",
      "page": 2,
      "quote": "FICTIONAL INVOICE DV-1042 - page 2 of 3 Cedar Studio to Harbor Market Due date: 2026-10-25."
    }
  ],
  "missingInformation": null
};
  const supplied = observed.evidence.map(item => ({ documentId: item.documentId, name: 'Source document', page: item.page, text: item.quote }));
  const scope = [{ documentId: observed.evidence[0].documentId, pages: [2] }, { documentId: observed.evidence[1].documentId, pages: [1, 2] }];
  const raw = { sourceReview: scope, requirements: [observed] };
  const before = structuredClone(raw);
  const [saved] = hostedRequirements(supplied, raw);
  assert.equal(saved.title, 'Review conflicting source information');
  assert.equal(saved.status, 'conflict');
  assert.equal(saved.reason, observed.reason);
  assert.deepEqual(saved.evidence, observed.evidence);
  assert.deepEqual(Object.keys(saved).sort(), ['category', 'evidence', 'reason', 'status', 'title']);
  assert.deepEqual(raw, before, 'The retained raw model response must not be rewritten');
  assert.equal(validateHostedResult(supplied, raw).requirements[0].title, observed.title);
});
