import type { ReactNode } from "react";
import { Activity, ArrowUpRight, Database, AlertCircle } from "lucide-react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  metrics,
  type Metric,
  type Observation,
} from "../contracts/observation";
export const utc = (value: string) =>
  new Date(value).toISOString().replace("T", " ").replace(".000Z", " UTC");
export const clock = (value: string) =>
  new Date(value).toISOString().slice(11, 16);
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function State({
  kind,
  children,
  retry,
}: {
  kind: "loading" | "error" | "empty" | "unavailable";
  children: ReactNode;
  retry?: () => void;
}) {
  return (
    <div className="state" role={kind === "error" ? "alert" : "status"}>
      <AlertCircle size={28} />
      <h2>
        {kind === "loading"
          ? "Loading observations"
          : kind === "empty"
            ? "No matching observations"
            : kind === "error"
              ? "Observations unavailable"
              : "Capability not connected"}
      </h2>
      <p>{children}</p>
      {retry && <button onClick={retry}>Try again</button>}
    </div>
  );
}
export function MetricCard({
  title,
  value,
  unit,
  detail,
  to,
}: {
  title: string;
  value: string;
  unit?: string;
  detail: string;
  to: string;
}) {
  return (
    <Link className="metric-card" to={to}>
      <div className="flex items-center justify-between">
        <span>{title}</span>
        <ArrowUpRight size={17} />
      </div>
      <div className="metric-value">
        {value} <small>{unit}</small>
      </div>
      <p>{detail}</p>
    </Link>
  );
}
export function ObservationValue({
  observation: o,
}: {
  observation: Observation;
}) {
  return (
    <span className={o.quality.status === "invalid" ? "text-amber-300" : ""}>
      {o.measurement.kind === "numeric"
        ? `${o.measurement.value} ${o.measurement.unit}`
        : o.measurement.kind === "boolean" ||
            o.measurement.kind === "categorical"
          ? String(o.measurement.value)
          : o.quality.status === "missing"
            ? "— Missing"
            : "— Unavailable"}
      {o.quality.status === "invalid" && " · invalid"}
    </span>
  );
}
export function Trend({
  rows,
  metric,
  person,
}: {
  rows: Observation[];
  metric: Metric;
  person?: string;
}) {
  const selected = rows.filter(
    (o) =>
      o.metric === metric &&
      (!person ||
        (o.scope.kind === "astronaut" && o.scope.astronaut_id === person)),
  );
  const data = selected.map((o) => ({
    time: o.timestamp,
    value:
      o.measurement.kind === "numeric" && o.quality.status === "valid"
        ? o.measurement.value
        : null,
  }));
  return (
    <Panel
      title={`${metrics[metric].label} · ${metrics[metric].unit}`}
      action={<Badge>SYNTHETIC</Badge>}
    >
      <p className="chart-note">
        UTC event time · gaps indicate missing or non-valid evidence
      </p>
      {!data.length ? (
        <State kind="empty">Choose a different time range.</State>
      ) : (
        <>
          <div
            className="chart"
            role="img"
            aria-label={`${metrics[metric].label} synthetic trend, ${data.filter((d) => d.value === null).length} gaps. Values available in Data Explorer.`}
          >
            <ResponsiveContainer
              width="100%"
              height="100%"
              initialDimension={{ width: 600, height: 200 }}
            >
              <LineChart
                data={data}
                margin={{ top: 20, right: 20, bottom: 0, left: -12 }}
              >
                <CartesianGrid
                  stroke="#233146"
                  strokeDasharray="3 5"
                  vertical={false}
                />
                <XAxis
                  dataKey="time"
                  tickFormatter={clock}
                  minTickGap={45}
                  stroke="#8293ac"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  stroke="#8293ac"
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  labelFormatter={(v) => utc(String(v))}
                  formatter={(v) => [
                    `${v} ${metrics[metric].unit}`,
                    metrics[metric].label,
                  ]}
                  contentStyle={{
                    background: "#101c2e",
                    border: "1px solid #32465e",
                    borderRadius: 8,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#3bdbed"
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <Link className="text-link" to={`/data-explorer?metric=${metric}`}>
            Inspect chart evidence <ArrowUpRight size={14} />
          </Link>
        </>
      )}
    </Panel>
  );
}
export function SourceNote() {
  return (
    <div className="source-note">
      <Database size={15} />
      <span>
        Deterministic synthetic demonstration · fixed at 13 Nov 2026, 12:00 UTC
        · no live telemetry or AI connection
      </span>
    </div>
  );
}
export function PageIntro({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <header className="page-intro">
      <div className="eyebrow">
        <Activity size={13} />
        {eyebrow}
      </div>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}
