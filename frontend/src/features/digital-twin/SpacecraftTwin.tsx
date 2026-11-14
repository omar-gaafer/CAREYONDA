import { useState } from "react";
import { Activity, Box, Users } from "lucide-react";
import { PageIntro } from "../../shared/ui";

type View = "crew" | "systems";

function CrewFigure({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g className="twin-crew-figure" transform={`translate(${x} ${y})`}>
      <title>{label} — illustrative figure</title>
      <circle cx="0" cy="-18" r="8" fill="#d8e6e1" />
      <path d="M-8-18a8 8 0 0 1 16 0" fill="#9ecdb9" />
      <path d="M-9-8Q0-14 9-8l6 28H-15z" fill="#a9c3b8" />
      <path
        d="M-8 1h16M-5 20l-3 15m13-15 3 15"
        stroke="#e0e9e5"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <path
        d="M-11 0l-9 14m29-14 8 14"
        stroke="#d4e4dd"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle cx="0" cy="1" r="3" fill="#69d5a2" />
      <rect x="-11" y="35" width="22" height="4" rx="2" fill="#7a998d" />
    </g>
  );
}

export function SpacecraftTwin() {
  const [view, setView] = useState<View>("crew");
  const systems = view === "systems";

  return (
    <div className="twin-page">
      <PageIntro
        eyebrow="ILLUSTRATIVE MODEL · NOT LIVE TELEMETRY"
        title="Spacecraft Digital Twin"
      >
        Explore a lightweight 3D-style habitat schematic. Crew figures and
        system markers are illustrative only.
      </PageIntro>

      <section
        className="twin-stage"
        aria-label="Illustrative spacecraft model"
      >
        <div className="twin-stage-header">
          <div>
            <span className="twin-kicker">
              <Activity size={13} /> REFERENCE SCHEMATIC
            </span>
            <h2>Orbital habitat · cutaway view</h2>
          </div>
          <div
            className="twin-view-switch"
            role="group"
            aria-label="Schematic view"
          >
            <button
              className={view === "crew" ? "selected" : ""}
              onClick={() => setView("crew")}
              aria-pressed={view === "crew"}
            >
              <Users size={15} /> Crew view
            </button>
            <button
              className={view === "systems" ? "selected" : ""}
              onClick={() => setView("systems")}
              aria-pressed={view === "systems"}
            >
              <Box size={15} /> Systems view
            </button>
          </div>
        </div>

        <div className={`twin-scene ${systems ? "systems-view" : "crew-view"}`}>
          <div className="twin-grid" aria-hidden="true" />
          <div className="twin-orbit twin-orbit-one" aria-hidden="true" />
          <div className="twin-orbit twin-orbit-two" aria-hidden="true" />
          <svg
            className="twin-craft"
            viewBox="0 0 920 490"
            role="img"
            aria-labelledby="craft-title craft-desc"
          >
            <title id="craft-title">Illustrative orbital habitat cutaway</title>
            <desc id="craft-desc">
              A non-operational isometric spacecraft made of three connected
              modules, with two illustrative crew figures in the central module.
            </desc>
            <defs>
              <linearGradient id="moduleFront" x1="0" x2="1" y1="0" y2="1">
                <stop stopColor="#30433d" />
                <stop offset="1" stopColor="#17251f" />
              </linearGradient>
              <linearGradient id="moduleTop" x1="0" x2="1">
                <stop stopColor="#526c60" />
                <stop offset="1" stopColor="#344d42" />
              </linearGradient>
              <linearGradient id="solar" x1="0" x2="1">
                <stop stopColor="#376e73" />
                <stop offset="1" stopColor="#1e414a" />
              </linearGradient>
              <filter
                id="craftShadow"
                x="-30%"
                y="-30%"
                width="160%"
                height="180%"
              >
                <feDropShadow
                  dx="0"
                  dy="18"
                  stdDeviation="14"
                  floodColor="#050907"
                  floodOpacity=".62"
                />
              </filter>
            </defs>
            <g className="twin-solar" opacity=".96">
              <path
                d="M315 237 166 172 157 184 305 250zM605 220l149-80 8 13-149 81z"
                fill="#78958a"
              />
              <path
                d="m62 142 103 25-11 133-103-27zm103 25 101 25-12 133-102-25zM665 182l102-55 10 129-103 55zm102-55 100-55 9 129-99 55z"
                fill="url(#solar)"
                stroke="#75aca2"
                strokeWidth="2"
              />
              <path
                d="m111 154-10 131m61-118-12 132m-88-91 203 50m466-54-9 130m59-158-9 130m-79-88 204-110"
                stroke="#82b6ad"
                strokeOpacity=".38"
                strokeWidth="2"
              />
            </g>
            <g
              filter="url(#craftShadow)"
              stroke="#93aa9e"
              strokeWidth="2"
              strokeLinejoin="round"
            >
              <path d="m260 257 111-64 107 44-111 67z" fill="url(#moduleTop)" />
              <path d="m260 257 107 47v95l-107-48z" fill="url(#moduleFront)" />
              <path d="m367 304 111-67v94l-111 68z" fill="#1d2b25" />
              <path d="m370 193 96-55 115 44-103 55z" fill="#5b7467" />
              <path d="m370 193 108 44v99l-108-32z" fill="url(#moduleFront)" />
              <path d="m478 237 103-55v94l-103 60z" fill="#1b2923" />
              <path d="m479 238 102-56 91 35-101 59z" fill="#50695c" />
              <path d="m479 238 92 38v86l-92-31z" fill="url(#moduleFront)" />
              <path d="m571 276 101-59v86l-101 59z" fill="#1a2822" />
              <path
                d="m316 281 50 22m-49-7 50 22m71-93 38 16m-38-1 38 15m48-5 42 18m-42-4 42 18"
                stroke="#a2b7ab"
                strokeOpacity=".48"
              />
              <path
                d="m345 247 27-16v54l-27 16zm162-47 29-16v52l-29 16zm91 87 29-17v50l-29 17z"
                fill="#6b9582"
                stroke="#b4c9bc"
              />
              <path
                d="m335 345 22 10v17l-22-10zm167-92 22 9v17l-22-9z"
                fill="#68d3a0"
                stroke="none"
              />
            </g>
            <g className="twin-crew">
              <CrewFigure x={422} y={258} label="Crew figure one" />
              <CrewFigure x={464} y={277} label="Crew figure two" />
            </g>
            <g
              className="twin-system-markers"
              fontFamily="inherit"
              fontSize="12"
              fontWeight="600"
            >
              <circle cx="350" cy="351" r="8" fill="#71dbad" />
              <text x="350" y="355" textAnchor="middle" fill="#102119">
                +
              </text>
              <circle cx="514" cy="268" r="8" fill="#71dbad" />
              <text x="514" y="272" textAnchor="middle" fill="#102119">
                +
              </text>
              <circle cx="620" cy="328" r="8" fill="#71dbad" />
              <text x="620" y="332" textAnchor="middle" fill="#102119">
                +
              </text>
            </g>
          </svg>
          <div className="twin-callout callout-left">
            <span>01</span>
            <b>Habitation module</b>
            <i />
          </div>
          <div className="twin-callout callout-top">
            <span>02</span>
            <b>Research module</b>
            <i />
          </div>
          <div className="twin-callout callout-right">
            <span>03</span>
            <b>Service module</b>
            <i />
          </div>
          <div className="twin-scene-caption">
            ISOMETRIC CUTAWAY <span>·</span> SCHEMATIC ONLY
          </div>
        </div>

        <div className="twin-stage-footer">
          <span>
            <i className="twin-legend-dot" />{" "}
            {systems
              ? "Illustrative system locations"
              : "Illustrative crew figures"}
          </span>
          <span>No spacecraft telemetry connected</span>
        </div>
      </section>

      <div className="twin-info-grid">
        <article className="twin-info-card">
          <span className="twin-card-icon">
            <Box size={17} />
          </span>
          <div>
            <h3>Modular layout</h3>
            <p>
              Three connected sections shown as a simplified reference model.
            </p>
          </div>
          <span className="twin-card-index">01</span>
        </article>
        <article className="twin-info-card">
          <span className="twin-card-icon">
            <Users size={17} />
          </span>
          <div>
            <h3>People are illustrative</h3>
            <p>Figures do not represent real crew identities or positions.</p>
          </div>
          <span className="twin-card-index">02</span>
        </article>
        <article className="twin-info-card">
          <span className="twin-card-icon">
            <Activity size={17} />
          </span>
          <div>
            <h3>Static demonstration</h3>
            <p>
              No live sensor state, safety status, or vehicle behavior is
              inferred.
            </p>
          </div>
          <span className="twin-card-index">03</span>
        </article>
      </div>
    </div>
  );
}
