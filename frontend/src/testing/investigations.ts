import type { InvestigationRepository } from "../infrastructure/investigations";
export type { InvestigationRepository } from "../infrastructure/investigations";
import data from "../infrastructure/fixtures/investigations.json";
// Precomputed by the unchanged Python engine; never executed in the browser.
export const syntheticInvestigationRepository: InvestigationRepository = {
  async list() {
    return structuredClone(data);
  },
};
