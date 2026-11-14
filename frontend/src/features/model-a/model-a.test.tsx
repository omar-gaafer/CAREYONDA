import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import fixture from "../../infrastructure/fixtures/model-a-simulated.json";
import { ModelAPanel } from "./ModelAPanel";
import {
  createModelAClient,
  type ModelAClient,
} from "../../infrastructure/model-a";
import {
  modelAResponseSchema,
  authorizedSchema,
} from "../../contracts/model-a";
const result = () => structuredClone(fixture);
const catalog = () =>
  authorizedSchema.parse({
    api_version: "1.0.0",
    correlation_id: "test-correlation",
    model_availability: "available",
    samples: [
      {
        sample_id: fixture.contexts[0].sample.sample_id,
        assessment_mode: "live",
        source_event_time: fixture.contexts[0].source_event_time,
        scope: fixture.contexts[0].sample.scope,
        receipt_id: null,
      },
    ],
  });
function client(data: unknown = fixture): ModelAClient {
  return {
    list: vi.fn(async () => catalog()),
    assess: vi.fn(async () => modelAResponseSchema.parse(data)),
  };
}
const response = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("Model A context validation", () => {
  it("accepts actual sidecar shape from artificial backend fixture", () =>
    expect(modelAResponseSchema.parse(fixture).contexts[0].schema_version).toBe(
      "1.1.0",
    ));
  it.each(["unit", "flag", "version", "availability", "lineage", "score"])(
    "rejects %s contradictions",
    (change) => {
      const data = result();
      const c = data.contexts[0];
      if (change === "unit") c.sample.features[0].unit = "Pa";
      if (change === "flag") c.status = "not_flagged";
      if (change === "version") c.schema_version = "2.0.0";
      if (change === "availability")
        c.sample.available_at = "2099-01-01T00:00:00Z";
      if (change === "lineage")
        c.sample.features[0].observation_ids = ["unknown"];
      if (change === "score") c.anomaly_score = Number.NaN;
      expect(modelAResponseSchema.safeParse(data).success).toBe(false);
    },
  );
});
describe("Model A client", () => {
  it("discovers references and submits no paths or receipts", async () => {
    const ref = catalog().samples[0];
    const assessed = fixture.contexts[0].assessed_at;
    const fetcher = vi.fn(
      async (_url: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === "GET") return response(catalog());
        const request = JSON.parse(String(init?.body));
        expect(request.schema_version).toBe("1.1.0");
        expect(request.sample_references).toEqual([
          { sample_id: ref.sample_id, assessment_mode: "live" },
        ]);
        expect(request).not.toHaveProperty("samples");
        expect(request).not.toHaveProperty("replay_acquisition");
        expect(init?.credentials).toBe("omit");
        return response(fixture);
      },
    );
    const api = createModelAClient("http://127.0.0.1:8000", fetcher);
    await api.list();
    expect((await api.assess(ref, assessed)).contexts).toHaveLength(1);
  });
  it.each([403, 422, 500])(
    "rejects HTTP %s with no fallback",
    async (status) => {
      const fetcher = vi.fn(async () =>
        response({ error: { code: "test" } }, status),
      );
      const api = createModelAClient("http://localhost:8000", fetcher);
      await expect(
        api.assess(catalog().samples[0], fixture.contexts[0].assessed_at),
      ).rejects.toThrow();
      expect(fetcher).toHaveBeenCalledTimes(1);
    },
  );
  it("handles 503 with explicit empty contexts", async () => {
    const api = createModelAClient(
      "http://localhost:8000",
      vi.fn(async () =>
        response(
          {
            ...fixture,
            model_availability: "unavailable" as const,
            contexts: [],
          },
          503,
        ),
      ),
    );
    expect(
      (await api.assess(catalog().samples[0], fixture.contexts[0].assessed_at))
        .model_availability,
    ).toBe("unavailable");
  });
  it("rejects malformed 200 response", async () => {
    const api = createModelAClient(
      "http://localhost:8000",
      vi.fn(async () => response({})),
    );
    await expect(
      api.assess(catalog().samples[0], fixture.contexts[0].assessed_at),
    ).rejects.toThrow("contract");
  });
  it("rejects wrong result identity", async () => {
    const data = result();
    data.contexts[0].sample.sample_id = "other";
    const api = createModelAClient(
      "http://localhost:8000",
      vi.fn(async () => response(data)),
    );
    await expect(
      api.assess(catalog().samples[0], fixture.contexts[0].assessed_at),
    ).rejects.toThrow("contract");
  });
  it("rejects non-local configuration", () =>
    expect(() => createModelAClient("https://example.com")).toThrow());
});
describe("Model A panel", () => {
  it("labels simulated fixture mode without network", async () => {
    const api = client();
    render(<ModelAPanel mode="fixture" client={api} />);
    expect(
      await screen.findByText("SIMULATED MODEL A DEMO"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("flagged", { exact: true }),
    ).toBeInTheDocument();
    expect(api.list).not.toHaveBeenCalled();
  });
  it("shows loading", () => {
    const api = client();
    api.list = vi.fn(
      () => new Promise<Awaited<ReturnType<ModelAClient["list"]>>>(() => {}),
    );
    render(<ModelAPanel mode="api" client={api} />);
    expect(screen.getByText("Loading Model A context…")).toBeInTheDocument();
  });
  it("shows unavailable sample without fabricating an authorized request", async () => {
    const api = client();
    api.list = vi.fn(async () => ({ ...catalog(), samples: [] }));
    render(<ModelAPanel mode="api" client={api} />);
    expect(
      await screen.findByText(/Authorized replay sample unavailable/),
    ).toBeInTheDocument();
    expect(api.assess).not.toHaveBeenCalled();
  });
  it("shows model unavailable", async () => {
    const api = client();
    api.list = vi.fn(async () => ({
      ...catalog(),
      model_availability: "unavailable" as const,
    }));
    render(<ModelAPanel mode="api" client={api} />);
    expect(await screen.findByText(/Model unavailable/)).toBeInTheDocument();
  });
  it.each(["flagged", "not_flagged", "abstained"] as const)(
    "renders %s from validated response",
    async (status) => {
      const data = modelAResponseSchema.parse(result());
      data.contexts[0].status = status;
      if (status === "not_flagged") data.contexts[0].anomaly_score = 0.4;
      if (status === "abstained") {
        data.contexts[0].anomaly_score = null;
        data.contexts[0].abstention_reasons = [
          "missing_required:cabin_co2_concentration_value",
        ];
      }
      render(<ModelAPanel mode="api" client={client(data)} />);
      await userEvent.click(
        await screen.findByRole("button", { name: "Assess Model A" }),
      );
      expect(
        await screen.findByText(status, { exact: true }),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Original mission event time"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Feature and evidence provenance"),
      ).toBeInTheDocument();
    },
  );
  it("shows backend unavailable without substituted fixture", async () => {
    const api = createModelAClient(
      "http://localhost:8000",
      vi.fn(async () => {
        throw new Error("offline");
      }),
    );
    render(<ModelAPanel mode="api" client={api} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No fixture fallback",
    );
    expect(
      screen.queryByText("flagged", { exact: true }),
    ).not.toBeInTheDocument();
  });
  it.each([403, 422])("shows rejected request %s", async (status) => {
    const api = createModelAClient(
      "http://localhost:8000",
      vi.fn(async (_url, init) =>
        init?.method === "GET" ? response(catalog()) : response({}, status),
      ),
    );
    render(<ModelAPanel mode="api" client={api} />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Assess Model A" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      status === 403 ? "Unauthorized" : "Invalid input",
    );
    expect(
      screen.queryByText("flagged", { exact: true }),
    ).not.toBeInTheDocument();
  });
});
