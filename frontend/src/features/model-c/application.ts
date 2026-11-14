import {
  fatigueCategories,
  MAX_ASSESSMENT_DAYS,
  MAX_ENTRIES,
  pseudonymPattern,
  type FatigueCategory,
  type LocalSubmission,
} from "../../contracts/model-c";

/** One editable row. Blank strings mean "not entered" — never zero. */
export type EntryDraft = {
  key: number;
  date: string;
  sleep: string;
  fatigue: "" | FatigueCategory;
};
export type DraftIssue = {
  key: number | "participant" | "session";
  field: "participant" | "date" | "sleep" | "fatigue" | "entry" | "session";
  message: string;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const DECIMAL = /^\d{1,2}(\.\d{1,2})?$/;
const REPORT_HOUR_UTC = 12;

export function reportTime(date: string): number {
  const [y, m, d] = date.split("-").map(Number);
  return Date.UTC(y, m - 1, d, REPORT_HOUR_UTC);
}

function realCalendarDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const [y, m, d] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(y, m - 1, d));
  return (
    parsed.getUTCFullYear() === y &&
    parsed.getUTCMonth() === m - 1 &&
    parsed.getUTCDate() === d
  );
}

/** Mirrors backend validation for immediate feedback; the server re-validates. */
export function validateDraft(
  participant: string,
  assessmentDays: number,
  drafts: EntryDraft[],
  now: number,
): { issues: DraftIssue[]; submission: LocalSubmission | null } {
  const issues: DraftIssue[] = [];
  if (!pseudonymPattern.test(participant))
    issues.push({
      key: "participant",
      field: "participant",
      message:
        "Use a 3–40 character pseudonym: letters, digits, '-' or '_' only. Do not use a name or e-mail address.",
    });
  if (
    !Number.isInteger(assessmentDays) ||
    assessmentDays < 1 ||
    assessmentDays > MAX_ASSESSMENT_DAYS
  )
    issues.push({
      key: "session",
      field: "session",
      message: `Assessment period must be 1–${MAX_ASSESSMENT_DAYS} days.`,
    });
  if (drafts.length === 0 || drafts.length > MAX_ENTRIES)
    issues.push({
      key: "session",
      field: "session",
      message: `Enter between 1 and ${MAX_ENTRIES} days.`,
    });
  const seen = new Set<string>();
  const entries: LocalSubmission["entries"] = [];
  for (const draft of drafts) {
    const before = issues.length;
    if (!realCalendarDate(draft.date))
      issues.push({
        key: draft.key,
        field: "date",
        message: "Enter a real calendar date (YYYY-MM-DD).",
      });
    else if (seen.has(draft.date))
      issues.push({
        key: draft.key,
        field: "date",
        message: "Each date may appear once.",
      });
    else if (reportTime(draft.date) > now)
      issues.push({
        key: draft.key,
        field: "date",
        message:
          "This date's 12:00 UTC report time has not happened yet; future entries are not accepted.",
      });
    seen.add(draft.date);
    const sleepText = draft.sleep.trim();
    const hours = sleepText === "" ? undefined : Number(sleepText);
    if (
      sleepText !== "" &&
      (!DECIMAL.test(sleepText) || hours === undefined || hours > 24)
    )
      issues.push({
        key: draft.key,
        field: "sleep",
        message: "Sleep must be 0–24 hours (up to 2 decimals) or left blank.",
      });
    if (draft.fatigue !== "" && !fatigueCategories.includes(draft.fatigue))
      issues.push({
        key: draft.key,
        field: "fatigue",
        message: "Choose rested, tired or very tired, or leave blank.",
      });
    if (sleepText === "" && draft.fatigue === "")
      issues.push({
        key: draft.key,
        field: "entry",
        message: "Enter sleep, fatigue or both; an empty day is not submitted.",
      });
    if (issues.length === before)
      entries.push({
        date: draft.date,
        ...(hours === undefined ? {} : { sleep_duration_hours: hours }),
        ...(draft.fatigue === "" ? {} : { fatigue: draft.fatigue }),
      });
  }
  if (issues.length) return { issues, submission: null };
  return {
    issues,
    submission: {
      schema_version: "1.0.0",
      participant_id: participant,
      assessment_days: assessmentDays,
      entries,
    },
  };
}

export const reasonText: Record<string, string> = {
  insufficient_occupied_bins:
    "too few days with valid entries in the reference period",
  insufficient_observed_span: "valid entries cover too short a stretch of time",
  insufficient_occupancy_fraction:
    "too large a share of reference days has no entry",
  reference_gap_exceeds_maximum: "a gap between valid entries is too long",
  reference_too_old: "the reference period is too old for the assessment time",
  no_valid_reference_evidence: "no valid entries in the reference period",
  zero_reference_dispersion:
    "reference values never varied, so a deviation score is undefined",
  sensor_identity_unavailable: "the instrument identity was not declared",
  insufficient_reference_reports:
    "too few fatigue reports in the reference period",
  no_valid_assessment_reports: "no fatigue reports in the assessment period",
  baseline_insufficient_reference:
    "your personal reference could not be established",
  baseline_unsupported: "the personal reference is unsupported",
  target_quality_suspect: "the entry was marked suspect",
  target_incompatible_or_unavailable:
    "the entry was unavailable at assessment time",
  no_scored_assessment_readings:
    "no valid sleep entry in the assessment period",
  no_indicator_assessed: "no supported indicator could be assessed",
  target_measurement_unavailable: "the value was not entered",
  measurement_unavailable: "the value was not entered",
  quality_unavailable: "the value was not entered",
  not_entered: "the value was not entered",
};
export const explainReason = (code: string) =>
  reasonText[code] ? `${reasonText[code]} (${code})` : code;
