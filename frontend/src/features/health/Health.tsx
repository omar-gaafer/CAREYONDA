import type { Observation } from "../../contracts/observation";
import { crew } from "../../testing/observations";
import { Badge, PageIntro, Trend } from "../../shared/ui";
export function Health({
  rows,
  crewId,
}: {
  rows: Observation[];
  crewId: string;
}) {
  return (
    <>
      <PageIntro eyebrow="CREW / OBSERVED EVIDENCE" title="Health Monitoring">
        Synthetic heart rate and reported sleep. Select a crew member and time
        range above to explore the evidence.
      </PageIntro>
      <div className="notice">
        <Badge>SYNTHETIC ONLY</Badge> No diagnosis, clinical thresholds, or
        medical confidence estimates are provided.
      </div>
      {crew
        .filter((c) => crewId === "all" || c.id === crewId)
        .map((c) => (
          <section key={c.id} className="crew-section">
            <h2>
              {c.name} <span>{c.role}</span>
            </h2>
            <div className="two-columns">
              <Trend rows={rows} metric="heart_rate" person={c.id} />
              <Trend rows={rows} metric="sleep_duration" person={c.id} />
            </div>
          </section>
        ))}
    </>
  );
}
