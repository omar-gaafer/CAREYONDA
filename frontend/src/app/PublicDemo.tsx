import { Badge, Panel, PageIntro } from "../shared/ui";

export function PublicDemoNotice() {
  return (
    <div className="notice" role="note">
      <Badge>PUBLIC SYNTHETIC DEMO</Badge>
      <p>
        All observations and M2 examples are synthetic, precomputed research
        fixtures — not live telemetry. No research API or personal-data
        submission is enabled.
      </p>
      <p>
        Model A: unavailable. Model B: unassessed, canonical policy pending.
        Model C and Hybrid execution remain private research workflows. No
        medical or safety determination.
      </p>
    </div>
  );
}
export function PublicModelA() {
  return (
    <Panel title="Model A · Environmental statistical context">
      <Badge tone="amber">MODEL UNAVAILABLE</Badge>
      <p>
        No trained artifact, authorized sample catalog or acquisition receipts
        are provisioned in this public demo. No scoring or fixture fallback is
        performed.
      </p>
    </Panel>
  );
}
export function PrivateModelC() {
  return (
    <>
      <PageIntro
        eyebrow="PRIVATE RESEARCH WORKFLOW"
        title="Sleep/Fatigue Research Monitor"
      >
        Local assessment is intentionally unavailable in the public demo.
      </PageIntro>
      <Panel title="No public self-report submission">
        <p>
          The verified local Model C workflow remains available to the research
          team. This deployment accepts no health entries and produces no
          substituted assessment.
        </p>
        <p>
          It is a sleep/fatigue research monitor, not a validated isolation or
          confinement detector.
        </p>
      </Panel>
    </>
  );
}
