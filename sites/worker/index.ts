import * as retiredAccess from "../app/api/access/route";
import * as retiredWorkspace from "../app/api/dove/[...path]/route";
import * as hostedAnalysis from "../app/api/analyze/visitor/route";

type Method = "GET" | "HEAD" | "POST" | "PUT" | "DELETE" | "PATCH" | "OPTIONS";
type Handler = (request: Request) => Response | Promise<Response>;
type Handlers = Partial<Record<Method, Handler>>;
type Environment = { ASSETS: Fetcher };
const methods: Method[] = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"];

// Preserve the existing route-module GET/HEAD/OPTIONS/405 behavior while passing
// the original Request, including its abort signal, to the unchanged handler.
async function dispatch(request: Request, handlers: Handlers) {
  const method = request.method as Method;
  if (!methods.includes(method)) return new Response(null, { status: 400 });
  if (method === "OPTIONS" && !handlers.OPTIONS) {
    const allowed = methods.filter(item => typeof handlers[item] === "function");
    if (handlers.GET && !handlers.HEAD) allowed.push("HEAD");
    allowed.push("OPTIONS");
    return new Response(null, { status: 204, headers: { Allow: allowed.sort().join(", ") } });
  }
  const handler = handlers[method] || (method === "HEAD" ? handlers.GET : undefined);
  if (!handler) return new Response(null, { status: 405 });
  const response = await handler(request);
  return method === "HEAD" ? new Response(null, { status: response.status, headers: response.headers }) : response;
}

const worker = {
  async fetch(request: Request, env: Environment) {
    const url = new URL(request.url);
    try { decodeURIComponent(url.pathname); }
    catch { return new Response(null, { status: 400 }); }
    // Assets own page canonicalization. Normalize only API paths here, keeping
    // the query and method without producing a protocol-relative Location.
    const normalized = url.pathname.replace(/\/{2,}/g, "/");
    const canonical = normalized === "/" ? "/" : normalized.replace(/\/+$/, "");
    if ((canonical === "/api" || canonical.startsWith("/api/")) && canonical !== url.pathname) {
      url.pathname = canonical;
      return new Response(null, { status: 308, headers: { Location: url.pathname + url.search } });
    }
    if (url.pathname === "/api/analyze/visitor") return dispatch(request, hostedAnalysis);
    if (url.pathname === "/api/access") return dispatch(request, retiredAccess);
    if (url.pathname.startsWith("/api/dove/")) return dispatch(request, retiredWorkspace);
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return new Response(null, { status: 404 });
    if (request.method !== "GET" && request.method !== "HEAD") return new Response(null, { status: 405 });

    // Return the asset service response unchanged: it owns HTML redirects,
    // cache policy and asset 404s in both the preview and managed hosting.
    return env.ASSETS.fetch(request);
  },
};

export default worker;
