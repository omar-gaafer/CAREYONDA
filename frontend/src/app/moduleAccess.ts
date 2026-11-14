import type { Capabilities } from "../contracts/capabilities";

/** Required capability identities, not invented endpoint names. */
const requirements: Record<string, string | undefined> = {
  "/health": "observations",
  "/environment": "observations",
  "/data-explorer": "observations",
  "/ai-intelligence": "m2_reasoning",
  "/analytics": "trained_models",
  "/recommendations": "safety_policies",
  "/reports": "investigation_persistence",
};
const blockers: Record<string, string> = {
  "/overview":
    "Mission identity, launch time, operational status and authorized context have no backend contract. No mission elapsed time or health summary is inferred.",
  "/health":
    "No authorized health observations. Authentication and subject authorization are absent; real-person health access is disabled.",
  "/environment":
    "No supported measured environmental source is exposed by this API. NASA records are not loaded. CO₂ ppm and partial pressure Pa remain distinct; radiation timing and accumulated-dose units have unresolved source limitations.",
  "/data-explorer":
    "No operational observations loaded. The existing ObservationPage v1 contract is configured_synthetic only; measured evidence requires a separately reviewed backend contract.",
  "/ai-intelligence":
    "Model unavailable for operational use. M2 executes on configured synthetic research contexts only. No frontend-generated hypotheses or precomputed results are displayed.",
  "/incidents":
    "No incident API or approved alert policy exists. Investigation results are not operational incidents; no incidents or review history are generated.",
  "/assistant":
    "No grounded assistant endpoint is implemented. No scripted replies, medical advice or spacecraft commands are supplied.",
  "/crew":
    "No authorized profiles. Authentication, subject authorization and a profile/context endpoint are required before real-person health access can be enabled.",
  "/analytics":
    "Model unavailable. No verified prediction endpoint or versioned evaluation output is exposed by this backend. No forecasts or confidence values are generated.",
  "/recommendations":
    "No approved, versioned procedure registry or independent safety-policy service is available. Actionable medical guidance is disabled.",
  "/digital-twin":
    "No trustworthy geometry/context metadata or spacecraft sensor endpoint is available. No live sensor statuses or reference schematic are invented.",
  "/reports":
    "Historical retrieval and report persistence are unavailable. No report metrics, saved investigations or replay history are generated.",
};
const messages: Record<string, [string, string]> = {
  "/overview": [
    "No data available",
    "Mission information will appear when available.",
  ],
  "/health": [
    "No observations found",
    "Health observations are currently unavailable.",
  ],
  "/environment": [
    "No observations found",
    "Environmental measurements are currently unavailable.",
  ],
  "/data-explorer": [
    "No observations found",
    "There are no observations available to inspect.",
  ],
  "/ai-intelligence": [
    "Analysis unavailable",
    "No investigation results are available.",
  ],
  "/incidents": [
    "No incident data available",
    "Incident monitoring is currently unavailable.",
  ],
  "/assistant": ["Assistant unavailable", "The assistant is not connected."],
  "/crew": [
    "No crew data available",
    "Crew profiles are currently unavailable.",
  ],
  "/analytics": [
    "Analysis unavailable",
    "Predictive results are currently unavailable.",
  ],
  "/recommendations": [
    "No protocols available",
    "Approved procedures are currently unavailable.",
  ],
  "/digital-twin": [
    "Digital twin unavailable",
    "Spacecraft monitoring is not connected.",
  ],
  "/reports": [
    "No reports available",
    "Saved reports and mission replay are currently unavailable.",
  ],
};
export function moduleAccess(path: string, data: Capabilities) {
  const required = requirements[path];
  const capability = data.capabilities.find((c) => c.name === required);
  const reported = capability?.availability;
  return {
    message: messages[path]?.[0] ?? "No data available",
    description: messages[path]?.[1] ?? "This page is currently unavailable.",
    title:
      path === "/health" || path === "/crew"
        ? "No authorized data"
        : reported === "simulation_only"
          ? "Unsupported operational data source"
          : "Capability unavailable",
    detail: blockers[path] ?? "This route has no defined integration contract.",
    reported: required
      ? capability
        ? `${required}: ${reported?.replaceAll("_", " ")} · not medically validated`
        : `${required}: not advertised by backend`
      : "No corresponding capability is advertised by this backend contract",
    // Availability alone cannot broaden source, authorization or payload contracts.
    enabled: false as const,
  };
}
