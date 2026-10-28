import test from 'node:test';
import assert from 'node:assert/strict';
import { AnalysisBatch, HostedAnalysisInput } from '../lib/analysis-contract.mjs';

const section = { documentId: '00000000-0000-4000-8000-000000000001', name: 'Agreement.txt', page: 1, text: 'Source text.' };
const work = { title: 'Completed work', customer: 'Example customer', description: '' };

test('Zod upgrade preserves analysis defaults, source identity, and strict fields', () => {
  assert.deepEqual(AnalysisBatch.parse({ source: [section] }), { source: [section], earlierProposals: [] });
  const batch = { work, source: [section] };
  assert.deepEqual(HostedAnalysisInput.parse(batch), batch);
  for (const input of [
    { ...batch, unexpected: true },
    { ...batch, source: [{ ...section, page: 1.5 }] },
    { ...batch, source: [{ ...section, documentId: 'invalid' }] },
    { ...batch, source: [section, section] },
  ]) assert.equal(HostedAnalysisInput.safeParse(input).success, false);
});

test('constrained source arrays reject oversize before visiting every invalid element', () => {
  let reads = 0;
  const invalid = Object.defineProperty({}, 'documentId', { enumerable: true, get() { reads++; return 'invalid'; } });
  const result = AnalysisBatch.safeParse({ source: Array(10000).fill(invalid) });
  assert.equal(result.success, false);
  assert.ok(result.error.issues.some(issue => issue.code === 'too_big' && issue.path[0] === 'source'));
  assert.equal(reads, 0, 'the length bound must be applied before validating elements');
  assert.equal(AnalysisBatch.safeParse({ source: Array(400).fill(section) }).success, true);
});
