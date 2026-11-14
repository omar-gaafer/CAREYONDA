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
} from "lucide-react";
export const modules = [
  {
    path: "/account",
    title: "Authorized records",
    short: "Authorized records",
    icon: Users,
  },
  {
    path: "/sleep-fatigue",
    title: "Sleep/Fatigue Monitor",
    short: "Sleep/Fatigue Monitor",
    icon: HeartPulse,
  },
  {
    path: "/overview",
    title: "Mission Dashboard",
    short: "Mission Dashboard",
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
    title: "Environmental Monitoring",
    short: "Environmental Monitoring",
    icon: Globe2,
    phase1: true,
  },
  {
    path: "/ai-intelligence",
    phase2: true,
    title: "AI Intelligence",
    short: "AI Intelligence",
    icon: BrainCircuit,
    detail:
      "Operational model access requires verified capabilities, compatible evidence contracts and explicit research limitations.",
  },
  {
    path: "/incidents",
    phase2: true,
    title: "Incidents",
    short: "Incidents",
    icon: Siren,
    detail:
      "No operational incident API or approved alert policy is exposed by the current backend.",
  },
  {
    path: "/assistant",
    title: "AI Assistant",
    short: "AI Assistant",
    icon: MessagesSquare,
    detail:
      "No language model or conversational service is connected. This module cannot provide diagnoses, treatment instructions, or spacecraft commands.",
  },
  {
    path: "/crew",
    title: "Crew",
    short: "Crew",
    icon: Users,
    detail:
      "Authorized subject context, profile retrieval and authentication are required before enabling health profiles.",
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
      "This route contains an illustrative reference schematic only. It is not connected to spacecraft geometry, crew profiles, telemetry, or an operational digital-twin service.",
  },
  {
    path: "/reports",
    title: "Reports",
    short: "Reports",
    icon: History,
    detail:
      "Report generation, saved investigations, and mission replay persistence are not implemented. Evidence can be inspected in the read-only Data Explorer.",
  },
];
