import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../testing/ResearchWorkspace";
import { modules } from "./modules";
import {
  createFixtures,
  type ObservationRepository,
} from "../testing/observations";
function mount(path = "/", repository?: ObservationRepository) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App repository={repository} />
    </MemoryRouter>,
  );
}
describe("mission workspace", () => {
  it.each(modules)("renders $path and its honest module title", async (m) => {
    mount(m.path);
    expect(
      await screen.findByRole("heading", { level: 1, name: m.title }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Deterministic synthetic demonstration/),
    ).toBeInTheDocument();
    if (!m.phase1 && !m.phase2)
      expect(
        screen.getByText("NOT IMPLEMENTED IN PHASE 1"),
      ).toBeInTheDocument();
  });
  it("redirects root and navigates using the sidebar", async () => {
    mount();
    await screen.findByRole("heading", {
      level: 1,
      name: "Mission Dashboard",
    });
    await userEvent.click(screen.getByRole("link", { name: /Data Explorer/ }));
    expect(
      await screen.findByRole("heading", { level: 1, name: "Data Explorer" }),
    ).toBeInTheDocument();
  });
  it("filters crew and time, and exposes original evidence provenance", async () => {
    mount("/data-explorer");
    await screen.findByRole("heading", { name: "Data Explorer", level: 1 });
    await userEvent.selectOptions(screen.getByLabelText("Crew"), "crew-02");
    await userEvent.selectOptions(screen.getByLabelText("Time range"), "6");
    expect(screen.getByText("78 observations · synthetic")).toBeInTheDocument();
    await userEvent.click(
      screen.getAllByRole("button", { name: /Inspect syn-/ })[0],
    );
    const details = screen.getByRole("region", { name: "Evidence details" });
    expect(within(details).getByText("Event time")).toBeInTheDocument();
    expect(within(details).getByText("Ingestion time")).toBeInTheDocument();
    expect(
      within(details).getByText("simulated / phase1-fixture"),
    ).toBeInTheDocument();
    await userEvent.click(
      within(details).getByRole("button", { name: "Close details" }),
    );
    expect(
      screen.queryByRole("region", { name: "Evidence details" }),
    ).not.toBeInTheDocument();
  });
  it("shows an empty state for a quality with no evidence", async () => {
    mount("/data-explorer?quality=unavailable");
    expect(
      await screen.findByText("No matching observations"),
    ).toBeInTheDocument();
  });
  it("retains invalid values and reason codes in the explorer", async () => {
    mount("/data-explorer?quality=invalid");
    expect(await screen.findByText("112 % · invalid")).toBeInTheDocument();
    expect(screen.getByText("physical_domain_violation")).toBeInTheDocument();
  });
  it("handles loading, repository failure and retry without leaking errors", async () => {
    let calls = 0;
    mount("/", {
      async list() {
        if (++calls === 1) throw new Error("private payload");
        return createFixtures();
      },
    });
    expect(screen.getByText("Loading observations")).toBeInTheDocument();
    await screen.findByRole("alert");
    expect(screen.queryByText("private payload")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Mission Dashboard",
      }),
    ).toBeInTheDocument();
  });
  it("rejects malformed adapter responses", async () => {
    const repository = {
      async list() {
        return [{ ...createFixtures()[0], schema_version: "bad" }];
      },
    };
    mount("/", repository);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "failed contract validation",
    );
  });
  it("keeps local observations available when browser reports offline", async () => {
    mount("/data-explorer");
    await screen.findByRole("heading", { name: "Data Explorer", level: 1 });
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    fireEvent(window, new Event("offline"));
    expect(screen.getByText(/Browser reports offline/)).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
    fireEvent(window, new Event("online"));
    await waitFor(() =>
      expect(
        screen.queryByText(/Browser reports offline/),
      ).not.toBeInTheDocument(),
    );
  });
  it("exposes gaps for missing heart-rate evidence", async () => {
    mount("/health");
    await screen.findByRole("heading", { name: "Health Monitoring", level: 1 });
    expect(
      screen.getAllByRole("img", {
        name: /Heart rate synthetic trend, 1 gaps/,
      }),
    ).toHaveLength(3);
  });
  it("paginates evidence without losing the selected quality context", async () => {
    mount("/data-explorer");
    await screen.findByRole("table");
    const firstId = screen
      .getAllByRole("button", { name: /Inspect syn-/ })[0]
      .getAttribute("aria-label");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Page 2 of 32")).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("button", { name: /Inspect syn-/ })[0]
        .getAttribute("aria-label"),
    ).not.toBe(firstId);
  });
  it("shows absence reasons without inventing a measurement", async () => {
    mount("/data-explorer?quality=missing");
    await screen.findByText("3 observations · synthetic");
    await userEvent.click(
      screen.getAllByRole("button", { name: /Inspect syn-/ })[0],
    );
    expect(
      within(
        screen.getByRole("region", { name: "Evidence details" }),
      ).getByText("not_received"),
    ).toBeInTheDocument();
  });
  it("closes the mobile navigation with Escape and restores its trigger focus", async () => {
    mount("/assistant");
    await screen.findByRole("heading", {
      name: "AI Assistant",
      level: 1,
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Open navigation" }),
    );
    expect(
      screen.getByRole("dialog", { name: "Mission navigation" }),
    ).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Open navigation" }),
    ).toHaveFocus();
  });
  it("supports keyboard sidebar navigation and collapse controls", async () => {
    mount("/assistant");
    await screen.findByRole("heading", {
      name: "AI Assistant",
      level: 1,
    });
    const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
    toggle.focus();
    await userEvent.keyboard("{Enter}");
    expect(
      screen.getByRole("button", { name: "Expand sidebar" }),
    ).toHaveAttribute("aria-expanded", "false");
    screen.getByRole("link", { name: /Health Monitoring/ }).focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByRole("heading", {
        name: "Health Monitoring",
        level: 1,
      }),
    ).toBeInTheDocument();
  });
});
