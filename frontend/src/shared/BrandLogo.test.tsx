import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../testing/ResearchWorkspace";

describe("official branding", () => {
  it("switches sidebar artwork on collapse and restores it on expansion", async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    const sidebar = screen.getByLabelText("Mission navigation");
    const logo = within(sidebar).getByRole("img");
    expect(logo).toHaveAttribute(
      "src",
      "/brand/careyonda-logo-transparent.png",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Collapse sidebar" }),
    );
    expect(logo).toHaveAttribute(
      "src",
      "/brand/careyonda-icon-transparent.png",
    );
    // A collapsed desktop sidebar must still show the full wordmark in a mobile drawer.
    expect(logo.closest("picture")?.querySelector("source")).toHaveAttribute(
      "media",
      "(max-width: 700px)",
    );
    expect(logo.closest("picture")?.querySelector("source")).toHaveAttribute(
      "srcset",
      "/brand/careyonda-logo-transparent.png",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Expand sidebar" }),
    );
    expect(logo).toHaveAttribute(
      "src",
      "/brand/careyonda-logo-transparent.png",
    );
    expect(logo).toHaveAccessibleName("CAREYONDA logo and wordmark");
  });

  it("brands the header and footer while preserving route titles", async () => {
    render(
      <MemoryRouter initialEntries={["/health"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Health Monitoring", level: 1 });
    expect(document.title).toBe("Health Monitoring · CAREYONDA");
    expect(
      screen.getByRole("img", { name: "CAREYONDA mission emblem" }),
    ).toHaveAttribute("src", "/brand/careyonda-icon-transparent.png");
    expect(
      within(screen.getByRole("contentinfo")).getByRole("img"),
    ).toHaveAttribute("src", "/brand/careyonda-logo-transparent.png");
  });
});
