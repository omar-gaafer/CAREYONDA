import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SpacecraftTwin } from "./SpacecraftTwin";

describe("illustrative spacecraft twin", () => {
  it("shows the schematic and switches between crew and system emphasis", () => {
    render(<SpacecraftTwin />);
    expect(
      screen.getByRole("img", { name: /illustrative orbital habitat/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No spacecraft telemetry connected/),
    ).toBeInTheDocument();

    const systems = screen.getByRole("button", { name: /systems view/i });
    fireEvent.click(systems);
    expect(systems).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByText("Illustrative system locations"),
    ).toBeInTheDocument();

    const crew = screen.getByRole("button", { name: /crew view/i });
    fireEvent.click(crew);
    expect(crew).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Illustrative crew figures")).toBeInTheDocument();
  });
});
