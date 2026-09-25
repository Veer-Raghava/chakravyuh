// Vendor the exact IBM Plex woff2 files the console needs out of the installed
// @fontsource packages into public/fonts, so the app never fetches a font at runtime.
// Runs as a postinstall step; safe to run again.
//
// The seven switchable UI faces (Hanken Grotesk, Instrument Sans, Work Sans, Fira Sans,
// Space Grotesk, Geist, Archivo) are committed directly under public/fonts/ — they are
// not on @fontsource in this offline setup, so this script does not manage them.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const out = resolve(root, "public/fonts");
mkdirSync(out, { recursive: true });

// Three weights only (400/500/600), latin subset, both faces.
const map = [
  ["ibm-plex-sans/files/ibm-plex-sans-latin-400-normal.woff2", "IBMPlexSans-Regular.woff2"],
  ["ibm-plex-sans/files/ibm-plex-sans-latin-500-normal.woff2", "IBMPlexSans-Medium.woff2"],
  ["ibm-plex-sans/files/ibm-plex-sans-latin-600-normal.woff2", "IBMPlexSans-SemiBold.woff2"],
  ["ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2", "IBMPlexMono-Regular.woff2"],
  ["ibm-plex-mono/files/ibm-plex-mono-latin-500-normal.woff2", "IBMPlexMono-Medium.woff2"],
  ["ibm-plex-mono/files/ibm-plex-mono-latin-600-normal.woff2", "IBMPlexMono-SemiBold.woff2"],
];

for (const [src, dst] of map) {
  copyFileSync(resolve(root, "node_modules/@fontsource", src), resolve(out, dst));
}
console.log(`vendored ${map.length} font files into public/fonts`);
