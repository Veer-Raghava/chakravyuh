import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/tokens.css";
import "./styles/global.css";
import { App } from "./App";
import { Primitives } from "./routes/Primitives";
import { Lineage } from "./routes/Lineage";
import { initAppearance } from "./theme";

// Pale Sage + Hanken Grotesk unless a prior choice was persisted. Applied before
// render so the first paint is already themed.
initAppearance();

// No router dependency: scratch routes branched off the path. Vite's SPA fallback
// serves index.html for these in dev and preview.
const path = window.location.pathname;
const Root = path === "/_primitives" ? Primitives : path === "/_lineage" ? Lineage : App;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
