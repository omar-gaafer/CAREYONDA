import type { ApiPreset } from "../contracts/api";
import data from "./fixtures/investigations.json";
export interface InvestigationRepository {
  list(): Promise<unknown>;
  presets?(): Promise<ApiPreset[]>;
  submit?(preset: ApiPreset): Promise<unknown>;
}
// Precomputed by the unchanged Python engine; never executed in the browser.
export const syntheticInvestigationRepository: InvestigationRepository = {
  async list() {
    return structuredClone(data);
  },
};
