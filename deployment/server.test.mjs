import { test } from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, writeFile, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";
import { createDemoServer, loadBundle } from "./server.mjs";
const files = new Map([
  [
    "/index.html",
    {
      body: Buffer.from("<div>synthetic public demo</div>"),
      type: "text/html",
    },
  ],
  [
    "/assets/a.js",
    { body: Buffer.from("console.log('synthetic')"), type: "text/javascript" },
  ],
]);
async function fixture(t, options) {
  const server = createDemoServer(files, options);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => {
    server.closeAllConnections();
    server.close();
  });
  return `http://127.0.0.1:${server.address().port}`;
}
test("root, direct routes, refresh and assets work", async (t) => {
  const base = await fixture(t);
  for (const path of [
    "/",
    "/overview",
    "/environment",
    "/model-c",
    "/ai-intelligence",
    "/data-explorer",
    "/incidents",
    "/health",
  ]) {
    const response = await fetch(base + path);
    assert.equal(response.status, 200);
    assert.match(await response.text(), /synthetic/);
  }
  assert.equal(
    (await fetch(base + "/assets/a.js", { headers: { Origin: base } })).status,
    200,
  );
  assert.equal(
    (await fetch(base + "/overview", { method: "HEAD" })).status,
    200,
  );
});
test("health and capabilities describe public isolation", async (t) => {
  const base = await fixture(t);
  assert.equal(
    (await (await fetch(base + "/api/v1/health")).json()).status,
    "ok",
  );
  const c = await (await fetch(base + "/api/v1/capabilities")).json();
  assert.equal(c.authentication, "none_public_synthetic_only");
  assert.equal(c.isolation, "no_research_backend");
  assert.equal(
    c.capabilities.find((x) => x.name === "model_b").availability,
    "unassessed",
  );
  assert.equal(
    c.capabilities.find((x) => x.name === "model_a").availability,
    "unavailable",
  );
});
test("research APIs, filesystem, secrets and artifacts are unreachable", async (t) => {
  const base = await fixture(t);
  for (const path of [
    "/openapi.json",
    "/api/v1/observations",
    "/api/v1/contexts",
    "/api/v1/investigations",
    "/api/v1/model-c/local-assessments",
    "/api/v1/environmental/anomaly-context",
    "/api/v1/environmental/authorized-samples",
    "/.env",
    "/.git/config",
    "/backend/app/main.py",
    "/artifacts/model.joblib",
    "/datasets/raw/nasa.csv",
    "/assets/missing.js",
  ]) {
    assert.equal((await fetch(base + path)).status, 404, path);
  }
  for (const path of [
    "/api/v1/investigations",
    "/api/v1/model-c/local-assessments",
    "/api/v1/environmental/anomaly-context",
  ]) {
    assert.equal(
      (await fetch(base + path, { method: "POST", body: "{}" })).status,
      405,
    );
  }
});
test("bodies, cross-origin reads and excessive URLs reject", async (t) => {
  const base = await fixture(t);
  assert.equal(
    (
      await fetch(base + "/api/v1/health", {
        headers: { Origin: "https://other.example" },
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await fetch(base + "/api/v1/health", {
        headers: { "Sec-Fetch-Site": "cross-site" },
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await fetch(base + "/overview", {
        headers: {
          "Sec-Fetch-Site": "cross-site",
          "Sec-Fetch-Dest": "document",
        },
      })
    ).status,
    200,
  );
  assert.equal((await fetch(base + "/" + "x".repeat(2100))).status, 414);
  assert.equal(
    (await fetch(base + "/", { method: "POST", body: "x".repeat(20000) }))
      .status,
    405,
  );
});
test("rate limiting is bounded and recovers", async (t) => {
  let tick = 0;
  const base = await fixture(t, {
    maxRequests: 2,
    windowMs: 1000,
    now: () => tick,
  });
  assert.equal((await fetch(base)).status, 200);
  assert.equal((await fetch(base)).status, 200);
  const limited = await fetch(base);
  assert.equal(limited.status, 429);
  assert.equal(limited.headers.get("Retry-After"), "1");
  tick = 1001;
  assert.equal((await fetch(base)).status, 200);
});
test("headers prohibit embedding, third parties and sniffing", async (t) => {
  const r = await fetch(await fixture(t));
  assert.equal(r.headers.get("X-Frame-Options"), "DENY");
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), null);
  assert.match(r.headers.get("Content-Security-Policy"), /connect-src 'self'/);
  assert.equal(r.headers.get("X-Content-Type-Options"), "nosniff");
  assert.ok(r.headers.get("X-Correlation-ID"));
});
test("bundle requires explicit public marker and rejects private symlinks", async () => {
  const root = await mkdtemp(tmpdir() + "/careyonda-public-test-");
  const url = pathToFileURL(root + "/");
  await writeFile(
    root + "/manifest.json",
    JSON.stringify({ mode: "local", assets: [] }),
  );
  await assert.rejects(loadBundle(url), /Public demo build required/);
  await writeFile(
    root + "/manifest.json",
    JSON.stringify({
      mode: "public_synthetic_only",
      assets: ["../private.joblib"],
    }),
  );
  await assert.rejects(loadBundle(url), /Invalid asset manifest/);
  const outside = await mkdtemp(tmpdir() + "/careyonda-outside-");
  await writeFile(outside + "/private", "not public");
  await writeFile(
    root + "/manifest.json",
    JSON.stringify({ mode: "public_synthetic_only", assets: [] }),
  );
  await symlink(outside + "/private", root + "/index.html");
  await assert.rejects(loadBundle(url), /Asset outside public bundle/);
});
