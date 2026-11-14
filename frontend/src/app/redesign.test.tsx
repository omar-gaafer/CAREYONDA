import { modules } from "./modules";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../testing/ResearchWorkspace";

function mount(path = "/data-explorer") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("v2 research workspace", () => {
  it("shows the only available mission and honest fixture connection status", async () => {
    mount("/overview");
    await screen.findByRole("heading", {
      name: "Mission Dashboard",
      level: 1,
    });
    expect(screen.getByLabelText("Mission context")).toHaveValue("ARES-07");
    expect(screen.getByText("Backend not required")).toBeInTheDocument();
    expect(screen.getByText("SYNTHETIC MODE")).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("navigation", { name: "Workspace modules" }),
      ).getAllByRole("link"),
    ).toHaveLength(modules.length);
  });
  it("searches evidence IDs without changing the original observation", async () => {
    mount();
    await screen.findByRole("heading", { name: "Data Explorer", level: 1 });
    const inspect = screen.getAllByRole("button", { name: /^Inspect / })[0];
    const id = inspect.getAttribute("aria-label")!.replace("Inspect ", "");
    const value = inspect.closest("tr")!.children[2].textContent;
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Search evidence" }),
      id,
    );
    expect(screen.getAllByRole("button", { name: /^Inspect / })).toHaveLength(
      1,
    );
    const found = screen.getByRole("button", { name: `Inspect ${id}` });
    expect(found.closest("tr")!.children[2].textContent).toBe(value);
    await userEvent.click(found);
    const dialog = screen.getByRole("dialog", { name: "Evidence inspection" });
    expect(within(dialog).getByText(id)).toBeInTheDocument();
    await userEvent.tab({ shift: true });
    expect(
      within(dialog).getByRole("button", { name: "Close details" }),
    ).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(found).toHaveFocus();
    expect(document.body.style.overflow).not.toBe("hidden");
  });
  it("shows an explicit empty state when evidence search has no matches", async () => {
    mount();
    await screen.findByRole("searchbox", { name: "Search evidence" });
    await userEvent.type(screen.getByRole("searchbox"), "no-such-evidence");
    expect(screen.getByText("No matching observations")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it("announces session-only incident updates and allows dismissal", async () => {
    mount("/incidents");
    await userEvent.click(
      await screen.findByRole("button", { name: "Acknowledge incident" }),
    );
    expect(
      screen.getByText("Session review updated. Not saved to a server."),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Dismiss notification" }),
    );
    expect(
      screen.queryByText("Session review updated. Not saved to a server."),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("acknowledged", { selector: "strong" }),
    ).toBeInTheDocument();
  });
});
