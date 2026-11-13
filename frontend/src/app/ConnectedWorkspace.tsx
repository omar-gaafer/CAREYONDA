import { useMemo, useState } from "react";
import { App } from "./App";
import { createHttpRepositories } from "../infrastructure/http";
import { State } from "../shared/ui";
export function ConnectedWorkspace({
  apiUrl = "http://127.0.0.1:8000",
}: {
  apiUrl?: string;
}) {
  const [mode, setMode] = useState<"fixture" | "api">("fixture");
  const connection = useMemo(() => {
    try {
      return { repositories: createHttpRepositories(apiUrl), error: false };
    } catch {
      return { repositories: undefined, error: true };
    }
  }, [apiUrl]);
  if (mode === "api" && connection.error)
    return (
      <main>
        <State kind="error">
          Invalid local API URL. Use a credential-free loopback HTTP origin.
        </State>
        <button onClick={() => setMode("fixture")}>Select fixture mode</button>
      </main>
    );
  return (
    <App
      key={mode}
      modelAApiUrl={apiUrl}
      repository={
        mode === "api" ? connection.repositories?.observations : undefined
      }
      investigationRepository={
        mode === "api" ? connection.repositories?.investigations : undefined
      }
      dataMode={mode}
      onModeChange={setMode}
    />
  );
}
