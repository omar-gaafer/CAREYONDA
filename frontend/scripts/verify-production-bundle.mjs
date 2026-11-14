/** Offline build-artifact review; no payloads, credentials or network access. */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
const modules = JSON.parse(
  readFileSync("dist/production-modules.json", "utf8"),
);
if (!modules.includes("src/app/App.tsx"))
  throw new Error("Missing production application entry");
const forbiddenModules =
  /testing\/|fixtures\/|\.(test|spec)\.|features\/(overview|health|environment|incidents|investigations|explorer|capabilities)\//;
if (modules.some((path) => forbiddenModules.test(path)))
  throw new Error("Unreviewed research/test presentation in production graph");
const sentinels = [
  "Alex Morgan",
  "Sam Rivera",
  "Jordan Chen",
  "phase1-fixture",
  "phase2-fixture",
  "deterministic-waveform",
  "SIMULATION ACTIVE",
  "Offline fixtures",
  "ARES-07",
  "synthetic_precomputed",
];
for (const file of readdirSync("dist/assets")) {
  if (!file.endsWith(".js")) continue;
  const text = readFileSync(join("dist/assets", file), "utf8");
  for (const sentinel of sentinels)
    if (text.includes(sentinel))
      throw new Error(
        "Synthetic fixture sentinel leaked into production bundle",
      );
}
console.log(
  `Production bundle reviewed: ${modules.length} source modules; no test modules, fixture data or demo sentinels.`,
);
