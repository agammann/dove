import { HostedAnalysisInput, hostedRequirements } from './analysis-contract.mjs';

export const HOSTED_CHARACTER_LIMIT = 32000;

function visitorKey(apiKey) {
  if (typeof apiKey !== 'string' || !/^sk-[A-Za-z0-9_-]{16,512}$/.test(apiKey.trim())) throw Error('Enter your own valid OpenAI API key to use hosted analysis.');
  return apiKey.trim();
}

async function requestAnalysis(batch, apiKey, model, signal) {
  signal?.throwIfAborted();
  const response = await fetch('/api/analyze/visitor', {
    method: 'POST', credentials: 'omit', redirect: 'error', cache: 'no-store', signal,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ batch, model }),
  });
  let result;
  try { result = await response.json(); }
  catch (error) {
    signal?.throwIfAborted();
    if (error?.name === 'AbortError') throw error;
    throw Error('The service did not return an analysis. Your checklist is unchanged. Try again.');
  }
  signal?.throwIfAborted();
  if (!response.ok) throw Error(typeof result?.error === 'string' ? result.error : 'Hosted analysis failed. Your checklist is unchanged.');
  return result;
}

export async function analyzeDocumentsHosted(work, { apiKey, model = 'gpt-5.4', signal, onProgress = () => {} } = {}) {
  signal?.throwIfAborted();
  let batch;
  try {
    const source = work.documents.flatMap(document => document.pages.flatMap((text, index) => text.length ? [{ documentId: document.id, name: document.name, page: index + 1, text }] : []));
    const characters = source.reduce((total, page) => total + page.text.length, 0);
    if (characters > HOSTED_CHARACTER_LIMIT) throw Error('hosted-character-limit');
    batch = HostedAnalysisInput.parse({ work: { title: work.title, customer: work.customer, description: work.description }, source });
  } catch (error) {
    if (error?.message === 'hosted-character-limit') throw Error('Hosted analysis supports up to 32,000 extracted characters across all documents. Use device analysis or review this work manually. Your checklist is unchanged.');
    throw Error('Upload readable documents with valid work details within the hosted analysis limits. Your checklist is unchanged.');
  }
  const key = visitorKey(apiKey);
  onProgress(`Reading all ${work.documents.length} document${work.documents.length === 1 ? '' : 's'} together using OpenAI…`);
  const result = await requestAnalysis(batch, key, model, signal);
  try { return hostedRequirements(batch.source, result.value); }
  catch { throw Error('The analysis did not pass source and status checks. Your checklist is unchanged.'); }
}
