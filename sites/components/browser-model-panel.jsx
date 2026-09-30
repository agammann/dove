import React, { useEffect, useRef, useState } from 'react';
import { MODELS, modelState, subscribeModel, selectModel, loadModel, stopDownload } from '../lib/browser-model.mjs';

export default function BrowserModelPanel() {
  const [state, setState] = useState(modelState);
  const [error, setError] = useState('');
  const controller = useRef(null);
  useEffect(() => { const unsubscribe = subscribeModel(setState); return () => { unsubscribe(); controller.current?.abort(); }; }, []);
  const busy = state.phase === 'loading' || state.phase === 'generating';
  async function download() {
    controller.current = new AbortController(); setError('');
    try { await loadModel({ signal: controller.current.signal }); }
    catch (e) { if (e.name !== 'AbortError') setError(e.message); }
    finally { controller.current = null; }
  }
  return <section aria-label="Browser model" style={{ margin: '16px 0', padding: '14px 16px', background: '#f3f7f5', border: '1px solid #d1ddd6', borderRadius: 10, color: '#243d32', fontSize: 14 }}>
    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
      <strong>Runs on your device</strong>
      <label>Model <select aria-label="Browser model" disabled={busy} value={state.model.replace('q4f32', 'q4f16')} onChange={e => { setError(''); selectModel(e.target.value); }} style={{ maxWidth: '100%' }}>{MODELS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}</select></label>
      {state.phase !== 'ready' && state.phase !== 'generating' && <button type="button" disabled={busy} onClick={download}>{state.phase === 'loading' ? 'Downloading…' : 'Download model'}</button>}
      {state.phase === 'loading' && <button type="button" onClick={stopDownload}>Stop download</button>}
    </div>
    <p role="status" style={{ margin: '8px 0 0', overflowWrap: 'anywhere' }}>{state.text}</p>
    {state.phase === 'loading' && <progress aria-label="Model download progress" value={state.progress} max="1" style={{ width: '100%', marginTop: 8 }} />}
    <p style={{ margin: '8px 0 0', fontSize: 12 }}>No account or API key. The first download is large and needs free storage and a compatible graphics device. Model files come from public hosts; your prompts are processed in this browser.</p>
    {error && <p role="alert">{error}</p>}
  </section>;
}
