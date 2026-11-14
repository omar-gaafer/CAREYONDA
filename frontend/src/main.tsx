import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConnectedWorkspace } from "./app/ConnectedWorkspace";
import "./styles.css";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConnectedWorkspace
        publicDemo={import.meta.env.VITE_PUBLIC_DEMO === "true"}
        apiUrl={import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"}
      />
    </BrowserRouter>
  </React.StrictMode>,
);
