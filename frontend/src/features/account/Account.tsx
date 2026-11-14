import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { observationSchema } from "../../contracts/observation";
import { Panel, PageIntro } from "../../shared/ui";
const profileSchema = z.strictObject({
  user_id: z.string().uuid(),
  roles: z.array(z.enum(["Admin", "Doctor", "Astronaut"])),
});
export function Account({ apiUrl }: { apiUrl: string }) {
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<z.infer<typeof profileSchema> | null>(
    null,
  );
  const [mission, setMission] = useState("");
  const [astronaut, setAstronaut] = useState("");
  const [message, setMessage] = useState("");
  const [rows, setRows] = useState<unknown[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  function clear(keepProfile = false) {
    generation.current++;
    if (!keepProfile) setProfile(null);
    setRows([]);
    setMessage("");
    setBusy(false);
  }
  async function request(path: string, body?: unknown) {
    const base = new URL(apiUrl);
    if (
      base.protocol !== "http:" ||
      !["127.0.0.1", "localhost"].includes(base.hostname) ||
      base.username ||
      base.password ||
      base.pathname !== "/" ||
      base.search ||
      base.hash
    )
      throw Error("Invalid local API origin");
    const r = await fetch(base.origin + "/api/v1/account" + path, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        Authorization: "Bearer " + token,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10000),
    });
    if (!r.ok)
      throw Error(
        r.status === 503
          ? "Database or authentication unavailable"
          : r.status === 401 || r.status === 403
            ? "Access denied"
            : "Request rejected",
      );
    return r.json() as Promise<unknown>;
  }
  async function run(action: () => Promise<void>) {
    const id = ++generation.current;
    setBusy(true);
    setMessage("");
    try {
      await action();
    } catch (e) {
      if (generation.current === id)
        setMessage(
          e instanceof Error &&
            [
              "Invalid local API origin",
              "Database or authentication unavailable",
              "Access denied",
              "Request rejected",
            ].includes(e.message)
            ? e.message
            : "Request rejected or unsupported contract",
        );
    } finally {
      if (generation.current === id) setBusy(false);
    }
  }
  return (
    <>
      <PageIntro title="Authorized records">
        Optional backend-only persistence. Research views remain separate. No
        client-selected roles or stored browser tokens.
      </PageIntro>
      <Panel title="Verified identity">
        <p>
          Obtain an access token through your configured Supabase Auth sign-in.
          This application verifies it server-side; no local role impersonation
          is supported.
        </p>
        <label>
          Supabase access token
          <input
            aria-label="Supabase access token"
            type="password"
            autoComplete="off"
            value={token}
            onChange={(e) => {
              clear();
              setToken(e.target.value);
            }}
          />
        </label>
        <button
          disabled={busy || !token}
          onClick={() => {
            const id = generation.current + 1;
            void run(async () => {
              const p = profileSchema.parse(await request("/me"));
              if (generation.current === id) setProfile(p);
            });
          }}
        >
          Verify identity
        </button>
        <button
          onClick={() => {
            clear();
            setToken("");
          }}
        >
          Sign out locally
        </button>
        {profile && (
          <p>
            Verified {profile.user_id} · {profile.roles.join(", ")}
          </p>
        )}
      </Panel>
      <Panel title="Assignment-scoped numeric observations">
        <label>
          Mission ID
          <input
            aria-label="Record mission"
            value={mission}
            onChange={(e) => {
              clear(true);
              setMission(e.target.value);
            }}
          />
        </label>
        <label>
          Astronaut ID
          <input
            aria-label="Record astronaut"
            value={astronaut}
            onChange={(e) => {
              clear(true);
              setAstronaut(e.target.value);
            }}
          />
        </label>
        <button
          disabled={busy || !token || !mission || !astronaut}
          onClick={() => {
            const id = generation.current + 1;
            void run(async () => {
              const r = z.array(observationSchema).parse(
                await request(
                  "/observations?" +
                    new URLSearchParams({
                      mission_id: mission,
                      astronaut_id: astronaut,
                    }),
                ),
              );
              if (generation.current === id) setRows(r);
            });
          }}
        >
          Read authorized records
        </button>
        <p>
          Bounded to the earliest 100 supported numeric, non-derived astronaut
          observations. Other evidence types are not represented by this slice.
        </p>
        <pre>{JSON.stringify(rows, null, 2)}</pre>
        <label>
          Validated Observation v1 JSON
          <textarea
            aria-label="Observation JSON"
            value={draft}
            onChange={(e) => {
              clear(true);
              setDraft(e.target.value);
            }}
          />
        </label>
        <button
          disabled={busy || !token || !draft}
          onClick={() => {
            const id = generation.current + 1;
            void run(async () => {
              const observation = observationSchema.parse(JSON.parse(draft));
              await request("/observations", observation);
              if (generation.current === id)
                setMessage("Persisted by the database");
            });
          }}
        >
          Persist observation
        </button>
      </Panel>
      {profile?.roles.includes("Admin") && (
        <Panel title="Admin mission creation">
          <button
            disabled={busy || !mission}
            onClick={() => {
              const id = generation.current + 1;
              void run(async () => {
                await request("/missions", { mission_id: mission });
                if (generation.current === id) setMessage("Mission created");
              });
            }}
          >
            Create mission
          </button>
        </Panel>
      )}
      {busy && <p role="status">Request pending</p>}
      {message && <p role="status">{message}</p>}
    </>
  );
}
