import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import data from "./fixtures/investigations.json";
import { createHttpRepositories, type Fetcher } from "./http";
import { ConnectedWorkspace } from "../app/ConnectedWorkspace";
const rows = data.flatMap<unknown>((c) => c.observations);
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function server(): Fetcher {
  return vi.fn(async (input, init) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith("/contexts"))
      return response({
        api_version: "1.0.0",
        source: "configured_synthetic",
        presets: data.map((c) => ({
          title: c.title,
          current: c.context,
          reference: c.reference_context,
        })),
      });
    if (url.pathname.endsWith("/investigations")) {
      const body = JSON.parse(String(init?.body));
      const item = data.find(
        (c) => c.context.sample_id === body.current.sample_id,
      )!;
      return response({
        api_version: "1.0.0",
        source: "configured_synthetic",
        result: item.result,
      });
    }
    const offset = Number(url.searchParams.get("offset") ?? 0);
    return response({
      api_version: "1.0.0",
      source: "configured_synthetic",
      items: rows.slice(offset, offset + 100),
      total: rows.length,
      limit: 100,
      offset,
    });
  });
}
afterEach(() => {
  vi.unstubAllGlobals();
});
function mount(path = "/ai-intelligence") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ConnectedWorkspace />
    </MemoryRouter>,
  );
}
describe("local HTTP integration", () => {
  it("loads bounded pages and submits existing M2 contracts", async () => {
    const mock = server();
    const repo = createHttpRepositories("http://127.0.0.1:8000", mock);
    expect(await repo.observations.list()).toHaveLength(145);
    const presets = await repo.investigations.presets!();
    const result = await repo.investigations.submit!(presets[0]);
    expect(result).toMatchObject({
      origin: "synthetic_api",
      result: { status: "ranked", safety_status: "not_evaluated" },
    });
    expect(mock).toHaveBeenCalledWith(
      expect.stringContaining("/investigations"),
      expect.objectContaining({ method: "POST", credentials: "omit" }),
    );
  });
  it.each([
    "https://remote.example",
    "http://remote.example",
    "http://user:secret@localhost:8000",
    "http://localhost:8000/private",
  ])("rejects non-local or credentialed configuration %s", (url) => {
    expect(() => createHttpRepositories(url)).toThrow();
  });
  it.each(["version", "malformed", "unavailable"])(
    "rejects %s responses without fixture fallback",
    async (kind) => {
      const mock: Fetcher = async () =>
        kind === "unavailable"
          ? response({}, 503)
          : kind === "version"
            ? response({ api_version: "9.0.0" })
            : response({ broken: true });
      await expect(
        createHttpRepositories(
          "http://localhost:8000",
          mock,
        ).observations.list(),
      ).rejects.toThrow();
    },
  );
  it("preserves fixture mode then loads API observations and inspects evidence", async () => {
    const mock = server();
    vi.stubGlobal("fetch", mock);
    mount("/data-explorer");
    await screen.findByRole("table");
    expect(mock).not.toHaveBeenCalled();
    await userEvent.selectOptions(screen.getByLabelText("Data source"), "api");
    await screen.findByText("145 observations · synthetic");
    await userEvent.selectOptions(screen.getByLabelText("Crew"), "crew-02");
    expect(screen.getByText("72 observations · synthetic")).toBeInTheDocument();
    await userEvent.click(
      screen.getAllByRole("button", { name: /Inspect / })[0],
    );
    expect(
      within(
        screen.getByRole("region", { name: "Evidence details" }),
      ).getByText("simulated / phase2-fixture"),
    ).toBeInTheDocument();
  });
  it("submits through API mode and renders exact safety, evidence and abstention", async () => {
    vi.stubGlobal("fetch", server());
    mount();
    await screen.findByRole("heading", {
      level: 1,
      name: "AI Health Intelligence",
    });
    await userEvent.selectOptions(screen.getByLabelText("Data source"), "api");
    await screen.findByRole("button", { name: "Submit investigation" });
    await userEvent.click(
      screen.getByRole("button", { name: "Submit investigation" }),
    );
    await screen.findByText("PATTERN SELECTED");
    expect(screen.getByText("not_evaluated")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Crew"), "crew-02");
    await userEvent.click(
      screen.getByRole("button", { name: "Submit investigation" }),
    );
    expect(await screen.findByText("ABSTAINED")).toBeInTheDocument();
  });
  it("shows a newly submitted competing result rather than an earlier selection", async () => {
    vi.stubGlobal("fetch", server());
    mount();
    await screen.findByRole("heading", {
      level: 1,
      name: "AI Health Intelligence",
    });
    await userEvent.selectOptions(screen.getByLabelText("Data source"), "api");
    await userEvent.click(
      await screen.findByRole("button", { name: "Submit investigation" }),
    );
    await screen.findByText("PATTERN SELECTED");
    await userEvent.selectOptions(
      screen.getByLabelText("Configured synthetic windows"),
      data[2].context.sample_id,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Submit investigation" }),
    );
    expect(await screen.findByText("ABSTAINED")).toBeInTheDocument();
    expect(screen.queryByText("PATTERN SELECTED")).not.toBeInTheDocument();
  });
  it("exposes API loss and allows explicit return to fixtures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("connection refused")),
    );
    mount("/data-explorer");
    await screen.findByRole("table");
    await userEvent.selectOptions(screen.getByLabelText("Data source"), "api");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "could not be loaded",
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Data source")).toHaveValue("api");
    await userEvent.selectOptions(
      screen.getByLabelText("Data source"),
      "fixture",
    );
    expect(await screen.findByRole("table")).toBeInTheDocument();
  });
  it("rejects truncated pagination rather than rendering partial evidence", async () => {
    const mock: Fetcher = async () =>
      response({
        api_version: "1.0.0",
        source: "configured_synthetic",
        items: [],
        total: 145,
        limit: 100,
        offset: 0,
      });
    await expect(
      createHttpRepositories("http://localhost:8000", mock).observations.list(),
    ).rejects.toThrow();
  });
});
