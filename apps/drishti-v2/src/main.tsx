import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ScrollProvider } from "./scroll/ScrollContext";
import App from "./App";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ScrollProvider>
      <App />
    </ScrollProvider>
  </StrictMode>,
);
