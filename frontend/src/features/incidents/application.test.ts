import { expect, it } from "vitest";
import { reviewIncident, type IncidentReview } from "./application";
it("keeps workflow transitions independent of reasoning and retains notes", () => {
  let review: IncidentReview = { status: "open", notes: [] };
  review = reviewIncident(review, { type: "acknowledge" });
  expect(review.status).toBe("acknowledged");
  review = reviewIncident(review, {
    type: "note",
    text: "  Synthetic review  ",
    recordedAt: "2026-11-13T12:00:00Z",
  });
  review = reviewIncident(review, { type: "close" });
  expect(review.status).toBe("closed");
  review = reviewIncident(review, { type: "reopen" });
  expect(review.status).toBe("open");
  expect(review.notes[0].text).toBe("Synthetic review");
  expect(
    reviewIncident(review, { type: "note", text: "   ", recordedAt: "" }),
  ).toBe(review);
  expect(
    reviewIncident(review, {
      type: "note",
      text: "x".repeat(2001),
      recordedAt: "",
    }),
  ).toBe(review);
});
