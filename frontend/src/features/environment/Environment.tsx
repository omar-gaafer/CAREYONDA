import type { Observation } from "../../contracts/observation";
import { Badge, PageIntro, Panel, Trend } from "../../shared/ui";
export function Environment({ rows }: { rows: Observation[] }) {
  return (
    <>
      <PageIntro
        eyebrow="HABITAT / ENVIRONMENTAL EVIDENCE"
        title="Environmental Monitoring"
      >
        Explore synthetic habitat measurements with explicit units and quality
        limitations.
      </PageIntro>
      <div className="notice">
        <Badge>SYNTHETIC ONLY</Badge> All plotted series are generated fixtures.
        No NASA measurements are loaded.
      </div>
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
