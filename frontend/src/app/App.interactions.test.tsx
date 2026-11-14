import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

const capabilities = {
  api_version: "1.0.0",
  authentication: "none_local_only",
  capabilities: [],
};

function mount(path = "/overview") {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify(capabilities), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    ),
  );
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App apiUrl="http://127.0.0.1:8000" />
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("production workspace interactions", () => {
  it("keeps the Mission Dashboard in its previous layout", async () => {
    mount();
    await screen.findByRole("heading", {
      level: 1,
      name: "Mission Dashboard",
    });
    expect(screen.getByText("No mission data available.")).toBeInTheDocument();
    expect(
      screen.getByText("No health observations available."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No environmental observations available."),
    ).toBeInTheDocument();
    expect(screen.getByText("No incident data available.")).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "Workspace modules" }),
    ).not.toBeInTheDocument();
  });

  it("opens the command palette with Ctrl+K, filters pages, and closes with Escape", async () => {
    const user = userEvent.setup();
    mount("/assistant");
    await screen.findByRole("heading", { name: "AI Assistant" });

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const search = await screen.findByRole("searchbox", {
      name: "Search pages",
    });
    await user.type(search, "digital twin");
    expect(
      within(screen.getByRole("dialog")).getByRole("link", {
        name: /Spacecraft Digital Twin/,
      }),
    ).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(
      screen.queryByRole("dialog", { name: "Search workspace modules" }),
    ).not.toBeInTheDocument();
  });
});
