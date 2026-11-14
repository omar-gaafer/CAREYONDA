import { useEffect, useMemo, useRef, useState } from "react";
import type { Capabilities } from "../contracts/capabilities";
import {
  ApiFailure,
  createCapabilitiesClient,
  type ApiFailureKind,
} from "../infrastructure/capabilities";
export type CapabilityState =
  | { status: "loading" }
  | {
      status: "error";
      kind: ApiFailureKind;
      previousSnapshotInvalidated: boolean;
    }
  | { status: "ready"; data: Capabilities; retrievedAt: string };
export function useCapabilities(apiUrl: string) {
  const client = useMemo(() => {
    try {
      return createCapabilitiesClient(apiUrl);
    } catch {
      return null;
    }
  }, [apiUrl]);
  const [state, setState] = useState<CapabilityState>({ status: "loading" });
  const hadSnapshot = useRef(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const previousSnapshotInvalidated = hadSnapshot.current;
    setState({ status: "loading" });
    if (!client) {
      setState({
        status: "error",
        kind: "configuration",
        previousSnapshotInvalidated,
      });
      return () => controller.abort();
    }
    client
      .read(controller.signal)
      .then((data) => {
        if (active) {
          hadSnapshot.current = true;
          setState({
            status: "ready",
            data,
            retrievedAt: new Date().toISOString(),
          });
        }
      })
      .catch((error: unknown) => {
        if (active)
          setState({
            status: "error",
            kind: error instanceof ApiFailure ? error.kind : "unavailable",
            previousSnapshotInvalidated,
          });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [client, attempt]);
  return { state, refresh: () => setAttempt((n) => n + 1) };
}
