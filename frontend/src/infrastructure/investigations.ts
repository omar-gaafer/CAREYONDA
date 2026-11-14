import type { ApiPreset } from "../contracts/api";
export interface InvestigationRepository {
  list(): Promise<unknown>;
  presets?(): Promise<ApiPreset[]>;
  submit?(preset: ApiPreset): Promise<unknown>;
}
