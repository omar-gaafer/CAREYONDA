import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { it, expect } from "vitest";
import { createModelAClient } from "../../infrastructure/model-a";
import { ModelAPanel } from "./ModelAPanel";
it.skipIf(!import.meta.env.VITE_MODEL_A_E2E_URL)(
  "renders a real local API replay result without mocking fetch",
  async () => {
    const apiUrl = import.meta.env.VITE_MODEL_A_E2E_URL;
    // jsdom supplies a DOM AbortSignal while Node fetch uses another realm.
    // Bridge transport only; actual HTTP responses remain completely unmocked.
    const client = createModelAClient(apiUrl, (input, init) =>
      fetch(input, { ...init, signal: undefined }),
    );
    const reference = (await client.list()).samples[0];
    const expected = (await client.assess(reference, new Date().toISOString()))
      .contexts[0];
    expect(expected.anomaly_score).not.toBeNull();
    render(
      <ModelAPanel
        mode="api"
        client={client}
        apiUrl={import.meta.env.VITE_MODEL_A_E2E_URL}
      />,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Assess Model A" }),
    );
    expect(
      await screen.findByText(expected.status, { exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(String(expected.anomaly_score), { exact: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("historical_replay", { exact: true }),
    ).toBeInTheDocument();
    expect(screen.getByText("unknown", { exact: true })).toBeInTheDocument();
    expect(
      screen.getByText("careyonda_replay", { exact: true }),
    ).toBeInTheDocument();
  },
);
