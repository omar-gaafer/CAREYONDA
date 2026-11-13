import { Link } from "react-router-dom";
import { ArrowRight, Orbit, Radio, ShieldCheck } from "lucide-react";
import {
  crew,
  DEMO_NOW,
  MISSION_START,
} from "../../infrastructure/observations";
import {
  Badge,
  MetricCard,
  ObservationValue,
  PageIntro,
  Panel,
  Trend,
  utc,
} from "../../shared/ui";
import {
  metrics,
  type Metric,
  type Observation,
} from "../../contracts/observation";
export function Overview({
  rows,
  crewId,
}: {
  rows: Observation[];
  crewId: string;
}) {
  const people = crew.filter((c) => crewId === "all" || c.id === crewId);
  return (
    <>
      <PageIntro
        eyebrow="MISSION OPERATIONS / ARES-07"
        title="Mission Command Center"
      >
        A connected view of crew observations, habitat conditions, and the
        evidence behind them.
      </PageIntro>
      <section className="mission-banner">
        <div>
          <Badge tone="cyan">
            <Radio size={12} /> SIMULATION ACTIVE
          </Badge>
          <h2>Beyond Earth. Grounded in evidence.</h2>
          <p>ARES-07 / Orbital research mission / Habitat 01</p>
          <div className="mission-meta">
            <span>
              MISSION ELAPSED{" "}
              <strong>
                {Math.floor(
                  (Date.parse(DEMO_NOW) - Date.parse(MISSION_START)) /
                    86_400_000,
                )}
                d 12h 00m
              </strong>
            </span>
            <span>
              DATA WINDOW <strong>13 NOV 2026 · UTC</strong>
            </span>
            <span>
              OPERATIONS <strong>Research demonstration</strong>
            </span>
          </div>
        </div>
        <Orbit className="orbit" size={160} strokeWidth={0.7} />
      </section>
      <div className="metric-grid">
        <MetricCard
          title="Crew in selected context"
          value={String(people.length).padStart(2, "0")}
          detail="Synthetic crew profiles"
          to="/health"
        />
        <MetricCard
          title="Observations in window"
          value={String(rows.length)}
          detail="Event-time filtered evidence"
          to="/data-explorer"
        />
        <MetricCard
          title="Quality limitations"
          value={String(
            rows.filter((o) => o.quality.status !== "valid").length,
          )}
          detail="Missing, suspect, or invalid records"
          to="/data-explorer?quality=limited"
        />
        <MetricCard
          title="Safety assessment"
          value="Not evaluated"
          detail="No operational safety determination"
          to="/recommendations"
        />
      </div>
      <div className="two-columns">
        <Panel
          title="Crew observation overview"
          action={
            <Link className="text-link" to="/health">
              View monitoring <ArrowRight size={14} />
            </Link>
          }
        >
          <div className="crew-list">
            {people.map((c) => {
              const latest = rows
                .filter(
                  (o) =>
                    o.metric === "heart_rate" &&
                    o.scope.kind === "astronaut" &&
                    o.scope.astronaut_id === c.id,
                )
                .at(-1);
              return (
                <Link to="/health" className="crew-row" key={c.id}>
                  <div className="avatar">{c.initials}</div>
                  <div className="grow">
                    <strong>{c.name}</strong>
                    <small>{c.role} · synthetic</small>
                  </div>
                  <div>
                    {latest ? (
                      <ObservationValue observation={latest} />
                    ) : (
                      "No observations"
                    )}
                    <small>Latest heart rate</small>
                  </div>
                </Link>
              );
            })}
          </div>
          <div className="panel-foot">
            <ShieldCheck size={16} /> Measurements describe evidence, not
            medical status.
          </div>
        </Panel>
        <Trend rows={rows} metric="cabin_co2_concentration" />
      </div>
      <Panel
        title="Environmental observation snapshot"
        action={
          <Link className="text-link" to="/environment">
            Explore environment <ArrowRight size={14} />
          </Link>
        }
      >
        <div className="environment-snapshot">
          {(
            [
              "environment_temperature",
              "relative_humidity",
              "cabin_co2_concentration",
              "cabin_co2_partial_pressure",
            ] as Metric[]
          ).map((metric) => {
            const latest = rows.filter((o) => o.metric === metric).at(-1);
            return (
              <div key={metric}>
                <small>{metrics[metric].label}</small>
                <strong>
                  {latest ? (
                    <ObservationValue observation={latest} />
                  ) : (
                    "No observations"
                  )}
                </strong>
                <small>
                  {latest?.quality.status ?? "Unavailable"} · synthetic
                </small>
              </div>
            );
          })}
        </div>
        <div className="panel-foot">
          Observation quality is separate from environmental safety. Radiation
          is unavailable in this demonstration.
        </div>
      </Panel>
      <div className="two-columns overview-bottom">
        <Panel title="Recent simulated observations">
          <div className="event-list">
            {[...rows]
              .reverse()
              .slice(0, 4)
              .map((o) => (
                <Link
                  to={`/data-explorer?metric=${o.metric}`}
                  key={o.observation_id}
                >
                  <span className="event-dot" />
                  <div>
                    <strong>{o.metric.replaceAll("_", " ")}</strong>
                    <small>{utc(o.timestamp)}</small>
                  </div>
                  <ObservationValue observation={o} />
                </Link>
              ))}
          </div>
        </Panel>
        <Panel title="Simulation event log" action={<Badge>DEMO EVENTS</Badge>}>
          <div className="event-list">
            <div>
              <span className="event-dot amber" />
              <div>
                <strong>Humidity record marked invalid</strong>
                <small>03:30 UTC · synthetic physical-domain violation</small>
              </div>
            </div>
            <div>
              <span className="event-dot amber" />
              <div>
                <strong>Heart-rate sample not received</strong>
                <small>21:30 UTC, previous day · synthetic dropout</small>
              </div>
            </div>
            <div>
              <span className="event-dot" />
              <div>
                <strong>Research fixture loaded</strong>
                <small>Not an operational incident feed</small>
              </div>
            </div>
          </div>
          <Link to="/incidents" className="text-link">
            Incident capability status <ArrowRight size={14} />
          </Link>
        </Panel>
      </div>
    </>
  );
}
