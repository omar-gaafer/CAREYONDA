import { Link } from "react-router-dom";
import { ArrowRight, Cable, Shield } from "lucide-react";
import { PageIntro, Panel, Badge } from "../../shared/ui";
export function Capability({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <>
      <PageIntro
        eyebrow="CAPABILITY ROADMAP / FUTURE INTEGRATION"
        title={title}
      >
        A reserved workspace for a future CAREYONDA capability.
      </PageIntro>
      <div className="capability-hero">
        <div className="capability-icon">
          <Cable size={38} />
        </div>
        <Badge tone="amber">NOT IMPLEMENTED IN PHASE 1</Badge>
        <h2>Ready for a defined integration boundary</h2>
        <p>{detail}</p>
        <Link className="primary-link" to="/data-explorer">
          Explore available synthetic evidence <ArrowRight size={16} />
        </Link>
      </div>
      <div className="two-columns">
        <Panel title="What is available">
          <p>
            Read-only synthetic observations, shared crew and time filters,
            quality reasons, and traceable provenance.
          </p>
          <Link className="text-link" to="/overview">
            Return to Mission Command Center <ArrowRight size={15} />
          </Link>
        </Panel>
        <Panel title="Before this capability can operate">
          <p>
            Reviewed backend contracts, an authorized implementation milestone,
            deterministic tests, and explicit data and safety limitations.
          </p>
          <div className="panel-foot">
            <Shield size={16} /> No live AI or operational safety determination.
          </div>
        </Panel>
      </div>
    </>
  );
}
