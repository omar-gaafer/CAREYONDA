import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../../app/App";
import data from "../../infrastructure/fixtures/investigations.json";
import type { InvestigationRepository } from "../../infrastructure/investigations";
const mount = (
  path = "/ai-intelligence",
  repository?: InvestigationRepository,
) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App investigationRepository={repository} />
    </MemoryRouter>,
  );
describe("Phase 2 research workspaces", () => {
  it("renders ranked compatibility, safety and traceable clickable evidence", async () => {
    mount();
    await screen.findByRole("heading", {
      name: "AI Health Intelligence",
      level: 1,
    });
    expect(screen.getByText("PATTERN SELECTED")).toBeInTheDocument();
    expect(screen.getByText("not_evaluated")).toBeInTheDocument();
    expect(screen.getByText("reference-rules-1.0.0")).toBeInTheDocument();
    expect(screen.getByText("SELECTED PATTERN")).toBeInTheDocument();
    const oid =
      data[0].result.hypotheses[0].supporting_evidence[0].observation_ids[0];
    await userEvent.click(
      screen.getAllByRole("button", { name: `Inspect evidence ${oid}` })[0],
    );
    const panel = screen.getByRole("region", {
      name: "Investigation evidence details",
    });
    expect(panel).toHaveFocus();
    expect(within(panel).getByText(oid)).toBeInTheDocument();
    expect(within(panel).getByText("Ingestion time")).toBeInTheDocument();
    expect(
      within(panel).getByText("simulated / phase2-fixture"),
    ).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(
      screen.queryByRole("region", { name: "Investigation evidence details" }),
    ).not.toBeInTheDocument();
  });
  it.each([1, 2, 3])(
    "preserves abstention mode for fixture %i",
    async (index) => {
      mount(
        `/ai-intelligence?investigation=${data[index].result.investigation_id}`,
      );
      await screen.findByText("ABSTAINED");
      expect(screen.queryByText("SELECTED PATTERN")).not.toBeInTheDocument();
      expect(screen.getByText("not_evaluated")).toBeInTheDocument();
    },
  );
  it("synchronizes crew context and exposes complete missing evidence", async () => {
    mount();
    await screen.findByRole("heading", {
      name: "AI Health Intelligence",
      level: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText("Crew"), "crew-02");
    expect(screen.getAllByText("Sam Rivera").length).toBeGreaterThan(0);
    expect(screen.getByText("ABSTAINED")).toBeInTheDocument();
    expect(screen.getAllByText("synthetic_dropout").length).toBe(3);
    await userEvent.selectOptions(screen.getByLabelText("Time range"), "6");
    expect(screen.getByText(/global 6-hour/)).toBeInTheDocument();
  });
  it("retains workflow acknowledgement, notes, closure and reopening across navigation", async () => {
    mount("/incidents");
    await screen.findByRole("heading", {
      name: "Alerts & Incidents",
      level: 1,
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Acknowledge incident" }),
    );
    expect(
      screen.queryByRole("button", { name: "Acknowledge incident" }),
    ).not.toBeInTheDocument();
    await userEvent.type(
      screen.getByLabelText("Manual review note"),
      "Reviewed synthetic evidence.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Record note" }));
    expect(
      screen.getByText("Reviewed synthetic evidence."),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Resolve workflow" }),
    );
    expect(
      screen.getByText(/does not mean a medical condition was resolved/),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("link", { name: "Open investigation" }),
    );
    await screen.findByText("PATTERN SELECTED");
    await userEvent.click(
      screen.getByRole("link", { name: "Open associated incident" }),
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Reopen incident" }),
    );
    expect(
      screen.getByRole("button", { name: "Acknowledge incident" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Reviewed synthetic evidence."),
    ).toBeInTheDocument();
    expect(screen.getByText("not_evaluated")).toBeInTheDocument();
  });
  it("filters incidents by shared crew and workflow status", async () => {
    mount("/incidents");
    await screen.findByRole("heading", {
      name: "Alerts & Incidents",
      level: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText("Crew"), "crew-03");
    expect(
      screen.getByRole("button", { name: /Competing synthetic patterns/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Incomplete cabin evidence/ }),
    ).not.toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Workflow status"),
      "closed",
    );
    expect(screen.getByText("No matching observations")).toBeInTheDocument();
  });
  it.each(["/ai-intelligence", "/incidents"])(
    "handles empty source at %s",
    async (path) => {
      mount(path, {
        async list() {
          return [];
        },
      });
      expect(
        await screen.findByText("No matching observations"),
      ).toBeInTheDocument();
    },
  );
  it("rejects unsupported payloads explicitly and recovers on retry", async () => {
    let calls = 0;
    mount("/ai-intelligence", {
      async list() {
        if (++calls === 1)
          return [
            {
              ...data[0],
              result: { ...data[0].result, engine_version: "unsupported" },
            },
          ];
        return data;
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "unsupported version",
    );
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("PATTERN SELECTED")).toBeInTheDocument();
  });
  it("handles unavailable source and stale deep links without changing crew context", async () => {
    mount("/ai-intelligence?investigation=unavailable");
    expect(
      await screen.findByText("Capability not connected"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Show available investigations" }),
    );
    expect(screen.getByText("PATTERN SELECTED")).toBeInTheDocument();
  });
  it("shows a safe source failure", async () => {
    mount("/ai-intelligence", {
      async list() {
        throw new Error("private raw record");
      },
    });
    expect(await screen.findByRole("alert")).not.toHaveTextContent(
      "private raw record",
    );
  });
});
