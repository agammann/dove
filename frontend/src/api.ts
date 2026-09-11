export type Row = { id: string; created: number; [key: string]: any };
export type Detail = {
  work: Row;
  document: Row[];
  requirement: Row[];
  evidence: Row[];
  request: Row[];
  incoming: Row[];
  decision: Row[];
  package: Row[];
  delivery: Row[];
  job: Row[];
  activity: Row[];
  usage: Row[];
};
export async function api<T = any>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const r = await fetch("/api" + path, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    credentials: "same-origin",
    headers: {
      "X-Dove-Action": "1",
      ...(body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
    },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r
      .json()
      .catch(() => ({ detail: "Connection interrupted. Please retry." }));
    throw new Error(
      typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail),
    );
  }
  return r.json();
}
export async function fileUrl(id: string, entry?: string) {
  const r = await api("/files/" + id + "/link");
  return r.url + (entry ? "?entry=" + encodeURIComponent(entry) : "");
}
export const label = (s: string) =>
  s.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
