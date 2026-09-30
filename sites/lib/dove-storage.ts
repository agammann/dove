import type { Work, Workspace } from "./dove-types";
import { need } from "./dove-core";

export type State = { version: number; workspace: Workspace; work: Work[] };
export type StoredFile = { id: string; workId: string; name: string; mime: string; bytes: Uint8Array };
export const MAX_BYTES = 64 * 1024 * 1024;
let opening: Promise<IDBDatabase> | undefined;

function request<T>(r: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
}
function finished(tx: IDBTransaction) {
  return new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = tx.onabort = () => reject(tx.error || new Error("Local save was interrupted. Your previous work is unchanged."));
  });
}
async function database() {
  if (!opening) opening = new Promise<IDBDatabase>((resolve, reject) => {
    if (!globalThis.indexedDB) { reject(new Error("This browser does not allow local storage. Enable site storage to use Dove.")); return; }
    const r = indexedDB.open("dove-local-workspace", 1);
    r.onupgradeneeded = () => { r.result.createObjectStore("state"); r.result.createObjectStore("files", { keyPath: "id" }); };
    r.onsuccess = () => { r.result.onversionchange = () => { r.result.close(); opening = undefined; }; resolve(r.result); };
    r.onerror = () => reject(new Error("Dove could not open browser storage. Check your browser's site-storage settings."));
    r.onblocked = () => reject(new Error("Close other Dove tabs and reopen this workspace."));
  }).catch(error => { opening = undefined; throw error; });
  return opening;
}
export async function readState(): Promise<State> {
  const db = await database(), tx = db.transaction("state", "readonly");
  return (await request(tx.objectStore("state").get("workspace"))) as State | undefined || {
    version: 0, workspace: { id: "local", name: "My workspace", billing: "", paused: 0 }, work: [],
  };
}
export async function readFile(id: string): Promise<StoredFile> {
  const db = await database(), tx = db.transaction("files", "readonly");
  const value = await request(tx.objectStore("files").get(id)) as StoredFile | undefined;
  need(value, "This file is not available in this browser. Restore a complete Dove backup.");
  return value;
}
export async function snapshot() {
  const db = await database(), tx = db.transaction(["state", "files"], "readonly");
  const [state, files] = await Promise.all([
    request(tx.objectStore("state").get("workspace")) as Promise<State | undefined>,
    request(tx.objectStore("files").getAll()) as Promise<StoredFile[]>,
  ]);
  return { state: state || await readState(), files };
}
// Keep the version check and all record/file writes in one transaction. A stale
// tab cannot overwrite a newer workspace, and failed saves cannot leave files orphaned.
export async function commit(state: State, additions: StoredFile[] = [], deletions: string[] = [], replace = false) {
  need(new TextEncoder().encode(JSON.stringify(state)).byteLength <= 19 * 1024 * 1024, "Workspace records have reached their limit. Export a backup and remove unneeded work.");
  need(state.work.every(w => JSON.stringify(w).length < 450000), "This work item has reached its record limit.");
  const db = await database(), tx = db.transaction(["state", "files"], "readwrite"), done = finished(tx);
  try {
    const records = tx.objectStore("state"), files = tx.objectStore("files");
    const current = await request(records.get("workspace")) as State | undefined;
    need((current?.version || 0) === state.version, "Work changed in another tab. Reload Dove before saving again.", 409);
    const existing = replace ? [] : await request(files.getAll()) as StoredFile[];
    const removed = new Set([...deletions, ...additions.map(f => f.id)]);
    const kept = existing.filter(f => !removed.has(f.id));
    need(kept.length + additions.length <= 100, "The workspace can contain at most 100 stored files.");
    need([...kept, ...additions].reduce((n, f) => n + f.bytes.byteLength, 0) <= MAX_BYTES, "The workspace storage limit is 64 MB. Export a backup and remove unneeded work.");
    if (replace) files.clear();
    for (const id of deletions) files.delete(id);
    for (const file of additions) files.put(file);
    records.put({ ...state, version: state.version + 1 }, "workspace");
    await done;
  } catch (error) {
    try { tx.abort(); } catch { /* Transaction already settled. */ }
    await done.catch(() => {});
    if (error instanceof DOMException && error.name === "QuotaExceededError") throw new Error("Your browser's storage is full. Export a backup, free space and try again.");
    throw error;
  }
}
export function download(bytes: Uint8Array, name: string, mime: string) {
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: mime }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
export async function downloadFile(id: string) {
  const f = await readFile(id); download(f.bytes, f.name, f.mime);
}
