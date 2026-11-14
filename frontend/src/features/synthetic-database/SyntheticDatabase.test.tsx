import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createSyntheticClient,
  pageSchema,
} from "../../infrastructure/synthetic-database";
import { SyntheticDatabase } from "./SyntheticDatabase";
import { ConnectedWorkspace } from "../../app/ConnectedWorkspace";
afterEach(() => vi.unstubAllGlobals());
describe("local synthetic database viewer", () => {
  it("rejects nonlocal API configuration", () => {
    expect(() => createSyntheticClient("https://external.invalid")).toThrow();
  });
  it("does not fall back after API failure", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response("private response must not display", { status: 503 }),
    );
    const client = createSyntheticClient("http://127.0.0.1:8110", fetcher);
    await expect(
      client.catalog(new AbortController().signal),
    ).rejects.toThrow();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("rejects wrong sources and oversized pages", () => {
    expect(() =>
      pageSchema.parse({
        api_version: "1.0.0",
        source: "fixture",
        mission_id: "synthetic-mission",
        items: [],
        total: 0,
        limit: 100,
        offset: 0,
        missing: 0,
        suspect: 0,
      }),
    ).toThrow();
    expect(() =>
      pageSchema.parse({
        api_version: "1.0.0",
        source: "synthetic_database",
        mission_id: "synthetic-mission",
        items: [],
        total: 0,
        limit: 101,
        offset: 0,
        missing: 0,
        suspect: 0,
      }),
    ).toThrow();
  });
  it("labels the viewer and sanitizes unavailability", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response("private connection details", { status: 503 }),
      ),
    );
    render(
      <MemoryRouter>
        <SyntheticDatabase apiUrl="http://127.0.0.1:8110" />
      </MemoryRouter>,
    );
    expect(screen.getByText("Synthetic Research Dataset")).toBeInTheDocument();
    expect(screen.getByText("Local PostgreSQL")).toBeInTheDocument();
    expect(
      screen.getByText("Not Live Astronaut Telemetry"),
    ).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No fixture fallback",
    );
    expect(document.body.textContent).not.toContain("private connection");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("does not show a local dataset mode in the default application", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              api_version: "1.0.0",
              authentication: "none_local_only",
              capabilities: [],
            }),
          ),
      ),
    );
    render(
      <MemoryRouter>
        <ConnectedWorkspace />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.queryByText("Loading…")).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("link", { name: /Local Synthetic Data/ }),
    ).not.toBeInTheDocument();
  });
});
