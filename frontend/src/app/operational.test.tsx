import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConnectedWorkspace } from "./ConnectedWorkspace";
import { modules } from "./modules";
import { capabilitiesSchema } from "../contracts/capabilities";
import { createCapabilitiesClient } from "../infrastructure/capabilities";
const capabilities = {
  api_version: "1.0.0",
  authentication: "none_local_only",
  capabilities: [
    {
      name: "observation_contract_validation",
      availability: "available",
      medically_validated: false,
    },
    {
      name: "observations",
      availability: "simulation_only",
      medically_validated: false,
    },
    {
      name: "m2_reasoning",
      availability: "simulation_only",
      medically_validated: false,
    },
    {
      name: "trained_models",
      availability: "not_implemented",
      medically_validated: false,
    },
  ],
};
const response = (body: unknown = capabilities, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function mount(path = "/overview", apiUrl?: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ConnectedWorkspace apiUrl={apiUrl} />
    </MemoryRouter>,
  );
}
afterEach(() => vi.unstubAllGlobals());
describe("API-only operational workspace", () => {
  it.each(modules)(
    "keeps $path navigable without requesting simulation telemetry",
    async (module) => {
      const fetcher = vi.fn(
        async (_input: RequestInfo | URL, _init?: RequestInit) => response(),
      );
      vi.stubGlobal("fetch", fetcher);
      mount(module.path);
      await screen.findByText(/Authentication: none/);
      expect(
        screen.getByRole("heading", { level: 1, name: module.title }),
      ).toBeInTheDocument();
      expect(document.title).toBe(`${module.title} · CAREYONDA`);
      expect(fetcher).toHaveBeenCalledTimes(1);
      expect(String(fetcher.mock.calls[0]?.[0])).toContain(
        "/api/v1/capabilities",
      );
      expect(screen.queryByLabelText("Data source")).not.toBeInTheDocument();
      expect(screen.getByLabelText("Crew")).toBeDisabled();
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(screen.queryByText("Alex Morgan")).not.toBeInTheDocument();
      expect(
        within(
          screen.getByRole("navigation", { name: "Workspace modules" }),
        ).getAllByRole("link"),
      ).toHaveLength(12);
      expect(screen.getByText(/Safety not evaluated/)).not.toBeVisible();
      expect(screen.queryByText("API ONLY")).not.toBeInTheDocument();
      const details = screen.getByText("Technical details").closest("details")!;
      expect(details).not.toHaveAttribute("open");
      await userEvent.click(within(details).getByText("Technical details"));
      expect(screen.getByText(/Safety not evaluated/)).toBeVisible();
    },
  );
  it("redirects the root and reports unavailable context without invented mission time", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response()),
    );
    mount("/");
    await screen.findByRole("heading", {
      name: "Mission Dashboard",
      level: 1,
    });
    expect(
      await screen.findByText("No mission data available."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/12h 00m/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ARES-07/)).not.toBeInTheDocument();
  });
  it.each(["disconnected", "denied", "version", "malformed", "service"])(
    "fails safely for %s without leaking response details",
    async (kind) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => {
          if (kind === "disconnected")
            throw new Error("private patient data must not be echoed");
          if (kind === "denied")
            return response({ secret: "private patient" }, 403);
          if (kind === "version")
            return response({ ...capabilities, api_version: "9.0.0" });
          if (kind === "service") return response({}, 503);
          return response({ private: "private patient" });
        }),
      );
      mount("/health");
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(
        kind === "denied"
          ? "Access unavailable"
          : kind === "disconnected"
            ? "Connection unavailable"
            : kind === "service"
              ? "Connection unavailable"
              : "Unable to load results",
      );
      expect(document.body.textContent).not.toContain("private patient");
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Data source")).not.toBeInTheDocument();
    },
  );
  it("shows no advertised capabilities for an empty backend catalog", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response({ ...capabilities, capabilities: [] })),
    );
    mount();
    expect(
      await screen.findByText("No capabilities advertised"),
    ).toBeInTheDocument();
  });
  it("does not mistake an available component for an authorized measured-data contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response({
          ...capabilities,
          capabilities: capabilities.capabilities.map((c) => ({
            ...c,
            availability: "available",
          })),
        }),
      ),
    );
    mount("/data-explorer");
    expect(
      await screen.findByText(
        /measured evidence requires a separately reviewed backend contract/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("invalidates stale metadata after a failed refresh and recovers on retry", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(response())
      .mockRejectedValueOnce(new Error("unreachable"))
      .mockResolvedValueOnce(response());
    vi.stubGlobal("fetch", fetcher);
    mount();
    await screen.findByText("Service capabilities");
    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "no longer current",
    );
    expect(screen.queryByText("Service capabilities")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Service capabilities")).toBeInTheDocument();
  });
  it("shows a real pending discovery state, never synthetic success", async () => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    mount("/analytics");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(
      screen.queryByText("Capability snapshot loaded"),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();
  });
  it("preserves brand collapse, mobile keyboard focus and route focus", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response()),
    );
    mount();
    await screen.findByText("Service capabilities");
    const logo = within(screen.getByLabelText("Mission navigation")).getByRole(
      "img",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    );
    expect(logo).toHaveAttribute(
      "src",
      "/brand/careyonda-icon-transparent.png",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Open navigation" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Mission navigation" });
    expect(
      within(dialog).getByRole("button", { name: "Close navigation" }),
    ).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(within(dialog).getAllByRole("link").at(-1)).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(
      screen.getByRole("button", { name: "Open navigation" }),
    ).toHaveFocus();
    await userEvent.click(
      screen.getByRole("link", { name: /Health Monitoring/ }),
    );
    await waitFor(() =>
      expect(document.getElementById("main-content")).toHaveFocus(),
    );
  });
  it("shows browser-offline context without claiming loopback failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response()),
    );
    mount();
    await screen.findByText("Service capabilities");
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    fireEvent(window, new Event("offline"));
    expect(
      screen.getByText(/Local services may still be available/),
    ).toBeInTheDocument();
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
    fireEvent(window, new Event("online"));
  });
  it("rejects invalid API configuration without sending a request", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    mount("/health", "https://remote.example");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Connection unavailable",
    );
    expect(fetcher).not.toHaveBeenCalled();
  });
});
describe("capability boundary", () => {
  it.each(["version", "auth", "medical", "availability", "duplicate"])(
    "rejects unsupported %s declarations",
    (kind) => {
      const payload = structuredClone(capabilities);
      if (kind === "version") payload.api_version = "2.0.0";
      if (kind === "auth") payload.authentication = "authorized";
      if (kind === "medical")
        payload.capabilities[0].medically_validated = true;
      if (kind === "availability")
        payload.capabilities[0].availability = "operational";
      if (kind === "duplicate")
        payload.capabilities.push(payload.capabilities[0]);
      expect(() => capabilitiesSchema.parse(payload)).toThrow();
    },
  );
  it("omits credentials, disables cache and refuses redirects", async () => {
    const fetcher = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) => response(),
    );
    await createCapabilitiesClient("http://localhost:8000", fetcher).read(
      new AbortController().signal,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/capabilities",
      expect.objectContaining({
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
      }),
    );
  });
});

it("never writes browser storage during operational discovery or navigation", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => response()),
  );
  const write = vi.spyOn(Storage.prototype, "setItem");
  try {
    mount();
    await screen.findByText("Service capabilities");
    await userEvent.click(screen.getByRole("link", { name: /Crew/ }));
    expect(
      await screen.findByText("No crew data available"),
    ).toBeInTheDocument();
    expect(write).not.toHaveBeenCalled();
  } finally {
    write.mockRestore();
  }
});
