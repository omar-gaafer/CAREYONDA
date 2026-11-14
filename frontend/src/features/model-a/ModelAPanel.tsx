import { useEffect, useState, useRef } from "react";
import {
  authorizedSchema,
  modelAResponseSchema,
  type ModelAResponse,
} from "../../contracts/model-a";
import {
  createModelAClient,
  ModelAError,
  type ModelAClient,
} from "../../infrastructure/model-a";
import fixture from "../../infrastructure/fixtures/model-a-simulated.json";
import { Panel, Badge } from "../../shared/ui";
const errors = {
  unauthorized:
    "Unauthorized sample or missing replay receipt. No result substituted.",
  invalid:
    "Invalid input or unavailable evidence at the requested assessment time (422).",
  backend: "Model A backend unavailable. No fixture fallback.",
  contract:
    "Unsupported or inconsistent Model A API response. No result substituted.",
};
export function ModelAPanel({
  mode,
  apiUrl = "http://127.0.0.1:8000",
  client: injected,
}: {
  mode: "fixture" | "api";
  apiUrl?: string;
  client?: ModelAClient;
}) {
  const epoch = useRef(0);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [catalog, setCatalog] = useState<ReturnType<
    typeof authorizedSchema.parse
  > | null>(null);
  const [result, setResult] = useState<ModelAResponse | null>(null);
  const [selected, setSelected] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const ticket = ++epoch.current;
    let active = true;
    setResult(null);
    setCatalog(null);
    setError("");
    setState("loading");
    if (mode === "fixture") {
      setResult(modelAResponseSchema.parse(fixture));
      setState("ready");
      return;
    }
    try {
      const client = injected ?? createModelAClient(apiUrl);
      client
        .list()
        .then((data) => {
          if (!active) return;
          setCatalog(data);
          setSelected(
            data.samples[0]
              ? `${data.samples[0].sample_id}|${data.samples[0].assessment_mode}`
              : "",
          );
          setState(
            data.model_availability !== "available"
              ? "unavailable"
              : data.samples.length
                ? "select"
                : "empty",
          );
        })
        .catch((e) => {
          if (active) {
            setError(
              e instanceof ModelAError ? errors[e.kind] : errors.contract,
            );
            setState("error");
          }
        });
    } catch {
      setError(errors.contract);
      setState("error");
    }
    return () => {
      active = false;
      epoch.current++;
    };
  }, [mode, apiUrl, injected, retry]);
  async function assess() {
    const reference = catalog?.samples.find(
      (s) => `${s.sample_id}|${s.assessment_mode}` === selected,
    );
    if (!reference) return;
    const ticket = ++epoch.current;
    setResult(null);
    setError("");
    setState("loading");
    try {
      const data = await (injected ?? createModelAClient(apiUrl)).assess(
        reference,
        new Date().toISOString(),
      );
      if (epoch.current !== ticket) return;
      setResult(data);
      setState(
        data.model_availability === "available" ? "ready" : "unavailable",
      );
    } catch (e) {
      if (epoch.current !== ticket) return;
      setError(
        e instanceof ModelAError
          ? `${errors[e.kind]}${e.correlation ? ` Correlation: ${e.correlation}` : ""}`
          : errors.contract,
      );
      setState("error");
    }
  }
  const context = result?.contexts[0];
  return (
    <div className="model-a-context">
      <Panel title="Model A · Environmental statistical context">
        <Badge>
          {mode === "fixture" ? "SIMULATED MODEL A DEMO" : "LOCAL MODEL A API"}
        </Badge>
        <p>
          Independent from M2 investigations and crew filters. Research only;
          not clinical risk, hazard severity or calibrated confidence.
        </p>
        <p>
          Model availability:{" "}
          {result?.model_availability ??
            catalog?.model_availability ??
            "loading"}
        </p>
        {state === "loading" && <p role="status">Loading Model A context…</p>}
        {state === "error" && <p role="alert">{error}</p>}
        {state === "empty" && (
          <p role="status">
            Authorized replay sample unavailable. No server-authorized evidence
            has been provisioned.
          </p>
        )}
        {state === "unavailable" && (
          <p role="status">
            Model unavailable
            {result
              ? ` (${result.model_availability}, 503)`
              : catalog
                ? ` (${catalog.model_availability})`
                : ""}
            . No inference or fixture fallback.
          </p>
        )}
        {mode === "api" && catalog?.samples.length !== 0 && catalog && (
          <div>
            <label>
              Authorized environmental sample{" "}
              <select
                aria-label="Authorized environmental sample"
                value={selected}
                disabled={state === "loading"}
                onChange={(e) => {
                  epoch.current++;
                  setSelected(e.target.value);
                  setResult(null);
                  setState("select");
                }}
              >
                {catalog.samples.map((s) => (
                  <option
                    key={`${s.sample_id}:${s.assessment_mode}`}
                    value={`${s.sample_id}|${s.assessment_mode}`}
                  >
                    {s.sample_id} · {s.assessment_mode}
                  </option>
                ))}
              </select>
            </label>
            <button
              disabled={
                state === "loading" ||
                catalog.model_availability !== "available"
              }
              onClick={() => void assess()}
            >
              Assess Model A
            </button>
          </div>
        )}
        {mode === "api" && (
          <button onClick={() => setRetry((x) => x + 1)}>
            Refresh Model A availability
          </button>
        )}
        {context && (
          <div>
            <dl>
              <dt>Model availability</dt>
              <dd>
                {result?.model_availability} / {context.compatibility}
              </dd>
              <dt>Model</dt>
              <dd>
                {context.model?.model_id ?? "Unavailable"} ·{" "}
                {context.model?.model_version ?? "—"}
              </dd>
              <dt>Assessment mode</dt>
              <dd>
                {mode === "fixture"
                  ? "Simulated fixture — not live evidence"
                  : context.assessment_mode}
              </dd>
              <dt>Statistical status</dt>
              <dd>{context.status}</dd>
              <dt>Statistical anomaly score</dt>
              <dd>{context.anomaly_score ?? "Not scored"}</dd>
              <dt>Decision threshold</dt>
              <dd>
                {context.threshold ?? "Unassessed"} ·{" "}
                {context.threshold_method ?? "No method"}
              </dd>
              <dt>Assessment time</dt>
              <dd>{context.assessed_at}</dd>
              <dt>Original mission event time</dt>
              <dd>{context.source_event_time}</dd>
              <dt>Replay acquisition time</dt>
              <dd>{context.replay_acquired_at ?? "Not a replay"}</dd>
              <dt>Historical source availability</dt>
              <dd>
                {mode === "fixture"
                  ? "Not established — simulated fixture"
                  : context.historical_source_availability}
              </dd>
              <dt>Evidence availability scope</dt>
              <dd>
                {mode === "fixture"
                  ? "Simulated only"
                  : context.evidence_availability_scope}
              </dd>
              <dt>Missing-data / abstention reasons</dt>
              <dd>{context.abstention_reasons.join(", ") || "None"}</dd>
              <dt>Imputed features</dt>
              <dd>{context.imputed_features.join(", ") || "None"}</dd>
              <dt>Correlation ID</dt>
              <dd>{result?.correlation_id}</dd>
              <dt>Mission / environment</dt>
              <dd>
                {mode === "fixture"
                  ? "Synthetic demo mission / simulated habitat / synthetic"
                  : `${context.sample.scope.mission_id} / ${context.sample.scope.spacecraft_id} / ${context.sample.scope.data_origin}`}
              </dd>
              <dt>Dataset / run</dt>
              <dd>
                {context.sample.scope.dataset_id} /{" "}
                {context.sample.scope.run_id}
              </dd>
              <dt>Replay receipt</dt>
              <dd>
                {context.sample.replay_acquisition?.record_id ??
                  "Not applicable"}
              </dd>
            </dl>
            <details>
              <summary>Feature and evidence provenance</summary>
              <p>
                Feature schema {context.model?.feature_schema_version} ·{" "}
                {context.sample.transformation_version}
              </p>
              <p>Artifact SHA-256: {context.model?.artifact_sha256}</p>
              <p>
                Training dataset manifest SHA-256:{" "}
                {context.model?.dataset_manifest_sha256}
              </p>
              <ul>
                {context.sample.features.map((f) => (
                  <li key={f.name}>
                    {f.name} [{f.unit}] ·{" "}
                    {f.observation_ids.join(", ") || "No observation"}
                  </li>
                ))}
              </ul>
              <ul>
                {context.sample.observations.map((o) => (
                  <li key={o.observation_id}>
                    {o.observation_id} · {o.provenance.source_id} ·{" "}
                    {mode === "fixture" ? "simulated" : o.provenance.origin} ·{" "}
                    {o.provenance.method} · quality: {o.quality.status}{" "}
                    {o.quality.reason_codes.join(", ")} · source ingestion:{" "}
                    {o.ingested_at ?? "unknown"}
                  </li>
                ))}
              </ul>
            </details>
            <ul>
              {[...(result?.limitations ?? []), ...context.limitations].map(
                (text, i) => (
                  <li key={i}>{text}</li>
                ),
              )}
            </ul>
          </div>
        )}
      </Panel>
    </div>
  );
}
