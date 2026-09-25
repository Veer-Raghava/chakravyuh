// Theme and UI-face selection. Purely presentational: it sets two attributes on
// <html> and persists the choice. It never touches the adapter, so switching cannot
// change any data the console shows. Defaults are Pale Sage + Hanken Grotesk.

export const THEMES = [
  { id: "sage", label: "Pale Sage" },
  { id: "paper", label: "Warm Paper" },
  { id: "ivory", label: "Soft Ivory" },
  { id: "cool", label: "Cool Paper" },
  { id: "violet", label: "Restrained Violet" },
  { id: "white", label: "Pure White" },
  { id: "dark", label: "Instrument Dark" },
] as const;

export const FONTS = [
  { id: "hanken", label: "Hanken Grotesk" },
  { id: "plex-sans", label: "IBM Plex Sans" },
  { id: "instrument", label: "Instrument Sans" },
  { id: "fira", label: "Fira Sans" },
  { id: "work", label: "Work Sans" },
  { id: "space-grotesk", label: "Space Grotesk" },
  { id: "geist", label: "Geist" },
  { id: "archivo", label: "Archivo" },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];
export type FontId = (typeof FONTS)[number]["id"];

const DEFAULT_THEME: ThemeId = "sage";
const DEFAULT_FONT: FontId = "hanken";

const THEME_KEY = "drishti.theme";
const FONT_KEY = "drishti.font";

function read<T extends string>(key: string, allowed: readonly { id: string }[], fallback: T): T {
  const v = localStorage.getItem(key);
  return allowed.some((a) => a.id === v) ? (v as T) : fallback;
}

export function getTheme(): ThemeId {
  return read(THEME_KEY, THEMES, DEFAULT_THEME);
}
export function getFont(): FontId {
  return read(FONT_KEY, FONTS, DEFAULT_FONT);
}

export function applyTheme(id: ThemeId): void {
  document.documentElement.setAttribute("data-theme", id);
  localStorage.setItem(THEME_KEY, id);
}
export function applyFont(id: FontId): void {
  document.documentElement.setAttribute("data-font", id);
  localStorage.setItem(FONT_KEY, id);
}

// Called once at startup, before React renders, so there is no unstyled flash.
export function initAppearance(): void {
  document.documentElement.setAttribute("data-theme", getTheme());
  document.documentElement.setAttribute("data-font", getFont());
}
