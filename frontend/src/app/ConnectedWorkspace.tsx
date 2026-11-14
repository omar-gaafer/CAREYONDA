import { App } from "./App";
/** Production composition: API discovery only; no fixture or demo mode. */
export function ConnectedWorkspace({
  apiUrl = "http://127.0.0.1:8000",
  enableSyntheticViewer = false,
}: {
  apiUrl?: string;
  enableSyntheticViewer?: boolean;
}) {
  return (
    <App
      key={apiUrl}
      apiUrl={apiUrl}
      enableSyntheticViewer={enableSyntheticViewer}
    />
  );
}
