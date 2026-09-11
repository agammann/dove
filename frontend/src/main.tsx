import React, { useState, useEffect, useCallback, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  Folder,
  FileText,
  Settings as Gear,
  ArrowRight,
  Plus,
  Search,
  Pause,
  Play,
  Check,
  Clock,
  ChevronRight,
  LogOut,
  Download,
  Mail,
  AlertCircle,
  Upload,
  ShieldCheck,
} from "lucide-react";
import { api, fileUrl, label, type Row, type Detail } from "./api";
import "./styles.css";

const Badge = ({ status }: { status: string }) => (
  <span className={"badge " + status}>{label(status)}</span>
);
const Field = ({
  label: caption,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) => (
  <label className="field">
    <span>{caption}</span>
    {children}
  </label>
);
function App() {
  const [me, setMe] = useState<any>(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState(location.pathname),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const navigate = (p: string) => {
    history.pushState({}, "", p);
    setPage(p);
    setError("");
    setNotice("");
    window.scrollTo(0, 0);
  };
  useEffect(() => {
    const fn = () => setPage(location.pathname);
    window.addEventListener("popstate", fn);
    api("/me")
      .then(setMe)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => window.removeEventListener("popstate", fn);
  }, []);
  const run = async (fn: () => Promise<any>, message = "Saved") => {
    setBusy(true);
    setError("");
    try {
      await fn();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  if (loading)
    return (
      <div className="loading" role="status">
        Opening Dove…
      </div>
    );
  const global = (
    <>
      {error && (
        <div className="notice error" role="alert">
          <AlertCircle size={18} />
          {error}
          <button onClick={() => setError("")} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
          <button
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      )}
    </>
  );
  if (!me)
    return (
      <>
        {global}
        {page.startsWith("/login") || page.startsWith("/invite") ? (
          <Login
            invite={page.startsWith("/invite")}
            run={run}
            busy={busy}
            onSuccess={async () => {
              setMe(await api("/me"));
              navigate("/work");
            }}
            navigate={navigate}
          />
        ) : (
          <Landing navigate={navigate} run={run} busy={busy} />
        )}
      </>
    );
  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <button className="wordmark" onClick={() => navigate("/work")}>
          dove
        </button>
        <nav aria-label="Main navigation">
          {[
            ["/work", "Work", Folder],
            ["/decisions", "Decisions", FileText],
            ["/settings", "Settings", Gear],
          ].map(([p, t, I]: any) => (
            <button
              key={p}
              className={page.startsWith(p) ? "active" : ""}
              onClick={() => navigate(p)}
            >
              <I size={19} />
              {t}
            </button>
          ))}
        </nav>
        <div className="workspace">
          <small>Workspace</small>
          <strong>{me.organization.name}</strong>
          {me.organization.sample && <small>Fictional sample data</small>}
          <div className="adapter">
            <span className="dot" />
            Integration status
          </div>
          <small>
            Model:{" "}
            {me.model_adapter === "fixture" ? "simulated" : me.model_adapter}
            {" · "}Email:{" "}
            {me.email_adapter === "local" ? "simulated" : me.email_adapter}
          </small>
          <button
            className="text-button"
            onClick={() =>
              run(async () => {
                await api("/auth/logout", {});
                setMe(null);
                navigate("/login");
              }, "Signed out")
            }
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>
      <main id="main">
        {global}
        {page.startsWith("/work/") ? (
          <WorkDetail
            id={page.split("/")[2]}
            run={run}
            busy={busy}
            me={me}
            navigate={navigate}
          />
        ) : page === "/decisions" ? (
          <Decisions run={run} busy={busy} navigate={navigate} />
        ) : page === "/settings" ? (
          <Settings
            me={me}
            refresh={async () => setMe(await api("/me"))}
            run={run}
            busy={busy}
          />
        ) : (
          <WorkList run={run} busy={busy} navigate={navigate} />
        )}
      </main>
    </div>
  );
}
type Shared = {
  run: (f: () => Promise<any>, m?: string) => Promise<void>;
  busy: boolean;
};
function Login({
  invite,
  run,
  busy,
  onSuccess,
  navigate,
}: Shared & {
  invite: boolean;
  onSuccess: () => Promise<void>;
  navigate: (p: string) => void;
}) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [local, setLocal] = useState(false),
    [token, setToken] = useState(location.hash.slice(1));
  useEffect(() => {
    api("/config").then((c) => setLocal(c.local));
    if (location.hash) history.replaceState({}, "", location.pathname);
  }, []);
  return (
    <div className="auth">
      <button className="wordmark" onClick={() => navigate("/")}>
        dove
      </button>
      <h1>{invite ? "Your workspace starts here." : "Welcome back."}</h1>
      <p>
        {invite
          ? "Accept your invitation to Dove."
          : "Sign in to pick up where the paperwork left off."}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () => {
            if (invite)
              await api("/auth/accept-invitation", { email, password, token });
            await api("/auth/login", { email, password });
            await onSuccess();
          }, "Workspace opened");
        }}
      >
        <Field label="Email">
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Password">
          <input
            type="password"
            autoComplete={invite ? "new-password" : "current-password"}
            minLength={12}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        {invite && (
          <Field label="Invitation token">
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
            />
          </Field>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "Opening…" : invite ? "Accept invitation" : "Sign in"}
          <ArrowRight size={17} />
        </button>
      </form>
      {local && !invite && (
        <div className="sample-login">
          <strong>Explore a fictional workspace</strong>
          <p>Local fixtures and outbox. No real email is sent.</p>
          {[
            ["Design studio", "studio"],
            ["Consulting firm", "consulting"],
            ["IT provider", "it"],
          ].map(([name, key]) => (
            <button
              key={key}
              onClick={() => {
                setEmail(key + "@dove.example");
                setPassword("Dove-local-sample-2026!");
              }}
            >
              {name}
              <ChevronRight size={16} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
function Landing({
  navigate,
  run,
  busy,
}: Shared & { navigate: (p: string) => void }) {
  const [sent, setSent] = useState(false);
  return (
    <div className="landing">
      <header>
        <span className="wordmark">dove</span>
        <button onClick={() => navigate("/login")}>
          Sign in <ArrowRight size={16} />
        </button>
      </header>
      <section className="hero">
        <h1>
          From completed work
          <br />
          to completed paperwork.
        </h1>
        <p>
          The work is done. The purchase order, approval, or final document is
          still missing. Dove helps you resolve what’s outstanding and prepare a
          billing package you can stand behind.
        </p>
        <a className="primary" href="#access">
          Request invitation access <ArrowRight size={18} />
        </a>
        <a
          className="text-button"
          href="/login"
          onClick={(e) => {
            e.preventDefault();
            navigate("/login");
          }}
        >
          Open your workspace
        </a>
      </section>
      <section className="product-story">
        <div>
          <h2>
            A clear path to
            <br />
            ready for invoicing.
          </h2>
          <p>
            Start with the documents you already have. Review the requirements,
            authorize follow-up, and approve the exact package before delivery.
          </p>
          <ol>
            <li>Upload agreements and completion documents.</li>
            <li>Inspect missing items and their source evidence.</li>
            <li>Resolve replies and decisions in one place.</li>
            <li>Review, export, and authorize delivery.</li>
          </ol>
        </div>
        <figure>
          <img
            src="/product-screenshot.png"
            alt="Dove work item with evidence-linked requirements, documents and a next action"
          />
          <figcaption>
            Actual Dove interface with fictional sample data.
          </figcaption>
        </figure>
      </section>
      <section className="access" id="access">
        <div>
          <h2>Let’s finish the paperwork.</h2>
          <p>
            Invitation beta for businesses with missing purchase orders,
            acceptance evidence, or approved deliverables.
          </p>
          <p>Access requests are reviewed manually. No payment is collected.</p>
        </div>
        {sent ? (
          <div className="success">
            <Check />
            Your request is saved. Thank you for explaining your workflow.
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/access-requests", {
                  name: f.get("name"),
                  email: f.get("email"),
                  business: f.get("business"),
                  problem: f.get("problem"),
                  consent: f.get("consent") === "on",
                  website: "",
                });
                setSent(true);
              }, "Access request saved");
            }}
          >
            <Field label="Your name">
              <input name="name" required maxLength={100} />
            </Field>
            <Field label="Work email">
              <input name="email" type="email" required />
            </Field>
            <Field label="Business">
              <input name="business" required maxLength={200} />
            </Field>
            <Field label="What holds up your invoicing?">
              <textarea
                name="problem"
                required
                minLength={10}
                maxLength={2000}
              />
            </Field>
            <label className="check">
              <input type="checkbox" name="consent" required />I agree that Dove
              may use these details to review and respond to my access request.
            </label>
            <button className="primary" disabled={busy}>
              Request access <ArrowRight size={16} />
            </button>
            <small>
              Your request is stored in Dove. It is not sent to the document
              analysis model.
            </small>
          </form>
        )}
      </section>
      <footer>
        <span className="wordmark">dove</span>
        <span>Human review. Explicit permission. A record of every step.</span>
      </footer>
    </div>
  );
}
function WorkList({
  run,
  busy,
  navigate,
}: Shared & { navigate: (p: string) => void }) {
  const [items, setItems] = useState<Row[]>([]),
    [contacts, setContacts] = useState<Row[]>([]),
    [loaded, setLoaded] = useState(false),
    [create, setCreate] = useState(false),
    [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all");
  const reload = useCallback(async () => {
    const [a, b] = await Promise.all([
      api<Row[]>("/work"),
      api<Row[]>("/contacts"),
    ]);
    setItems(a);
    setContacts(b);
    setLoaded(true);
  }, []);
  useEffect(() => {
    run(reload, "");
  }, [reload]);
  const shown = items.filter(
    (i) =>
      (i.title + " " + i.customer)
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === "all" || i.status === filter),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="breadcrumb">Workspace / Work</div>
          <h1>Work, ready to move forward.</h1>
          <p>See what’s missing. Know what happens next.</p>
        </div>
        <button className="primary" onClick={() => setCreate(!create)}>
          <Plus size={18} />
          Create work item
        </button>
      </div>
      {create && (
        <section className="panel">
          <h2>Start with completed work</h2>
          {!contacts.length ? (
            <p>Add a customer and authorized contact in Settings first.</p>
          ) : (
            <form
              className="form-grid"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                run(async () => {
                  const w = await api("/work", {
                    title: f.get("title"),
                    description: f.get("description"),
                    contact_id: f.get("contact_id"),
                    currency: f.get("currency"),
                  });
                  navigate("/work/" + w.id);
                }, "Work item created");
              }}
            >
              <Field label="Work item title">
                <input name="title" required maxLength={200} />
              </Field>
              <Field label="Customer contact">
                <select name="contact_id">
                  {contacts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.customer} · {c.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Short work description">
                <textarea name="description" required maxLength={2000} />
              </Field>
              <Field label="Currency">
                <select name="currency">
                  {["USD", "EUR", "GBP", "CAD", "AUD"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </Field>
              <button className="primary" disabled={busy}>
                Create and upload documents
              </button>
            </form>
          )}
        </section>
      )}
      <div className="toolbar">
        <label className="search">
          <Search size={18} />
          <input
            aria-label="Search work"
            placeholder="Search work or customer"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <select
          aria-label="Filter work status"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          {[...new Set(items.map((i) => i.status))].map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
        <span>{shown.length} work items</span>
      </div>
      <div className="work-table">
        <div className="table-heading">
          <span>Work item / customer</span>
          <span>Status</span>
          <span>Current blocker</span>
          <span />
        </div>
        {!loaded ? (
          <p className="empty" role="status">
            Loading your work…
          </p>
        ) : shown.length ? (
          shown.map((i) => (
            <button
              className="work-row"
              key={i.id}
              onClick={() => navigate("/work/" + i.id)}
            >
              <span>
                <strong>{i.title}</strong>
                <small>{i.customer}</small>
              </span>
              <span>
                <Badge status={i.status} />
              </span>
              <span className="muted">{i.blocker}</span>
              <ChevronRight size={18} />
            </button>
          ))
        ) : (
          <div className="empty">
            <Folder size={30} />
            <h2>
              {query
                ? "No work matches your search."
                : "A fresh place for finished work."}
            </h2>
            <p>
              {query
                ? "Try another customer or title."
                : "Create a work item and upload an agreement to begin."}
            </p>
          </div>
        )}
      </div>
      <div className="footnote">
        <ShieldCheck size={17} /> Nothing is sent until the required permissions
        and approvals are recorded.
      </div>
    </>
  );
}
function Evidence({ e, docs }: { e: Row; docs: Row[] }) {
  const d = docs.find((d) => d.id === e.document_id);
  return (
    <blockquote>
      <p>“{e.excerpt}”</p>
      <footer>
        {d ? (
          <button
            className="text-button"
            onClick={async () =>
              window.open(await fileUrl(d.id), "_blank", "noopener")
            }
          >
            {d.filename} · v{e.version} · page {e.page}
            {e.line ? " · line " + e.line : ""}
          </button>
        ) : (
          <span>
            Incoming reply · {e.sender} · {e.sender_authentication}
          </span>
        )}
        <span>{e.review_status}</span>
      </footer>
    </blockquote>
  );
}
function WorkDetail({
  id,
  run,
  busy,
  me,
  navigate,
}: Shared & { id: string; me: any; navigate: (p: string) => void }) {
  const [d, setD] = useState<Detail | null>(null),
    [tab, setTab] = useState("Review"),
    [contacts, setContacts] = useState<Row[]>([]),
    [newReq, setNewReq] = useState(false),
    [requestBody, setRequestBody] = useState(""),
    [deleteOpen, setDeleteOpen] = useState(false);
  const refresh = useCallback(async () => {
    const [a, b] = await Promise.all([
      api<Detail>("/work/" + id),
      api<Row[]>("/contacts"),
    ]);
    setD(a);
    setContacts(b);
  }, [id]);
  useEffect(() => {
    run(refresh, "");
    const timer = setInterval(() => refresh().catch(() => {}), 4000);
    return () => clearInterval(timer);
  }, [refresh]);
  const act = (fn: () => Promise<any>, msg = "Saved") =>
    run(async () => {
      await fn();
      await refresh();
    }, msg);
  if (!d) return <div className="loading">Loading work item…</div>;
  const work = d.work,
    missing = d.requirement.filter(
      (r) =>
        r.status === "missing" &&
        !d.request.some(
          (req) => !req.stopped && req.requirement_ids.includes(r.id),
        ),
    ),
    waiting = d.request.some((req) => !req.stopped),
    needsReview = d.requirement.some((r) =>
      ["received", "needs_review"].includes(r.status),
    ),
    openDecisions = d.decision.filter((x) => x.status === "open");
  return (
    <>
      <div className="breadcrumb">
        <button onClick={() => navigate("/work")}>Work</button> / {work.title}
      </div>
      <div className="page-heading detail-heading">
        <div>
          <h1>{work.title}</h1>
          <div className="meta">
            <span>
              <small>Customer</small>
              <strong>{work.customer}</strong>
            </span>
            <span>
              <small>Status</small>
              <Badge status={work.status} />
            </span>
          </div>
        </div>
        <button
          onClick={() =>
            act(
              () => api("/work/" + id + "/pause", {}),
              work.paused ? "Automation resumed" : "Automation paused",
            )
          }
        >
          {work.paused ? <Play size={16} /> : <Pause size={16} />}{" "}
          {work.paused ? "Resume automation" : "Pause automation"}
        </button>
      </div>
      <div className="steps" role="tablist">
        {["Documents", "Review", "Resolve", "Package"].map((t, i) => (
          <button
            role="tab"
            aria-selected={tab === t}
            key={t}
            className={tab === t ? "current" : ""}
            onClick={() => setTab(t)}
          >
            <span>
              {i === 0 && d.document.length ? <Check size={16} /> : i + 1}
            </span>
            {t}
          </button>
        ))}
      </div>
      <div className="detail-grid">
        <div>
          {tab === "Documents" ? (
            <section className="panel">
              <h2>Documents</h2>
              <p>
                Text-based PDF or UTF-8 TXT · up to 8 MB, 50 pages. A changed
                version triggers review.
              </p>
              <form
                className="upload-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget;
                  act(async () => {
                    await api("/work/" + id + "/documents", new FormData(form));
                    form.reset();
                  }, "Document saved. Analysis runs in the background.");
                }}
              >
                <Upload size={28} />
                <Field label="Choose a document">
                  <input type="file" name="file" accept=".pdf,.txt" required />
                </Field>
                <Field label="Document purpose">
                  <select name="role">
                    <option value="internal">Internal evidence only</option>
                    <option value="support">
                      Customer-facing supporting document
                    </option>
                    <option value="invoice">Existing invoice PDF</option>
                  </select>
                </Field>
                <button className="primary" disabled={busy}>
                  Upload and analyze
                </button>
              </form>
              {d.document.map((doc) => (
                <div className="document-row" key={doc.id}>
                  <FileText size={18} />
                  <div>
                    <strong>{doc.filename}</strong>
                    <small>
                      Version {doc.version} ·{" "}
                      {doc.current ? "Current" : "Superseded"} · {doc.role}
                    </small>
                  </div>
                  <button
                    onClick={() =>
                      act(async () => {
                        window.open(
                          await fileUrl(doc.id),
                          "_blank",
                          "noopener",
                        );
                      }, "")
                    }
                  >
                    Preview
                  </button>
                  {doc.current &&
                    doc.role === "support" &&
                    !doc.approved_support && (
                      <button
                        onClick={() =>
                          act(
                            () =>
                              api(
                                "/documents/" + doc.id + "/approve-support",
                                {},
                              ),
                            "Document approved for customer delivery",
                          )
                        }
                      >
                        Approve for delivery
                      </button>
                    )}
                </div>
              ))}
            </section>
          ) : tab === "Review" ? (
            <section className="panel checklist">
              <div className="section-title">
                <div>
                  <h2>Requirement checklist</h2>
                  <p>Verify each requirement against its source evidence.</p>
                </div>
                <button
                  className="icon-button"
                  aria-label="Add requirement"
                  onClick={() => setNewReq(!newReq)}
                >
                  <Plus size={19} />
                </button>
              </div>
              {d.requirement.length ? (
                d.requirement.map((r) => (
                  <Requirement key={r.id} r={r} d={d} act={act} busy={busy} />
                ))
              ) : (
                <div className="empty">
                  Upload a document to propose your first requirements.
                </div>
              )}
              {newReq && (
                <form
                  className="inline-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    act(async () => {
                      await api("/work/" + id + "/requirements", {
                        title: f.get("title"),
                        category: "custom",
                        status: "missing",
                        reason: f.get("reason"),
                        evidence_ids: [],
                      });
                      setNewReq(false);
                    });
                  }}
                >
                  <Field label="Requirement">
                    <input name="title" required />
                  </Field>
                  <Field label="Why is this required?">
                    <textarea name="reason" required />
                  </Field>
                  <button disabled={busy}>Add missing requirement</button>
                </form>
              )}
            </section>
          ) : tab === "Resolve" ? (
            <>
              <section className="panel">
                <h2>Decisions</h2>
                <p>
                  Resolve ambiguity explicitly. Internal decisions do not
                  establish customer acceptance.
                </p>
                {openDecisions.length ? (
                  openDecisions.map((x) => (
                    <Decision
                      key={x.id}
                      decision={x}
                      d={d}
                      act={act}
                      busy={busy}
                    />
                  ))
                ) : (
                  <div className="empty">No open decisions.</div>
                )}
              </section>
              <section className="panel">
                <h2>Requests & replies</h2>
                {d.request.length ? (
                  d.request.map((r) => (
                    <div className="request" key={r.id}>
                      <div className="section-title">
                        <strong>To {r.recipient}</strong>
                        <Badge status={r.status} />
                      </div>
                      <pre>{r.body}</pre>
                      <small>
                        {r.reminders_sent} reminders sent ·{" "}
                        {r.stopped
                          ? "Reminders stopped"
                          : "Follow-up permission recorded"}
                      </small>
                      {!r.stopped && (
                        <button
                          onClick={() =>
                            act(
                              () => api("/requests/" + r.id + "/stop", {}),
                              "Reminders stopped",
                            )
                          }
                        >
                          Stop reminders
                        </button>
                      )}
                      {d.incoming
                        .filter((m) => m.request_id === r.id)
                        .map((m) => (
                          <blockquote key={m.id}>
                            <strong>{m.sender}</strong>
                            <p>{m.text || "Retrieving message content…"}</p>
                            <small>
                              {m.simulated ? "Local inbox fixture · " : ""}
                              {m.classification || "Requires human review"}
                            </small>
                            {m.attachments?.map((a: any) => (
                              <p key={a.id}>
                                {a.filename} · {a.size} bytes ·{" "}
                                <button
                                  onClick={() =>
                                    act(
                                      () =>
                                        api(
                                          "/incoming/" +
                                            m.id +
                                            "/attachments/" +
                                            a.id,
                                          {},
                                        ),
                                      "Attachment retrieved for review",
                                    )
                                  }
                                >
                                  Retrieve attachment
                                </button>
                              </p>
                            ))}
                          </blockquote>
                        ))}
                      {me.local && me.email_adapter === "local" && (
                        <LocalInbox request={r} act={act} busy={busy} />
                      )}
                    </div>
                  ))
                ) : (
                  <div className="empty">
                    No requests. Complete input does not need outreach.
                  </div>
                )}
              </section>
            </>
          ) : (
            <PackagePanel d={d} contacts={contacts} act={act} busy={busy} />
          )}
          <section className="panel history">
            <h2>Activity</h2>
            {[...d.activity].reverse().map((a) => (
              <div className="activity" key={a.id}>
                <span className="dot" />
                <div>
                  <small>
                    {new Date(a.created * 1000).toLocaleString()} · {a.actor}
                  </small>
                  <p>{a.message}</p>
                </div>
              </div>
            ))}
          </section>
        </div>
        <aside className="detail-aside">
          <section className="panel next-action">
            <small>Next action</small>
            <h2>{work.blocker}</h2>
            {work.paused && (
              <p className="warning">
                Automation is paused. An already accepted message cannot be
                recalled.
              </p>
            )}
            {!work.confirmed ? (
              <>
                <p>Review the evidence before authorizing outreach.</p>
                <button
                  className="primary"
                  disabled={busy || !d.requirement.length}
                  onClick={() =>
                    act(
                      () => api("/work/" + id + "/confirm", {}),
                      "Checklist confirmed",
                    )
                  }
                >
                  Confirm checklist
                </button>
              </>
            ) : missing.length ? (
              <>
                <p>
                  {missing.length} missing{" "}
                  {missing.length === 1 ? "item" : "items"}. Choose a contact
                  and authorize this request.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    act(
                      () =>
                        api("/work/" + id + "/requests", {
                          requirement_ids: missing.map((r) => r.id),
                          contact_id: f.get("contact"),
                          follow_up_permission: f.get("permission") === "on",
                          body: requestBody || null,
                        }),
                      "Request queued",
                    );
                  }}
                >
                  <Field label="Authorized contact">
                    <select name="contact">
                      {contacts
                        .filter(
                          (c) =>
                            c.customer_id === work.customer_id && c.authorized,
                        )
                        .map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} · {c.email}
                          </option>
                        ))}
                    </select>
                  </Field>
                  <label className="check">
                    <input type="checkbox" name="permission" required />
                    Authorize this missing-item request and up to{" "}
                    {me.organization.reminder_limit ?? 2} reminders.
                  </label>
                  <Field label="Request message (optional)">
                    <textarea
                      value={requestBody}
                      onChange={(e) => setRequestBody(e.target.value)}
                      maxLength={3000}
                      placeholder="Leave blank for the standard missing-item request."
                    />
                  </Field>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      act(async () => {
                        const result = await api(
                          "/work/" + id + "/request-draft",
                          {},
                        );
                        setRequestBody(result.body);
                      }, "Draft ready for your review")
                    }
                  >
                    Draft request
                  </button>
                  <button className="primary" disabled={busy}>
                    Authorize request <Mail size={16} />
                  </button>
                </form>
              </>
            ) : waiting ? (
              <>
                <p>
                  An authorized request is active. Dove will resume this item
                  when a reply arrives.
                </p>
                <button className="primary" onClick={() => setTab("Resolve")}>
                  View request and replies
                </button>
              </>
            ) : (
              <>
                <p>
                  {openDecisions.length
                    ? "Review the questions and source evidence."
                    : work.status === "sent"
                      ? "Review the approved package and delivery history. Provider acceptance does not establish payment or customer acceptance."
                      : "Inspect received evidence, then assemble the exact invoice and supporting documents."}
                </p>
                <button
                  className="primary"
                  onClick={() =>
                    setTab(
                      openDecisions.length
                        ? "Resolve"
                        : needsReview
                          ? "Review"
                          : "Package",
                    )
                  }
                >
                  {openDecisions.length
                    ? "Review decisions"
                    : needsReview
                      ? "Review received evidence"
                      : "Open billing package"}
                  <ArrowRight size={16} />
                </button>
              </>
            )}
          </section>
          <section className="panel">
            <h3>Documents</h3>
            {d.document
              .filter((x) => x.current)
              .map((doc) => (
                <button
                  className="file-link"
                  key={doc.id}
                  onClick={() =>
                    act(async () => {
                      window.open(await fileUrl(doc.id), "_blank", "noopener");
                    }, "")
                  }
                >
                  <FileText size={18} />
                  <span>
                    {doc.filename}
                    <small>Version {doc.version}</small>
                  </span>
                  <ChevronRight size={16} />
                </button>
              ))}
            <button className="text-button" onClick={() => setTab("Documents")}>
              <Plus size={16} />
              Add a document
            </button>
          </section>
          <section className="panel">
            <h3>Delivery history</h3>
            {d.delivery.length ? (
              d.delivery.map((a) => (
                <div className="delivery" key={a.id}>
                  <Badge status={a.status} />
                  <small>
                    {a.simulated ? "SIMULATED · " : ""}
                    {a.type}
                  </small>
                  <p>{a.recipient.join(", ")}</p>
                  {a.provider_id && <small>Provider ID: {a.provider_id}</small>}
                  {a.error && <p className="warning">{a.error}</p>}
                  {a.status === "uncertain" && (
                    <button
                      onClick={() =>
                        act(
                          () => api("/deliveries/" + a.id + "/reconcile", {}),
                          "Provider status checked",
                        )
                      }
                    >
                      Reconcile status
                    </button>
                  )}
                  {a.status === "failed" && !a.provider_id && (
                    <button
                      onClick={() =>
                        act(
                          () => api("/deliveries/" + a.id + "/retry", {}),
                          "Retry queued",
                        )
                      }
                    >
                      Retry rejected send
                    </button>
                  )}
                </div>
              ))
            ) : (
              <p className="muted">No delivery attempts.</p>
            )}
            <small>
              Provider acceptance ≠ confirmed delivery, customer acceptance, or
              payment.
            </small>
          </section>
          {d.job.some((j) => j.error) && (
            <section className="panel">
              <h3>Processing needs attention</h3>
              {d.job
                .filter((j) => j.error)
                .map((j) => (
                  <div key={j.id}>
                    <p>{j.error}</p>
                    <Badge status={j.status} />
                    {j.status === "failed" && j.type !== "send" && (
                      <button
                        onClick={() =>
                          act(
                            () => api("/jobs/" + j.id + "/retry", {}),
                            "Retry queued",
                          )
                        }
                      >
                        Retry processing
                      </button>
                    )}
                  </div>
                ))}
            </section>
          )}
          <button
            className="text-button danger"
            onClick={() => setDeleteOpen(!deleteOpen)}
          >
            Delete work item
          </button>
          {deleteOpen && (
            <div className="panel">
              <p>
                Delete this work item, its files, history, pending jobs and
                reminders? This cannot be undone.
              </p>
              <button
                className="danger"
                onClick={() =>
                  run(async () => {
                    await api("/work/" + id, undefined, "DELETE");
                    navigate("/work");
                  }, "Work item deleted")
                }
              >
                Permanently delete this work item
              </button>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
type Act = (fn: () => Promise<any>, msg?: string) => Promise<void>;
function Requirement({
  r,
  d,
  act,
  busy,
}: {
  r: Row;
  d: Detail;
  act: Act;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false),
    [status, setStatus] = useState(r.status),
    [reason, setReason] = useState("");
  useEffect(() => setStatus(r.status), [r.status]);
  return (
    <div className="requirement">
      <details open>
        <summary>
          <span className={"status-icon " + r.status}>
            {["satisfied", "waived"].includes(r.status) ? (
              <Check size={14} />
            ) : r.status === "missing" ? (
              <AlertCircle size={15} />
            ) : (
              <Clock size={14} />
            )}
          </span>
          <strong>{r.title}</strong>
          <Badge status={r.status} />
        </summary>
        {r.evidence_ids?.map((id: string) => {
          const ev = d.evidence.find((e) => e.id === id);
          return ev ? <Evidence key={id} e={ev} docs={d.document} /> : null;
        })}
        <div className="review-footer">
          <small>
            {r.reviewed_by
              ? "Reviewed by " + r.reviewed_by
              : "Received information is not yet verified."}
          </small>
          <button className="text-button" onClick={() => setEditing(!editing)}>
            {editing ? "Close review" : "Review / correct"}
          </button>
        </div>
        {editing && (
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              act(async () => {
                await api(
                  "/requirements/" + r.id,
                  {
                    title: f.get("title"),
                    category: r.category,
                    status,
                    reason,
                    evidence_ids: f.getAll("evidence"),
                  },
                  "PUT",
                );
                setEditing(false);
              }, "Requirement review saved");
            }}
          >
            <Field label="Requirement title">
              <input name="title" defaultValue={r.title} required />
            </Field>
            <Field label="Review outcome">
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {[
                  "missing",
                  "received",
                  "needs_review",
                  "satisfied",
                  "waived",
                ].map((x) => (
                  <option key={x} value={x}>
                    {label(x)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Review explanation">
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                placeholder="What did you verify or correct? Waivers are internal authorization."
              />
            </Field>
            <fieldset>
              <legend>Evidence supporting this review</legend>
              {d.evidence
                .filter(
                  (e) =>
                    !e.document_id ||
                    d.document.some(
                      (doc) => doc.id === e.document_id && doc.current,
                    ),
                )
                .map((e) => (
                  <label className="check" key={e.id}>
                    <input
                      type="checkbox"
                      name="evidence"
                      value={e.id}
                      defaultChecked={r.evidence_ids?.includes(e.id)}
                    />
                    {e.excerpt.slice(0, 140)}
                  </label>
                ))}
            </fieldset>
            <button className="primary" disabled={busy}>
              Save review
            </button>
          </form>
        )}
      </details>
    </div>
  );
}
function Decision({
  decision: x,
  d,
  act,
  busy,
}: {
  decision: Row;
  d?: Detail;
  act: Act;
  busy: boolean;
}) {
  return (
    <form
      className="decision"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        act(
          () =>
            api("/decisions/" + x.id + "/resolve", {
              action: f.get("action"),
              explanation: f.get("explanation"),
            }),
          "Decision recorded",
        );
      }}
    >
      <h3>{x.question}</h3>
      <p>{x.why}</p>
      <p>{x.consequence}</p>
      {d &&
        x.evidence_ids?.map((id: string) => {
          const ev = d.evidence.find((e) => e.id === id);
          return ev ? <Evidence key={id} e={ev} docs={d.document} /> : null;
        })}
      <Field label="Decision">
        <select name="action">
          <option value="approve">Approve evidence for further review</option>
          <option value="reject">Reject proposed evidence</option>
          <option value="correct">Record a correction</option>
          <option value="waive">Record an internal waiver</option>
        </select>
      </Field>
      <Field label="Explanation and consequences">
        <textarea name="explanation" minLength={5} required />
      </Field>
      <button disabled={busy}>Record decision</button>
    </form>
  );
}
function LocalInbox({
  request: r,
  act,
  busy,
}: {
  request: Row;
  act: Act;
  busy: boolean;
}) {
  return (
    <details className="local-inbox">
      <summary>Local inbox · simulate a reply</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          act(
            () =>
              api("/local/inbox", {
                request_id: r.id,
                event_id: crypto.randomUUID(),
                sender: f.get("sender"),
                text: f.get("text"),
                out_of_office: f.get("ooo") === "on",
                forwarded: f.get("forwarded") === "on",
              }),
            "Local reply saved; worker will resume the workflow",
          );
        }}
      >
        <p>
          Uses the durable incoming-message path. No external email is involved.
        </p>
        <Field label="Reply sender">
          <input
            name="sender"
            type="email"
            defaultValue={r.recipient}
            required
          />
        </Field>
        <Field label="Reply text">
          <textarea
            name="text"
            defaultValue="The purchase order is PO-ALDER-1042. Please include it with the invoice."
            required
          />
        </Field>
        <label className="check">
          <input name="ooo" type="checkbox" />
          Out of office
        </label>
        <label className="check">
          <input name="forwarded" type="checkbox" />
          Forwarded message
        </label>
        <button disabled={busy}>Submit local reply</button>
      </form>
    </details>
  );
}
function PackagePanel({
  d,
  contacts,
  act,
  busy,
}: {
  d: Detail;
  contacts: Row[];
  act: Act;
  busy: boolean;
}) {
  const [mode, setMode] = useState("generated"),
    [preview, setPreview] = useState(""),
    [build, setBuild] = useState(false),
    [lineCount, setLineCount] = useState(1),
    [previewPage, setPreviewPage] = useState(0),
    [previewPages, setPreviewPages] = useState(1);
  const p = d.package.at(-1);
  const evidence = d.evidence.filter(
    (e) =>
      e.review_status === "reviewed" &&
      d.requirement.some(
        (r) =>
          r.category === "amount" &&
          r.status === "satisfied" &&
          r.evidence_ids.includes(e.id),
      ),
  );
  return (
    <section className="panel package">
      <div className="section-title">
        <div>
          <h2>Billing package</h2>
          <p>Exact contents. Explicit approval. Authorized delivery.</p>
        </div>
        <button onClick={() => setBuild(!build)}>
          <Plus size={16} />
          {p ? "New version" : "Assemble package"}
        </button>
      </div>
      {(!p || build) && (
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            act(async () => {
              await api("/work/" + d.work.id + "/packages", {
                mode,
                contact_ids: f.getAll("contact"),
                document_ids: f.getAll("document"),
                invoice_document_id:
                  mode === "existing" ? f.get("invoice") : null,
                line_items:
                  mode === "generated"
                    ? Array.from({ length: lineCount }, (_, i) => ({
                        description: f.get("description-" + i),
                        quantity: f.get("quantity-" + i),
                        unit_price: f.get("unit_price-" + i),
                        evidence_id: f.get("evidence-" + i),
                      }))
                    : [],
                confirmed_total: f.get("total"),
                tax: f.get("tax") || "0",
                discount: f.get("discount") || "0",
                issue_date: f.get("issue"),
                due_date: f.get("due"),
                summary: f.get("summary"),
                details_confirmed: f.get("confirmed") === "on",
              });
              setBuild(false);
            }, "Immutable package version assembled");
          }}
        >
          <Field label="Invoice source">
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="generated">
                Generate from confirmed line items
              </option>
              <option value="existing">Attach existing invoice PDF</option>
            </select>
          </Field>
          {mode === "existing" ? (
            <Field label="Existing invoice">
              <select name="invoice" required>
                {d.document
                  .filter((x) => x.current && x.filename.endsWith(".pdf"))
                  .map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.filename}
                    </option>
                  ))}
              </select>
            </Field>
          ) : (
            <>
              {Array.from({ length: lineCount }, (_, i) => (
                <React.Fragment key={i}>
                  <Field
                    label={
                      lineCount > 1
                        ? "Line " + (i + 1) + " description"
                        : "Line item description"
                    }
                  >
                    <input
                      name={"description-" + i}
                      defaultValue={i === 0 ? d.work.title : ""}
                      required
                    />
                  </Field>
                  <Field label="Quantity">
                    <input
                      name={"quantity-" + i}
                      defaultValue="1"
                      inputMode="decimal"
                      required
                    />
                  </Field>
                  <Field label="Unit price">
                    <input
                      name={"unit_price-" + i}
                      placeholder="2400.00"
                      inputMode="decimal"
                      required
                    />
                  </Field>
                  <Field label="Reviewed charge evidence">
                    <select name={"evidence-" + i} required>
                      <option value="">Choose supporting evidence</option>
                      {evidence.map((e) => (
                        <option key={e.id} value={e.id}>
                          {e.excerpt.slice(0, 100)}
                        </option>
                      ))}
                    </select>
                  </Field>
                </React.Fragment>
              ))}
              <div className="actions wide">
                <button
                  type="button"
                  disabled={lineCount >= 30}
                  onClick={() => setLineCount(lineCount + 1)}
                >
                  Add line item
                </button>
                {lineCount > 1 && (
                  <button
                    type="button"
                    onClick={() => setLineCount(lineCount - 1)}
                  >
                    Remove last line
                  </button>
                )}
              </div>
              <Field label="Entered tax amount">
                <input name="tax" defaultValue="0.00" inputMode="decimal" />
              </Field>
              <Field label="Discount amount">
                <input
                  name="discount"
                  defaultValue="0.00"
                  inputMode="decimal"
                />
              </Field>
            </>
          )}
          <Field label={"Confirmed total · " + d.work.currency}>
            <input
              name="total"
              placeholder="2400.00"
              inputMode="decimal"
              required
            />
          </Field>
          <Field label="Invoice issue date">
            <input name="issue" type="date" required />
          </Field>
          <Field label="Due date">
            <input name="due" type="date" required />
          </Field>
          <Field label="Customer-facing completion summary">
            <textarea name="summary" required maxLength={2000} />
          </Field>
          <fieldset>
            <legend>Exact recipients</legend>
            {contacts
              .filter(
                (c) => c.customer_id === d.work.customer_id && c.authorized,
              )
              .map((c) => (
                <label className="check" key={c.id}>
                  <input type="checkbox" name="contact" value={c.id} />
                  {c.name} · {c.email}
                </label>
              ))}
          </fieldset>
          <fieldset>
            <legend>Approved supporting documents</legend>
            {d.document
              .filter((x) => x.current && x.approved_support)
              .map((x) => (
                <label className="check" key={x.id}>
                  <input type="checkbox" name="document" value={x.id} />
                  {x.filename} · v{x.version}
                </label>
              ))}
            <small>
              Internal evidence is excluded. Approve customer-facing documents
              in Documents.
            </small>
          </fieldset>
          <label className="check wide">
            <input type="checkbox" name="confirmed" required />I confirm the
            customer and business details, dates, currency, charges, entered
            taxes and discounts. Dove does not determine tax obligations.
          </label>
          <button className="primary" disabled={busy}>
            Build exact package preview
          </button>
        </form>
      )}
      {p && (
        <>
          <div className="package-summary">
            <Badge status={p.approval ? "approved" : "ready_for_approval"} />
            <h3>
              Version {p.version} · {p.manifest.invoice_number}
            </h3>
            <strong className="amount">
              {p.manifest.currency} {p.manifest.total}
            </strong>
            <p>To: {p.manifest.recipients.join(", ")}</p>
            <p>
              Issue {p.manifest.issue_date} · Due {p.manifest.due_date}
            </p>
            <p>{p.manifest.summary}</p>
            <small className="digest">Package SHA-256: {p.digest}</small>
            {p.invalidation && (
              <p className="warning">Approval invalidated: {p.invalidation}</p>
            )}
          </div>
          <div className="actions">
            <button
              onClick={() =>
                act(async () => {
                  const response = await fetch(
                    "/api/packages/" + p.id + "/preview-page?page=0",
                  );
                  if (!response.ok)
                    throw new Error((await response.json()).detail);
                  setPreviewPages(
                    Number(response.headers.get("X-PDF-Pages") || 1),
                  );
                  setPreviewPage(0);
                  setPreview("/api/packages/" + p.id + "/preview-page?page=0");
                }, "")
              }
            >
              <FileText size={16} />
              Preview exact invoice
            </button>
            <button
              onClick={() =>
                act(async () => {
                  window.open(await fileUrl(p.id), "_blank", "noopener");
                }, "")
              }
            >
              <Download size={16} />
              Download ZIP
            </button>
            <button
              onClick={() =>
                act(async () => {
                  setPreview(await fileUrl(p.id, "manifest.json"));
                }, "")
              }
            >
              View manifest
            </button>
          </div>
          {preview &&
            (preview.includes("preview-page") ? (
              <div className="invoice-preview">
                <div className="actions">
                  <button
                    disabled={previewPage === 0}
                    onClick={() => {
                      setPreviewPage(previewPage - 1);
                      setPreview(
                        "/api/packages/" +
                          p.id +
                          "/preview-page?page=" +
                          (previewPage - 1),
                      );
                    }}
                  >
                    Previous page
                  </button>
                  <span>
                    Page {previewPage + 1} of {previewPages}
                  </span>
                  <button
                    disabled={previewPage + 1 >= previewPages}
                    onClick={() => {
                      setPreviewPage(previewPage + 1);
                      setPreview(
                        "/api/packages/" +
                          p.id +
                          "/preview-page?page=" +
                          (previewPage + 1),
                      );
                    }}
                  >
                    Next page
                  </button>
                </div>
                <img
                  src={preview}
                  alt={"Exact invoice rendering, page " + (previewPage + 1)}
                />
              </div>
            ) : (
              <iframe title="Exact billing package preview" src={preview} />
            ))}
          <h3>Customer-facing attachments</h3>
          <ul>
            <li>
              invoice.pdf —{" "}
              {p.manifest.invoice_mode === "existing"
                ? "original PDF bytes preserved"
                : "generated from confirmed charges"}
            </li>
            <li>completion-summary.txt</li>
            <li>manifest.json</li>
            {p.manifest.documents.map((x: any) => (
              <li key={x.id}>
                {x.filename} · v{x.version}
              </li>
            ))}
          </ul>
          <div className="approval-box">
            <ShieldCheck size={22} />
            <div>
              <strong>
                {p.approval
                  ? "Package approval recorded."
                  : "Review every attachment and recipient."}
              </strong>
              <p>
                {p.approval
                  ? "Delivery requires a separate explicit authorization."
                  : "Approval binds to this exact package version and digest. Any change requires a new review."}
              </p>
              {!p.approval ? (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    act(
                      () =>
                        api("/packages/" + p.id + "/approve", {
                          digest: p.digest,
                          authorize: true,
                        }),
                      "Exact package approved",
                    )
                  }
                >
                  Approve this exact package
                </button>
              ) : (
                <button
                  className="primary"
                  disabled={busy || p.delivered}
                  onClick={() =>
                    act(
                      () =>
                        api("/packages/" + p.id + "/deliver", {
                          digest: p.digest,
                          authorize: true,
                        }),
                      "Delivery authorized and queued",
                    )
                  }
                >
                  {p.delivered
                    ? "Provider accepted package"
                    : "Authorize delivery to listed recipients"}
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
function Decisions({
  run,
  busy,
  navigate,
}: Shared & { navigate: (p: string) => void }) {
  const [items, setItems] = useState<Row[]>([]);
  const refresh = useCallback(
    async () => setItems(await api("/decisions")),
    [],
  );
  useEffect(() => {
    run(refresh, "");
  }, [refresh]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="breadcrumb">Workspace / Decisions</div>
          <h1>A little judgment moves work forward.</h1>
          <p>Open questions with a clear consequence.</p>
        </div>
      </div>
      {items.filter((x) => x.status === "open").length ? (
        items
          .filter((x) => x.status === "open")
          .map((x) => (
            <section className="panel" key={x.id}>
              <h2>{x.question}</h2>
              <p>{x.consequence}</p>
              <button
                className="primary"
                onClick={() => navigate("/work/" + x.work_id)}
              >
                Open work item and evidence <ArrowRight size={16} />
              </button>
            </section>
          ))
      ) : (
        <div className="empty">
          <Check size={30} />
          <h2>No open decisions.</h2>
          <p>Questions appear here when evidence needs your attention.</p>
        </div>
      )}
    </>
  );
}
function Settings({
  me,
  refresh,
  run,
  busy,
}: Shared & { me: any; refresh: () => Promise<void> }) {
  const [contacts, setContacts] = useState<Row[]>([]),
    [deletion, setDeletion] = useState("");
  const o = me.organization;
  const reload = useCallback(
    async () => setContacts(await api("/contacts")),
    [],
  );
  useEffect(() => {
    run(reload, "");
  }, [reload]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="breadcrumb">Workspace / Settings</div>
          <h1>A few details. Clear permissions.</h1>
          <p>Billing information, contacts, and automation controls.</p>
        </div>
      </div>
      <section className="panel">
        <h2>Business & automation</h2>
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api(
                "/settings",
                {
                  business_name: f.get("business_name"),
                  billing_details: f.get("billing_details"),
                  timezone: f.get("timezone"),
                  reminder_limit: Number(f.get("limit")),
                  reminder_business_days: Number(f.get("days")),
                  automation_paused: f.get("pause") === "on",
                },
                "PUT",
              );
              await refresh();
            }, "Settings saved");
          }}
        >
          <Field label="Business billing name">
            <input
              name="business_name"
              defaultValue={o.business_name}
              required
            />
          </Field>
          <Field label="Business billing details">
            <textarea
              name="billing_details"
              defaultValue={o.billing_details}
              required
            />
          </Field>
          <Field label="Timezone">
            <input
              name="timezone"
              defaultValue={o.timezone || "UTC"}
              required
            />
          </Field>
          <Field label="Maximum automated reminders">
            <input
              name="limit"
              type="number"
              min={0}
              max={2}
              defaultValue={o.reminder_limit ?? 2}
            />
          </Field>
          <Field label="Business days between reminders">
            <input
              name="days"
              type="number"
              min={2}
              max={30}
              defaultValue={o.reminder_business_days ?? 2}
            />
          </Field>
          <label className="check">
            <input
              type="checkbox"
              name="pause"
              defaultChecked={o.automation_paused}
            />
            Pause all workspace automation
          </label>
          <button className="primary" disabled={busy}>
            Save settings
          </button>
        </form>
      </section>
      <section className="panel">
        <h2>Authorized customer contacts</h2>
        <p>
          Authorization to receive requests and packages is separate from
          customer acceptance authority.
        </p>
        {contacts.map((c) => (
          <div className="document-row" key={c.id}>
            <div>
              <strong>
                {c.name} · {c.customer}
              </strong>
              <small>{c.email}</small>
            </div>
            <Badge status={c.authorized ? "approved" : "needs_review"} />
            <button
              onClick={() =>
                run(async () => {
                  await api(
                    "/contacts/" + c.id,
                    {
                      name: c.name,
                      email: c.email,
                      customer: c.customer,
                      authorized: !c.authorized,
                      acceptance_authority: c.acceptance_authority,
                    },
                    "PUT",
                  );
                  await reload();
                }, "Contact authorization updated")
              }
            >
              {c.authorized ? "Revoke authorization" : "Authorize contact"}
            </button>
          </div>
        ))}
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget,
              f = new FormData(form);
            run(async () => {
              await api("/contacts", {
                customer: f.get("customer"),
                name: f.get("name"),
                email: f.get("email"),
                authorized: f.get("authorized") === "on",
                acceptance_authority: f.get("authority") === "on",
              });
              form.reset();
              await reload();
            }, "Contact saved");
          }}
        >
          <Field label="Customer name">
            <input name="customer" required />
          </Field>
          <Field label="Contact name">
            <input name="name" required />
          </Field>
          <Field label="Contact email">
            <input name="email" type="email" required />
          </Field>
          <label className="check">
            <input name="authorized" type="checkbox" />
            Authorized for requests and billing delivery
          </label>
          <label className="check">
            <input name="authority" type="checkbox" />
            Authorized to provide customer acceptance
          </label>
          <button disabled={busy}>Add contact</button>
        </form>
      </section>
      <section className="panel">
        <h2>Email & model configuration</h2>
        <p>
          Model: <strong>{me.model_adapter}</strong> · Email:{" "}
          <strong>{me.email_adapter}</strong>
        </p>
        <p>
          {me.email_adapter === "local"
            ? "Email is simulated using the real database workflow."
            : "Email credentials and webhook configuration are managed by the deployment operator."}{" "}
          {me.model_adapter === "fixture"
            ? "Document analysis, request drafting and reply interpretation are simulated."
            : "Model requests use the configured live provider."}
        </p>
        <p>
          Document text goes to OpenAI only in live mode. Authorized outbound
          messages and attachments go to Resend. No credentials are exposed in
          this interface.
        </p>
      </section>
      <section className="panel">
        <h2>Your workspace data</h2>
        <p>
          Export work records and files. Deletion removes active files and
          cancels pending jobs and reminders. Backup copies expire under the
          deployment retention policy.
        </p>
        <a className="button" href="/api/settings/export">
          <Download size={16} />
          Export workspace
        </a>
        <details className="delete-section">
          <summary>Delete this workspace permanently</summary>
          <p>
            This removes every operator account, work item, file and pending
            reminder in this organization.
          </p>
          <Field label="Type DELETE WORKSPACE">
            <input
              value={deletion}
              onChange={(e) => setDeletion(e.target.value)}
            />
          </Field>
          <button
            className="danger"
            disabled={deletion !== "DELETE WORKSPACE" || busy}
            onClick={() =>
              run(async () => {
                const r = await fetch("/api/settings/workspace", {
                  method: "DELETE",
                  headers: { "X-Dove-Action": "1", "X-Dove-Delete": deletion },
                });
                if (!r.ok) throw new Error((await r.json()).detail);
                location.href = "/";
              }, "Workspace deleted")
            }
          >
            Permanently delete workspace
          </button>
        </details>
      </section>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
