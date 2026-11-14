import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ConnectedWorkspace } from "./ConnectedWorkspace";

describe("public deployment isolation", () => {
  it.each(["/overview", "/environment", "/model-c", "/ai-intelligence"])(
    "isolates %s from private APIs",
    async (path) => {
      const fetcher = vi
        .spyOn(globalThis, "fetch")
        .mockRejectedValue(new Error("No public research API"));
      try {
        render(
          <MemoryRouter initialEntries={[path]}>
            <ConnectedWorkspace publicDemo apiUrl="https://untrusted.example" />
          </MemoryRouter>,
        );
        expect(
          await screen.findByText("PUBLIC SYNTHETIC DEMO"),
        ).toBeInTheDocument();
        expect(screen.queryByLabelText("Data source")).not.toBeInTheDocument();
        if (path === "/environment") {
          expect(
            await screen.findByText("MODEL UNAVAILABLE"),
          ).toBeInTheDocument();
          expect(
            screen.queryByText("SIMULATED MODEL A DEMO"),
          ).not.toBeInTheDocument();
        }
        if (path === "/model-c") {
          expect(
            await screen.findByText("No public self-report submission"),
          ).toBeInTheDocument();
          expect(
            screen.queryByLabelText("Pseudonymous participant ID"),
          ).not.toBeInTheDocument();
        }
        expect(fetcher).not.toHaveBeenCalled();
      } finally {
        fetcher.mockRestore();
      }
    },
  );
});
