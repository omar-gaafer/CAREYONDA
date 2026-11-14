import { z } from "zod";
const id = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
/** Mirrors the current backend capability contract; no implied auth upgrade. */
export const capabilitiesSchema = z.strictObject({
  api_version: z.literal("1.0.0"),
  authentication: z.literal("none_local_only"),
  capabilities: z
    .array(
      z.strictObject({
        name: id,
        availability: z.enum([
          "available",
          "simulation_only",
          "not_implemented",
          "unavailable",
        ]),
        medically_validated: z.literal(false),
      }),
    )
    .superRefine((items, ctx) => {
      if (new Set(items.map((c) => c.name)).size !== items.length)
        ctx.addIssue({
          code: "custom",
          message: "Duplicate capability identity",
        });
    }),
});
export type Capabilities = z.infer<typeof capabilitiesSchema>;
