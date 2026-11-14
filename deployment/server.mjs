if (Number(process.versions.node.split(".")[0]) !== 24) {
  throw Error("Public deployment requires the tested Node 24 runtime");
}
/** Public synthetic bundle only. Never imports Python or proxies a research API. */
import { createServer } from "node:http";
import { readFile, realpath } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";

const routes = new Set([
  "/",
  "/overview",
  "/health",
  "/environment",
  "/model-c",
  "/data-explorer",
  "/ai-intelligence",
  "/incidents",
  "/assistant",
  "/crew",
  "/analytics",
  "/recommendations",
  "/digital-twin",
  "/reports",
]);
export async function loadBundle(root = new URL("./public/", import.meta.url)) {
  const directory = await realpath(root);
  const manifest = JSON.parse(
    await readFile(new URL("manifest.json", root), "utf8"),
  );
  if (
    manifest.mode !== "public_synthetic_only" ||
    !Array.isArray(manifest.assets) ||
    manifest.assets.length > 64
  )
    throw Error("Public demo build required");
  const files = new Map();
  let size = 0;
  for (const name of [
    "index.html",
    ...manifest.assets.map((name) => {
      if (typeof name !== "string" || !/^[a-zA-Z0-9_-]+\.(js|css)$/.test(name))
        throw Error("Invalid asset manifest");
      return "assets/" + name;
    }),
  ]) {
    const path = await realpath(new URL(name, root));
    if (!path.startsWith(directory + "/"))
      throw Error("Asset outside public bundle");
    const body = await readFile(path);
    size += body.length;
    if (body.length > 2_000_000 || size > 10_000_000)
      throw Error("Bundle exceeds bounds");
    files.set("/" + name, {
      body,
      type: name.endsWith(".js")
        ? "text/javascript"
        : name.endsWith(".css")
          ? "text/css"
          : "text/html",
    });
  }
  return files;
}
export function createDemoServer(
  files,
  { maxRequests = 240, windowMs = 60000, now = Date.now } = {},
) {
  let windowStart = now(),
    requests = 0;
  const server = createServer({ maxHeaderSize: 8192 }, (req, res) => {
    const correlation = randomUUID();
    const headers = {
      "X-Correlation-ID": correlation,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "X-Frame-Options": "DENY",
      "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
      "Content-Security-Policy":
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    };
    function reply(status, body, type = "application/json") {
      res.writeHead(status, {
        ...headers,
        "Content-Type": type,
        "Content-Length": Buffer.byteLength(body),
      });
      res.end(req.method === "HEAD" ? undefined : body);
    }
    const error = (status, code) =>
      reply(
        status,
        JSON.stringify({ error: { code, correlation_id: correlation } }),
      );
    if (now() - windowStart >= windowMs) {
      windowStart = now();
      requests = 0;
    }
    if (++requests > maxRequests) {
      res.setHeader("Retry-After", String(Math.ceil(windowMs / 1000)));
      error(429, "demo_rate_limit");
      return;
    }
    if ((req.url?.length ?? 0) > 2048) {
      error(414, "url_too_long");
      return;
    }
    if (!["GET", "HEAD"].includes(req.method)) {
      headers.Connection = "close";
      error(405, "public_demo_read_only");
      return;
    }
    if (
      req.headers["transfer-encoding"] ||
      (req.headers["content-length"] && req.headers["content-length"] !== "0")
    ) {
      headers.Connection = "close";
      error(413, "body_not_allowed");
      return;
    }
    if (
      (req.headers.origin &&
        ![`http://${req.headers.host}`, `https://${req.headers.host}`].includes(
          req.headers.origin,
        )) ||
      (req.headers["sec-fetch-site"] === "cross-site" &&
        req.headers["sec-fetch-dest"] !== "document")
    ) {
      error(403, "cross_origin_not_allowed");
      return;
    }
    let path;
    try {
      path = new URL(req.url, "http://public.invalid").pathname;
    } catch {
      error(400, "invalid_url");
      return;
    }
    if (path === "/api/v1/health") {
      reply(
        200,
        JSON.stringify({ status: "ok", deployment: "public_synthetic_only" }),
      );
      return;
    }
    if (path === "/api/v1/capabilities") {
      reply(
        200,
        JSON.stringify({
          api_version: "1.0.0",
          authentication: "none_public_synthetic_only",
          isolation: "no_research_backend",
          capabilities: [
            {
              name: "synthetic_dashboard_and_precomputed_m2",
              availability: "simulation_only",
            },
            { name: "model_a", availability: "unavailable" },
            {
              name: "model_b",
              availability: "unassessed",
              reason: "canonical_policy_pending",
            },
            { name: "model_c_public_submission", availability: "unavailable" },
            { name: "hybrid_execution", availability: "unavailable" },
          ],
          medically_validated: false,
        }),
      );
      return;
    }
    if (path === "/favicon.ico") {
      reply(204, "", "image/x-icon");
      return;
    }
    const file = routes.has(path) ? files.get("/index.html") : files.get(path);
    if (
      !file ||
      (path !== "/index.html" &&
        !routes.has(path) &&
        !path.startsWith("/assets/"))
    ) {
      error(404, "not_found");
      return;
    }
    reply(200, file.body, file.type);
  });
  server.headersTimeout = 5000;
  server.requestTimeout = 5000;
  server.timeout = 5000;
  server.keepAliveTimeout = 2000;
  server.maxConnections = 32;
  server.maxRequestsPerSocket = 100;
  return server;
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env.PORT ?? "5000");
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw Error("Invalid assigned port");
  const server = createDemoServer(await loadBundle());
  server.listen(port, "0.0.0.0", () =>
    console.log("CAREYONDA public synthetic demo ready"),
  );
}
