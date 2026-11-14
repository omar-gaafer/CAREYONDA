import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Account } from "./Account";
afterEach(() => vi.unstubAllGlobals());
describe("server-authorized account client", () => {
  it("shows unavailable without substituting a profile", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("", { status: 503 })),
    );
    render(<Account apiUrl="http://127.0.0.1:8108" />);
    fireEvent.change(screen.getByLabelText("Supabase access token"), {
      target: { value: "synthetic-test-token" },
    });
    fireEvent.click(screen.getByText("Verify identity"));
    expect(
      await screen.findByText("Database or authentication unavailable"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Create mission")).not.toBeInTheDocument();
  });
  it("keeps a delayed previous identity out after sign out", async () => {
    let resolve!: (response: Response) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((r) => {
            resolve = r;
          }),
      ),
    );
    render(<Account apiUrl="http://127.0.0.1:8108" />);
    fireEvent.change(screen.getByLabelText("Supabase access token"), {
      target: { value: "synthetic-test-token" },
    });
    fireEvent.click(screen.getByText("Verify identity"));
    fireEvent.click(screen.getByText("Sign out locally"));
    resolve(
      new Response(
        JSON.stringify({
          user_id: "11111111-1111-4111-8111-111111111111",
          roles: ["Admin"],
        }),
      ),
    );
    await waitFor(() =>
      expect(screen.getByText("Verify identity")).toBeDisabled(),
    );
    expect(screen.queryByText("Create mission")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Supabase access token")).toHaveValue("");
  });
  it("uses only server-returned roles and never persists the token", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            user_id: "11111111-1111-4111-8111-111111111111",
            roles: ["Doctor"],
          }),
        ),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<Account apiUrl="http://127.0.0.1:8108" />);
    fireEvent.change(screen.getByLabelText("Supabase access token"), {
      target: { value: "synthetic-test-token" },
    });
    fireEvent.click(screen.getByText("Verify identity"));
    expect(await screen.findByText(/Verified .*Doctor/)).toBeInTheDocument();
    expect(screen.queryByText("Create mission")).not.toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(fetcher.mock.calls.length).toBe(1);
  });
});
