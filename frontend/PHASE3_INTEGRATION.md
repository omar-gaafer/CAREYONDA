# Phase 3 — local API integration

Start the backend using [the API reference](../docs/api/LOCAL_API_V1.md). From `frontend/`, use Node 22.12–24.x (tested Node 24.21.0):

```sh
npm ci
npm run dev -- --port 5173 --strictPort
```

The default API origin is `http://127.0.0.1:8000`. To change it, provision `VITE_API_URL` in the shell/build environment or a local ignored `.env.local` using `.env.example` as documentation. Restart Vite after changes. Only credential-free HTTP loopback origins on `localhost` or `127.0.0.1` are accepted; paths, query strings, remote hosts and credentials are rejected. No key or cookie is used. Environment values are public build configuration, not secret storage. Keep the frontend on one of the API's documented CORS origins.

## Demonstrate the connection

1. Start backend and frontend locally. Open the frontend, which defaults to **Offline fixtures**.
2. Use **Data source → Local API · synthetic**. The mode label and source footer change. API mode loads 145 configured synthetic observations in bounded pages and validated context presets. It does not load or auto-submit precomputed fixture investigations.
3. Open Data Explorer to inspect quality, original values, evidence IDs, event/ingestion times and provenance. API catalog cases are separate controlled examples, not one continuous real mission; charts retain original observations without adding a claim of consistency or safety.
4. Open AI Health Intelligence. Select configured synthetic windows and click **Submit investigation**. The actual local M2 engine runs through POST `/api/v1/investigations`. The frontend validates the envelope and result, resolves original evidence from the API catalog, and displays the original ranks, explanations, uncertainty and safety status.
5. Choose crew-02/missing evidence or a competing/conflicting preset to see explicit abstention. Each successful submission is retained in memory and is available to the incident review workspace. The newly submitted result is selected by default.
6. Stop the backend. New API requests expose a connection/submission error; there is no fixture fallback. A failed submission can leave an earlier successful result visible with an explicit error saying it is earlier data. Previously loaded observations remain memory snapshots until retry/remount; there is no connection polling or claim of continual backend availability.
7. Select **Offline fixtures** explicitly to return to the original 480-observation demonstration and precomputed Phase 2 cases. Changing source remounts the workspace and clears session notes/statuses/results so records from different modes are not mixed.

## Contract mapping additions

- `contracts/api.ts` validates API version `1.0.0`, source `configured_synthetic`, complete context presets, bounded observation pages and nested original M2 results. Observation detail continues to use the existing `Observation` schema.
- `infrastructure/http.ts` supplies typed `ObservationRepository` and `InvestigationRepository` adapters. It verifies pagination completeness/consistency, unique evidence, synthetic origin, supported versions and original domain payloads. Requests omit credentials, reject redirects, disable cache and time out after ten seconds.
- `InvestigationRepository` optionally exposes context presets and a submit operation. Fixture implementations remain unchanged. The application hook owns async submission state; presentation does not implement reasoning rules.
- The existing frontend synthetic envelope now permits `origin=synthetic_api` alongside `synthetic_precomputed`. Both require original simulated observations. API results are nested unchanged; no frontend ranking is computed. This explicitly reviewed extension is synthetic-only and does not authorize measured health data.
- The incident workflow still has no backend persistence or medical meaning. Timeline review/evaluation timestamps remain explicitly synthetic storyboards, not actual API execution/audit timing.
- `ConnectedWorkspace` composes the selected adapters. No mutable global service locator, browser persistence, service worker, credential, telemetry or external data fetch was introduced.

The API currently serves only the nine-metric subset already supported by the frontend. Known but absent metrics produce empty views. NASA data, radiation series, trained models, procedures, authentication and saved investigation retrieval remain unavailable. No cloud/model service is involved; API mode requires a reachable local backend, while fixture mode works with only the local frontend server.

## Verify

```sh
npm run typecheck
npm test
npm run format:check
npm run build
```

See [the M3 report](../docs/api/M3_INTEGRATION_REPORT.md) for executed checks and browser evidence. The earlier [Phase 2 mapping](PHASE2_CONTRACT_MAPPING.md) is the historical contract baseline; this document records the new transport/envelope behavior.
