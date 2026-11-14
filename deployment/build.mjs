if (Number(process.versions.node.split(".")[0]) !== 24) {
  throw Error("Public deployment requires the tested Node 24 runtime");
}
import { execFileSync } from "node:child_process";
import { mkdir, copyFile, readdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../", import.meta.url));
const env = { ...process.env, VITE_PUBLIC_DEMO: "true" };
delete env.VITE_API_URL;
execFileSync("npm", ["run", "build"], {
  cwd: root + "frontend",
  env,
  stdio: "inherit",
});
const target = new URL("./public/", import.meta.url);
await mkdir(new URL("assets/", target), { recursive: true });
await copyFile(
  new URL("../frontend/dist/index.html", import.meta.url),
  new URL("index.html", target),
);
const assets = await readdir(
  new URL("../frontend/dist/assets/", import.meta.url),
);
for (const name of assets) {
  if (!/^[a-zA-Z0-9_-]+\.(js|css)$/.test(name))
    throw Error("Unexpected build asset");
  await copyFile(
    new URL("../frontend/dist/assets/" + name, import.meta.url),
    new URL("assets/" + name, target),
  );
}
await writeFile(
  new URL("manifest.json", target),
  JSON.stringify({ mode: "public_synthetic_only", assets }),
);
console.log("Public synthetic-only bundle prepared");
