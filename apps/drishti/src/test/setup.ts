import "@testing-library/jest-dom";

// This Node/jsdom build ships no localStorage (needs --localstorage-file) and no
// matchMedia. Appearance reads persisted theme/font on mount and components probe
// prefers-reduced-motion, so give both a minimal in-memory stub for the test env.
if (!("localStorage" in globalThis) || globalThis.localStorage == null) {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => [...store.keys()][i] ?? null,
      get length() {
        return store.size;
      },
    },
  });
}

if (typeof globalThis.matchMedia !== "function") {
  globalThis.matchMedia = (query: string) =>
    ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList;
}
