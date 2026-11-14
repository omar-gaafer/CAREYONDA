import {
  LayoutDashboard,
  HeartPulse,
  Globe2,
  BrainCircuit,
  Siren,
  MessagesSquare,
  Users,
  ChartNoAxesCombined,
  ClipboardList,
  Database,
  Box,
  History,
  Moon,
} from "lucide-react";
export const modules = [
  {
    path: "/overview",
    title: "Mission Command Center",
    short: "Command Center",
    icon: LayoutDashboard,
    phase1: true,
  },
  {
    path: "/health",
    title: "Health Monitoring",
    short: "Health Monitoring",
    icon: HeartPulse,
    phase1: true,
  },
  {
    path: "/environment",
    title: "Space Environment",
    short: "Space Environment",
    icon: Globe2,
    phase1: true,
  },
  {
    path: "/ai-intelligence",
    phase2: true,
    title: "AI Health Intelligence",
    short: "AI Intelligence",
    icon: BrainCircuit,
    detail:
      "Precomputed synthetic M2 compatibility rankings, evidence inspection, and abstention; no live inference or HTTP integration.",
  },
  {
    path: "/incidents",
    phase2: true,
    title: "Alerts & Incidents",
    short: "Alerts & Incidents",
    icon: Siren,
    detail:
      "Synthetic incident review with session-only acknowledgement, notes, and closure. No operational alert policy or medical resolution is implied.",
  },
  {
    path: "/assistant",
    title: "CAREYONDA AI Assistant",
    short: "AI Assistant",
    icon: MessagesSquare,
    detail:
      "No language model or conversational service is connected. This module cannot provide diagnoses, treatment instructions, or spacecraft commands.",
  },
  {
    // Local, transient Model C self-report flow; rendered by its own route.
    path: "/model-c",
    title: "Isolation & Confinement · Model C",
    short: "Model C (local)",
    icon: Moon,
    local: true,
  },
  {
    path: "/crew",
    title: "Crew Health Profiles",
    short: "Crew Profiles",
    icon: Users,
    detail:
      "Synthetic crew selectors are available in Phase 1. Longitudinal profiles, authorized record access, and profile persistence require future contracts.",
  },
  {
    path: "/analytics",
    title: "Predictive Analytics",
    short: "Predictive Analytics",
    icon: ChartNoAxesCombined,
    detail:
      "No prediction models or forecasting API are connected. Displayed observation trends do not predict future health or environmental safety.",
  },
  {
    path: "/recommendations",
    title: "Recommendations & Protocols",
    short: "Protocols",
    icon: ClipboardList,
    detail:
      "Approved procedure and safety-policy implementations are absent. No treatment recommendations or autonomous actions are available. Safety remains not evaluated.",
  },
  {
    path: "/data-explorer",
    title: "Data Explorer",
    short: "Data Explorer",
    icon: Database,
    phase1: true,
  },
  {
    path: "/digital-twin",
    title: "Spacecraft Digital Twin",
    short: "Digital Twin",
    icon: Box,
    detail:
      "No spacecraft geometry, subsystem simulation, or digital-twin service is connected. The synthetic habitat context is an observation scope only.",
  },
  {
    path: "/reports",
    title: "Reports & Mission Replay",
    short: "Reports & Replay",
    icon: History,
    detail:
      "Report generation, saved investigations, and mission replay persistence are not implemented. Evidence can be inspected in the read-only Data Explorer.",
  },
];
