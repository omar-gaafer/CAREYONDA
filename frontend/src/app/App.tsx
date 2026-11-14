import { useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  Orbit,
  Radio,
  WifiOff,
  ChevronDown,
} from "lucide-react";
import { modules } from "./modules";
import {
  fixtureRepository,
  crew,
  filterObservations,
  type ObservationRepository,
} from "../infrastructure/observations";
import type { Observation } from "../contracts/observation";
import { parseObservations } from "../contracts/observation";
import { Badge, SourceNote, State } from "../shared/ui";
import { Overview } from "../features/overview/Overview";
import { Health } from "../features/health/Health";
import { Environment } from "../features/environment/Environment";
import { Explorer } from "../features/explorer/Explorer";
import { Capability } from "../features/capabilities/Capability";
import { Intelligence } from "../features/investigations/Intelligence";
import { Incidents } from "../features/incidents/Incidents";
import { ModelCPanel } from "../features/model-c/ModelCPanel";
import { useInvestigations } from "../features/investigations/application";
import {
  syntheticInvestigationRepository,
  type InvestigationRepository,
} from "../infrastructure/investigations";
import type { IncidentReview } from "../features/incidents/application";
import { PublicDemoNotice, PrivateModelC } from "./PublicDemo";

export function App({
  publicDemo = false,
  modelAApiUrl = "http://127.0.0.1:8000",
  dataMode = "fixture",
  onModeChange,
  repository = fixtureRepository,
  investigationRepository = syntheticInvestigationRepository,
}: {
  publicDemo?: boolean;
  modelAApiUrl?: string;
  dataMode?: "fixture" | "api";
  onModeChange?: (mode: "fixture" | "api") => void;
  repository?: ObservationRepository;
  investigationRepository?: InvestigationRepository;
}) {
  const [collapsed, setCollapsed] = useState(false),
    [mobileOpen, setMobileOpen] = useState(false);
  const [crewId, setCrewId] = useState("all"),
    [hours, setHours] = useState(24);
  const [rows, setRows] = useState<Observation[]>([]),
    [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0),
    [offline, setOffline] = useState(!navigator.onLine);
  const location = useLocation();
  const investigations = useInvestigations(investigationRepository);
  const [reviews, setReviews] = useState<Record<string, IncidentReview>>({});
  const phase2 = (content: React.ReactNode) =>
    investigations.status === "loading" ? (
      <State kind="loading">
        Validating synthetic investigation contracts.
      </State>
    ) : investigations.status === "error" ? (
      <State kind="error" retry={investigations.retry}>
        Investigation payload unavailable, malformed, or unsupported version. No
        result has been substituted.
      </State>
    ) : (
      content
    );
  useEffect(() => {
    let active = true;
    setStatus("loading");
    repository
      .list()
      .then((data) => {
        const validated = parseObservations(data);
        if (active) {
          setRows(validated);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [repository, attempt]);
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
    setMobileOpen(false);
    const title =
      modules.find((m) => m.path === location.pathname)?.title ??
      "Page not found";
    document.title = `${title} · CAREYONDA`;
    document.getElementById("main-content")?.focus();
  }, [location.pathname]);
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
  const filtered = filterObservations(rows, crewId, hours);
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
        role={mobileOpen ? "dialog" : undefined}
        aria-modal={mobileOpen ? true : undefined}
        id="mission-navigation"
        className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}
        aria-label="Mission navigation"
      >
        <div className="brand">
          <div className="brand-mark">
            <Orbit size={27} />
          </div>
          <div className="brand-text">
            <strong>CAREYONDA</strong>
            <span>MISSION INTELLIGENCE</span>
          </div>
          <button
            className="mobile-close"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="nav-caption">WORKSPACE / ARES-07</div>
        <nav>
          {modules.map((m, i) => (
            <NavLink
              key={m.path}
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
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-status">
            <span className="status-dot" />
            <span>Local research workspace</span>
          </div>
          <p>
            PHASE 02 <span>•</span> SYNTHETIC DATA
          </p>
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
            <span className="context-orbit">
              <Orbit size={19} />
            </span>
            <strong>ARES-07</strong>
            <span className="top-divider" />
            <span>Orbital Research Mission</span>
            <ChevronDown size={13} />
          </div>
          <div className="mode-controls">
            {onModeChange && (
              <label>
                Data source
                <select
                  aria-label="Data source"
                  value={dataMode}
                  onChange={(e) =>
                    onModeChange?.(e.target.value as "fixture" | "api")
                  }
                >
                  <option value="fixture">Offline fixtures</option>
                  <option value="api">Local API · synthetic</option>
                </select>
              </label>
            )}
            <Badge tone="cyan">
              <Radio size={12} />
              {dataMode === "api" ? "LOCAL API · SYNTHETIC" : "SYNTHETIC MODE"}
            </Badge>
          </div>
        </header>
        {offline && (
          <div className="offline-banner" role="status">
            <WifiOff size={16} /> Browser reports offline.{" "}
            {dataMode === "api"
              ? "Local API connectivity is separate from internet connectivity; requests may fail. No fixture fallback."
              : "Local synthetic observations remain available; no network service is required."}
          </div>
        )}
        <div className="context-bar">
          <div>
            <span className="status-dot" /> RESEARCH WORKSPACE{" "}
            <span className="context-label">/ HABITAT 01</span>
          </div>
          <div className="context-filters">
            <label>
              Crew
              <select
                aria-label="Crew"
                value={crewId}
                onChange={(e) => setCrewId(e.target.value)}
              >
                <option value="all">All crew members</option>
                {crew.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Time range
              <select
                aria-label="Time range"
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
              >
                <option value={24}>Last 24 hours</option>
                <option value={12}>Last 12 hours</option>
                <option value={6}>Last 6 hours</option>
              </select>
            </label>
          </div>
        </div>
        <main id="main-content" tabIndex={-1}>
          {publicDemo && <PublicDemoNotice />}
          {status === "loading" ? (
            <State kind="loading">
              Validating the synthetic evidence contract.
            </State>
          ) : status === "error" ? (
            <State kind="error" retry={() => setAttempt(attempt + 1)}>
              The evidence source could not be loaded or failed contract
              validation (malformed data or unsupported contract version). No
              measurements have been substituted.
            </State>
          ) : (
            <Routes>
              <Route path="/" element={<Navigate replace to="/overview" />} />
              <Route
                path="/overview"
                element={<Overview rows={filtered} crewId={crewId} />}
              />
              <Route
                path="/health"
                element={<Health rows={filtered} crewId={crewId} />}
              />
              <Route
                path="/environment"
                element={
                  <Environment
                    publicDemo={publicDemo}
                    rows={filtered}
                    mode={dataMode}
                    modelAApiUrl={modelAApiUrl}
                  />
                }
              />
              <Route
                path="/data-explorer"
                element={<Explorer rows={filtered} />}
              />
              <Route
                path="/ai-intelligence"
                element={phase2(
                  <Intelligence
                    apiControls={
                      dataMode === "api" ? investigations : undefined
                    }
                    key={crewId}
                    cases={investigations.cases}
                    crewId={crewId}
                    hours={hours}
                  />,
                )}
              />
              <Route
                path="/incidents"
                element={phase2(
                  <Incidents
                    key={crewId}
                    cases={investigations.cases}
                    crewId={crewId}
                    reviews={reviews}
                    onReview={(id, next) =>
                      setReviews((old) => ({ ...old, [id]: next }))
                    }
                  />,
                )}
              />
              <Route
                path="/model-c"
                element={
                  publicDemo ? (
                    <PrivateModelC />
                  ) : (
                    <ModelCPanel
                      title={
                        modules.find((m) => m.path === "/model-c")?.title ??
                        "Sleep/Fatigue Research Monitor"
                      }
                      mode={dataMode}
                      apiUrl={modelAApiUrl}
                    />
                  )
                }
              />
              {modules
                .filter((m) => !m.phase1 && !m.phase2 && !m.local)
                .map((m) => (
                  <Route
                    key={m.path}
                    path={m.path}
                    element={<Capability title={m.title} detail={m.detail!} />}
                  />
                ))}
              <Route
                path="*"
                element={
                  <Capability
                    title="Page not found"
                    detail="This route is not part of the CAREYONDA workspace. Use the navigation to open an available module."
                  />
                }
              />
            </Routes>
          )}
          {dataMode === "fixture" ? (
            <SourceNote />
          ) : (
            <div className="source-note">
              Local API · configured synthetic evidence · M2 executes on request
              · no authentication, persistence, medical validation or safety
              evaluation
            </div>
          )}
        </main>
        <footer className="footer">
          <span>
            CAREYONDA <span className="muted">/ Research decision support</span>
          </span>
          <span>Human review required · Safety not evaluated</span>
        </footer>
      </div>
    </div>
  );
}
