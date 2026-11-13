export type WorkflowStatus = "open" | "acknowledged" | "closed";
export interface ReviewNote {
  text: string;
  recordedAt: string;
}
export interface IncidentReview {
  status: WorkflowStatus;
  notes: ReviewNote[];
}
export type ReviewAction =
  | { type: "acknowledge" | "close" | "reopen" }
  | { type: "note"; text: string; recordedAt: string };
export function reviewIncident(
  state: IncidentReview,
  action: ReviewAction,
): IncidentReview {
  if (action.type === "note") {
    const text = action.text.trim();
    return text && text.length <= 2000
      ? {
          ...state,
          notes: [...state.notes, { text, recordedAt: action.recordedAt }],
        }
      : state;
  }
  if (action.type === "acknowledge")
    return state.status === "open"
      ? { ...state, status: "acknowledged" }
      : state;
  if (action.type === "close")
    return state.status !== "closed" ? { ...state, status: "closed" } : state;
  return state.status === "closed" ? { ...state, status: "open" } : state;
}
