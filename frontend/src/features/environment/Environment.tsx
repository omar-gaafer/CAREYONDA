import { PublicModelA } from "../../app/PublicDemo";
import { ModelAPanel } from "../model-a/ModelAPanel";
import type { Observation } from "../../contracts/observation";
import { Badge, PageIntro, Panel, Trend } from "../../shared/ui";
export function Environment({
  rows,
  publicDemo = false,
  mode = "fixture",
  modelAApiUrl,
}: {
  rows: Observation[];
  publicDemo?: boolean;
  mode?: "fixture" | "api";
  modelAApiUrl?: string;
}) {
  return (
    <>
      <PageIntro
        eyebrow="HABITAT / ENVIRONMENTAL EVIDENCE"
        title="Space Environment"
      >
        Explore synthetic habitat measurements with explicit units and quality
        limitations.
      </PageIntro>
      <div className="notice">
        <Badge>SYNTHETIC ONLY</Badge> All plotted series are generated fixtures.
        No NASA measurements are plotted in these charts. Model A context
        appears separately below.
      </div>
      {publicDemo ? (
        <PublicModelA />
      ) : (
        <ModelAPanel key={mode} mode={mode} apiUrl={modelAApiUrl} />
      )}
      <div className="two-columns">
        <Trend rows={rows} metric="cabin_co2_concentration" />
        <Trend rows={rows} metric="cabin_co2_partial_pressure" />
        <Trend rows={rows} metric="environment_temperature" />
        <Trend rows={rows} metric="relative_humidity" />
      </div>
      <div className="two-columns">
        <Panel title="CO₂: two distinct measurements">
          <p>
            Concentration in ppm and partial pressure in Pa are separate
            synthetic series. They are not interchangeable and are not converted
            or paired here. A valid conversion requires total pressure and
            compatible context.
          </p>
          <p className="muted">
            Repository reference: docs/architecture/TRAINING_HANDOFF.md · NASA
            RR-1 uses ppm; synthetic M1.2 uses Pa.
          </p>
        </Panel>
        <Panel title="Radiation · data limitations">
          <Badge tone="amber">UNAVAILABLE IN THIS DEMO</Badge>
          <p>
            No radiation series is plotted. The NASA adapter retains daily
            radiation separately from telemetry. Date boundaries/timezones are
            assumed and flagged suspect; accumulated-dose units are unresolved
            and values remain unavailable.
          </p>
          <p className="muted">
            Repository reference: docs/architecture/D2_D3_NASA_RR1.md. No
            exposure limit or safety assessment is inferred.
          </p>
        </Panel>
      </div>
    </>
  );
}
