/** Historical fixture wrapper retained for isolated tests; production imports the core. */
import fixture from "../../infrastructure/fixtures/model-a-simulated.json";
import { ModelAContextPanel } from "./ModelAContextPanel";
import type { ModelAClient } from "../../infrastructure/model-a";
export function ModelAPanel(props: {
  mode: "fixture" | "api";
  apiUrl?: string;
  client?: ModelAClient;
}) {
  return <ModelAContextPanel {...props} fixture={fixture} />;
}
