import { z } from "zod";
import { observationSchema } from "./observation";
import { investigationSchema } from "./investigation";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
const anchor = z.strictObject({
  sample_id: id,
  episode_id: id,
  mission_id: id,
  astronaut_id: id,
  spacecraft_id: id,
  compartment_id: id,
  timestamp: z.iso.datetime({ offset: true }),
});
export const apiPresetSchema = z.strictObject({
  title: z.string(),
  current: anchor,
  reference: anchor,
});
export type ApiPreset = z.infer<typeof apiPresetSchema>;
const envelope = {
  api_version: z.literal("1.0.0"),
  source: z.literal("configured_synthetic"),
};
export const contextsSchema = z.strictObject({
  ...envelope,
  presets: z.array(apiPresetSchema),
});
export const pageSchema = z.strictObject({
  ...envelope,
  items: z.array(observationSchema),
  total: z.number().int().nonnegative().max(10000),
  limit: z.number().int().min(1).max(100),
  offset: z.number().int().nonnegative().max(10000),
});
export const investigationResponseSchema = z.strictObject({
  ...envelope,
  result: investigationSchema,
});
