import BrowserModelPanel from './browser-model-panel';
import { HOSTED_CHARACTER_LIMIT } from '../lib/hosted-analysis.mjs';

type Props = {
  sourceCharacters: number;
  mode: 'browser' | 'hosted';
  apiKey: string;
  model: string;
  busy: boolean;
  onMode: (mode: 'browser' | 'hosted') => void;
  onKey: (key: string) => void;
  onModel: (model: string) => void;
};

export default function AnalysisOptions({ sourceCharacters, mode, apiKey, model, busy, onMode, onKey, onModel }: Props) {
  return <section className="d-analysis-options" aria-label="Document analysis mode">
    <fieldset disabled={busy}>
      <legend>Choose how to analyze</legend>
      <label className="d-check"><input type="radio" name="analysis-mode" checked={mode === 'browser'} onChange={() => onMode('browser')}/>On this device — no API charge; requires WebGPU</label>
      <label className="d-check"><input type="radio" name="analysis-mode" checked={mode === 'hosted'} onChange={() => onMode('hosted')}/>OpenAI with your key — paid API usage; no model download</label>
    </fieldset>
    {mode === 'browser' ? <><BrowserModelPanel/><p className="d-muted">Browser models can miss requirements or misread evidence. Check every proposal and add missing items manually.</p></> : <>
      <p className={sourceCharacters > HOSTED_CHARACTER_LIMIT ? "d-notice" : "d-muted"}>Hosted analysis reads all documents together, up to 32,000 extracted characters, and suggests up to 20 requirements. This work has {sourceCharacters.toLocaleString()} characters.{sourceCharacters > HOSTED_CHARACTER_LIMIT ? " Use device analysis or review this work manually; hosted analysis will not send a partial document set." : " Review every proposal and check for omissions or unresolved conflicts."}</p>
      <div className="d-form-grid">
        <label>Hosted model<select value={model} disabled={busy} onChange={event => onModel(event.target.value)}><option value="gpt-5.4">GPT-5.4</option><option value="gpt-5.4-mini">GPT-5.4 mini · lower cost</option></select></label>
        <label>Your OpenAI API key<input type="password" value={apiKey} autoComplete="off" spellCheck={false} maxLength={515} disabled={busy} onChange={event => onKey(event.target.value)} aria-describedby="hosted-analysis-privacy" placeholder="Paste your API key"/></label>
      </div>
      <button type="button" disabled={busy || !apiKey} onClick={() => onKey('')}>Clear key</button>
      <p id="hosted-analysis-privacy" className="d-muted">Analyze with OpenAI sends all extracted document text and filenames, plus the work title, customer and description, through Dove&apos;s server to OpenAI. Each analysis makes one paid API request using your account. Your key stays in this tab&apos;s memory and is sent only for analysis; Dove does not save it in workspace data or backups. Clear key, refresh, or switch to device mode to remove it. Requests disable provider response storage; OpenAI&apos;s data policies still apply. <a href="https://openai.com/api/pricing/" target="_blank" rel="noopener noreferrer">Check current prices</a>.</p>
    </>}
  </section>;
}
