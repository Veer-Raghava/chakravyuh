/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SOURCE?: "fixtures" | "api";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
