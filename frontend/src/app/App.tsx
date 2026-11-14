import { SyntheticDatabase } from "../features/synthetic-database/SyntheticDatabase";
import { Database as DatabaseIcon } from "lucide-react";
import { M2Research } from "../features/research/M2Research";
import { ModelAContextPanel } from "../features/model-a/ModelAContextPanel";
import { ModelCPanel } from "../features/model-c/ModelCPanel";
import { Account } from "../features/account/Account";
import { Fragment, useEffect, useRef, useState } from "react";
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { ChevronLeft, ChevronRight, Menu, Search, X } from "lucide-react";
import { BrandLogo } from "../shared/BrandLogo";
import { PageIntro, Panel, utc } from "../shared/ui";
import { modules } from "./modules";
import { useCapabilities, type CapabilityState } from "./useCapabilities";
import { moduleAccess } from "./moduleAccess";
import { SpacecraftTwin } from "../features/digital-twin/SpacecraftTwin";

const connectionLabels = {
  disconnected: "Connection unavailable",
  permission_denied: "Access unavailable",
  contract_mismatch: "Unable to load results",
  unavailable: "Connection unavailable",
  configuration: "Connection unavailable",
};
const errorDetails = {
  disconnected: "The local API could not be reached.",
  permission_denied:
    "The server denied access. No subject data was requested or retained.",
  contract_mismatch:
    "The capability payload is malformed or its contract version is unsupported.",
  unavailable: "The local API returned an unsuccessful response.",
  configuration: "A credential-free loopback HTTP API origin is required.",
};
function CapabilityContent({
  path,
  state,
  refresh,
  apiUrl,
  enableSyntheticViewer = false,
}: {
  apiUrl: string;
  enableSyntheticViewer?: boolean;
  path: string;
  state: CapabilityState;
  refresh: () => void;
}) {
  if (path === "/synthetic-database" && enableSyntheticViewer)
    return <SyntheticDatabase apiUrl={apiUrl} />;
  if (path === "/ai-intelligence") return <M2Research apiUrl={apiUrl} />;
  if (path === "/account") return <Account apiUrl={apiUrl} />;
  if (path === "/sleep-fatigue")
    return (
      <ModelCPanel title="Sleep/fatigue research" mode="api" apiUrl={apiUrl} />
    );
  if (path === "/environment")
    return (
      <>
        <PageIntro title="Environmental Monitoring">
          Historical research replay is separate from contemporary astronaut
          exposure.
        </PageIntro>
        <ModelAContextPanel mode="api" apiUrl={apiUrl} />
      </>
    );
  if (state.status === "ready" && path === "/analytics")
    return (
      <>
        <PageIntro title="AI research availability" />
        <Panel title="Model B">
          Actual synthetic-health estimator is available through the verified
          CLI workflow. Canonical decision remains unassessed pending owner
          approval. No clinical interpretation.
        </Panel>
        <Panel title="Temporal and Hybrid research">
          Run the documented H1/H2 examples and H3 frozen evaluation. NASA
          replay is quarantined from prospective astronaut evidence. No combined
          inference is fabricated.
        </Panel>
      </>
    );
  if (path === "/digital-twin") return <SpacecraftTwin />;
  const module = modules.find((m) => m.path === path);
  const access =
    state.status === "ready" ? moduleAccess(path, state.data) : null;
  return (
    <>
      {!module ? (
        <>
          <PageIntro title="Page not found" />
          <div className="state" role="status">
            <h2>Page unavailable</h2>
            <p>Choose a page from the navigation.</p>
          </div>
        </>
      ) : state.status === "loading" ? (
        <div className="state" role="status" aria-live="polite">
          <h2>Loading…</h2>
        </div>
      ) : state.status === "error" ? (
        <>
          <PageIntro title={module.title} />
          <div className="state" role="alert" data-kind={state.kind}>
            <h2>{connectionLabels[state.kind]}</h2>
            <p>
              {state.kind === "permission_denied"
                ? "You don’t have access to this content."
                : "Please try again."}
            </p>
            {state.previousSnapshotInvalidated && (
              <p>Previously loaded information is no longer current.</p>
            )}
            <button onClick={refresh}>Retry</button>
            <details className="technical-details">
              <summary>Technical details</summary>
              <p>{errorDetails[state.kind]}</p>
              {state.previousSnapshotInvalidated && (
                <p>
                  The previous capability snapshot was invalidated after refresh
                  failed.
                </p>
              )}
            </details>
          </div>
        </>
      ) : (
        <>
          <PageIntro title={module.title} />
          {path === "/overview" ? (
            <>
              <div className="dashboard-empty-grid">
                <Panel title="Mission">
                  <p>No mission data available.</p>
                </Panel>
                <Panel title="Crew health">
                  <p>No health observations available.</p>
                </Panel>
                <Panel title="Environment">
                  <p>No environmental observations available.</p>
                </Panel>
                <Panel title="Incidents">
                  <p>No incident data available.</p>
                </Panel>
              </div>
            </>
          ) : (
            <div
              className="capability-hero"
              role="status"
              data-kind="unavailable"
            >
              <h2>{access?.message}</h2>
              <p>{access?.description}</p>
            </div>
          )}
          <details className="technical-details">
            <summary>Technical details</summary>
            <p>{access?.detail}</p>
            <p>{access?.reported}</p>
            <p>
              Authentication: none, local only. Real-person health access is
              disabled.
            </p>
            <p>
              Safety not evaluated. No operational observations or analysis
              results are loaded.
            </p>
            <p>
              Capability metadata retrieved {utc(state.retrievedAt)}. This
              timestamp does not indicate measurement freshness or continuous
              connectivity.
            </p>
            {path === "/overview" && (
              <Panel title="Service capabilities">
                {state.data.capabilities.length ? (
                  <dl className="capability-inventory">
                    {state.data.capabilities.map((c) => (
                      <Fragment key={c.name}>
                        <dt>{c.name.replaceAll("_", " ")}</dt>
                        <dd>
                          {c.availability.replaceAll("_", " ")}
                          <small>Not medically validated</small>
                        </dd>
                      </Fragment>
                    ))}
                  </dl>
                ) : (
                  <p>No capabilities advertised</p>
                )}
              </Panel>
            )}
          </details>
        </>
      )}
    </>
  );
}

export function App({
  apiUrl = "http://127.0.0.1:8000",
  enableSyntheticViewer = false,
}: {
  apiUrl?: string;
  enableSyntheticViewer?: boolean;
}) {
  const navigationModules = enableSyntheticViewer
    ? [
        ...modules,
        {
          path: "/synthetic-database",
          title: "Synthetic Research Dataset",
          short: "Local Synthetic Data",
          icon: DatabaseIcon,
        },
      ]
    : modules;
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const paletteTriggerRef = useRef<HTMLButtonElement>(null);
  const [offline, setOffline] = useState(!navigator.onLine);
  const location = useLocation();
  const { state, refresh } = useCapabilities(apiUrl);
  useEffect(() => {
    setMobileOpen(false);
    document.title = `${navigationModules.find((m) => m.path === location.pathname)?.title ?? "Page not found"} · CAREYONDA`;
    document.getElementById("main-content")?.focus();
  }, [location.pathname]);
  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => {
          if (open)
            requestAnimationFrame(() => paletteTriggerRef.current?.focus());
          return !open;
        });
        setPaletteQuery("");
      } else if (event.key === "Escape" && paletteOpen) {
        setPaletteOpen(false);
        requestAnimationFrame(() => paletteTriggerRef.current?.focus());
      } else if (
        event.key === "/" &&
        !(event.target instanceof HTMLInputElement) &&
        !(event.target instanceof HTMLTextAreaElement)
      ) {
        event.preventDefault();
        setPaletteOpen(true);
        setPaletteQuery("");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [paletteOpen]);
  const paletteItems = navigationModules.filter((module) =>
    `${module.title} ${module.short}`
      .toLowerCase()
      .includes(paletteQuery.trim().toLowerCase()),
  );
  useEffect(() => {
    if (!mobileOpen) return;
    const drawer = document.getElementById("mission-navigation");
    const controls = drawer?.querySelectorAll<HTMLElement>(
      ".mobile-close, nav a",
    );
    controls?.[0]?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        document.querySelector<HTMLButtonElement>(".mobile-menu")?.focus();
      }
      if (event.key === "Tab" && controls?.length) {
        const first = controls[0],
          last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileOpen]);
  return (
    <div className={`app-shell ${collapsed ? "is-collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      {mobileOpen && (
        <button
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        id="mission-navigation"
        className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}
        aria-label="Mission navigation"
        role={mobileOpen ? "dialog" : undefined}
        aria-modal={mobileOpen || undefined}
      >
        <div className="brand">
          <BrandLogo variant="navigation" compact={collapsed} />
          <button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="nav-caption">MISSION WORKSPACE</div>
        <nav aria-label="Workspace modules">
          {navigationModules.map((m, i) => (
            <Fragment key={m.path}>
              {[0, 5, 9].includes(i) && (
                <div className="nav-group-label">
                  {i === 0
                    ? "MONITOR & INVESTIGATE"
                    : i === 5
                      ? "INTELLIGENCE & CREW"
                      : "DATA & SYSTEMS"}
                </div>
              )}
              <NavLink
                to={m.path}
                title={m.title}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "active" : ""}`
                }
              >
                <m.icon size={19} />
                <span>{m.short}</span>
                <small>{String(i + 1).padStart(2, "0")}</small>
              </NavLink>
            </Fragment>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button
            className="collapse-button"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
          >
            {collapsed ? (
              <ChevronRight size={17} />
            ) : (
              <>
                <ChevronLeft size={17} />
                <span>Collapse navigation</span>
              </>
            )}
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="top-context">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
              aria-controls="mission-navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={20} />
            </button>
            <BrandLogo variant="icon" />
            <span>Mission workspace</span>
          </div>
          <div className="mode-controls">
            <button
              ref={paletteTriggerRef}
              className="command-search-trigger"
              onClick={() => {
                setPaletteOpen(true);
                setPaletteQuery("");
              }}
              aria-haspopup="dialog"
              aria-label="Search and navigate modules"
            >
              <Search size={15} />
              <span>Search</span>
              <kbd>Ctrl K</kbd>
            </button>
            {state.status === "error" && (
              <span className="connection-status" role="status">
                {connectionLabels[state.kind]}
              </span>
            )}
            <button onClick={refresh} disabled={state.status === "loading"}>
              Refresh
            </button>
          </div>
        </header>
        {offline && (
          <div className="offline-banner" role="status">
            Your device is offline. Local services may still be available.
          </div>
        )}
        <div className="context-bar">
          <span>
            {navigationModules.find((m) => m.path === location.pathname)
              ?.short ?? "Workspace"}
          </span>
          <div className="context-filters">
            <label>
              Crew
              <select aria-label="Crew" disabled>
                <option>No crew available</option>
              </select>
            </label>
            <label>
              Time range
              <select aria-label="Time range" disabled>
                <option>No observations available</option>
              </select>
            </label>
          </div>
        </div>
        <main id="main-content" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Navigate replace to="/overview" />} />
            {navigationModules.map((m) => (
              <Route
                key={m.path}
                path={m.path}
                element={
                  <CapabilityContent
                    apiUrl={apiUrl}
                    enableSyntheticViewer={enableSyntheticViewer}
                    path={m.path}
                    state={state}
                    refresh={refresh}
                  />
                }
              />
            ))}
            <Route
              path="*"
              element={
                <CapabilityContent
                  apiUrl={apiUrl}
                  enableSyntheticViewer={enableSyntheticViewer}
                  path={location.pathname}
                  state={state}
                  refresh={refresh}
                />
              }
            />
          </Routes>
        </main>
        <footer className="footer">
          <div className="footer-brand">
            <BrandLogo />
          </div>
        </footer>
      </div>
      {paletteOpen && (
        <div
          className="command-palette-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setPaletteOpen(false);
              requestAnimationFrame(() => paletteTriggerRef.current?.focus());
            }
          }}
        >
          <section
            className="command-palette"
            role="dialog"
            aria-modal="true"
            aria-labelledby="command-palette-title"
            onKeyDown={(event) => {
              if (event.key !== "Tab") return;
              const controls =
                event.currentTarget.querySelectorAll<HTMLElement>(
                  'input, button, a[href]:not([tabindex="-1"])',
                );
              if (!controls.length) return;
              const first = controls[0];
              const last = controls[controls.length - 1];
              if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
              } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
              }
            }}
          >
            <h2 id="command-palette-title" className="sr-only">
              Search workspace modules
            </h2>
            <div className="command-palette-input">
              <Search size={18} aria-hidden="true" />
              <input
                autoFocus
                type="search"
                placeholder="Where would you like to go?"
                aria-label="Search pages"
                value={paletteQuery}
                onChange={(event) => setPaletteQuery(event.target.value)}
              />
              <button
                onClick={() => {
                  setPaletteOpen(false);
                  requestAnimationFrame(() =>
                    paletteTriggerRef.current?.focus(),
                  );
                }}
                aria-label="Close search"
              >
                <X size={17} />
              </button>
            </div>
            <p className="command-palette-label">WORKSPACE PAGES</p>
            <div className="command-palette-results">
              {paletteItems.length ? (
                paletteItems.map((module) => (
                  <NavLink
                    key={module.path}
                    to={module.path}
                    onClick={() => setPaletteOpen(false)}
                    className="command-palette-item"
                  >
                    <module.icon size={17} />
                    <span>{module.title}</span>
                    <kbd>↵</kbd>
                  </NavLink>
                ))
              ) : (
                <p className="command-palette-empty" role="status">
                  No pages match “{paletteQuery}”.
                </p>
              )}
            </div>
            <div className="command-palette-hint">
              Press <kbd>Esc</kbd> to close · Search uses page names only
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
