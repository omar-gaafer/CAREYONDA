import {
  capabilitiesSchema,
  type Capabilities,
} from "../contracts/capabilities";

export type ApiFailureKind =
  | "disconnected"
  | "permission_denied"
  | "contract_mismatch"
  | "unavailable"
  | "configuration";
export class ApiFailure extends Error {
  constructor(public readonly kind: ApiFailureKind) {
    super(kind);
  }
}
export interface CapabilitiesClient {
  read(signal: AbortSignal): Promise<Capabilities>;
}
export function createCapabilitiesClient(
  baseUrl: string,
  fetcher: typeof fetch = (...args) => fetch(...args),
): CapabilitiesClient {
  let url: URL;
  try {
    url = new URL(baseUrl);
  } catch {
    throw new ApiFailure("configuration");
  }
  if (
    url.protocol !== "http:" ||
    !["127.0.0.1", "localhost"].includes(url.hostname) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new ApiFailure("configuration");
  return {
    async read(signal) {
      let response: Response;
      try {
        response = await fetcher(`${url.origin}/api/v1/capabilities`, {
          credentials: "omit",
          cache: "no-store",
          redirect: "error",
          signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]),
        });
      } catch {
        throw new ApiFailure("disconnected");
      }
      if ([401, 403].includes(response.status))
        throw new ApiFailure("permission_denied");
      if (!response.ok) throw new ApiFailure("unavailable");
      try {
        return capabilitiesSchema.parse(await response.json());
      } catch {
        throw new ApiFailure("contract_mismatch");
      }
    },
  };
}
