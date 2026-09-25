/**
 * The DRISHTI ECharts theme. ECharts out of the box looks like ECharts, and looking like
 * ECharts is looking generic, so every default is overridden here: no title, no legend
 * unless two series overlap, axis lines in --line, no gridlines, mono micro tick labels,
 * a hairline tooltip on --bg-raise with no shadow, and no animation on data update.
 *
 * Colours are not literals here — canvas cannot read CSS variables, so we pull the token
 * values off :root at register time. tokens.css stays the single source of colour.
 *
 * echarts is injected rather than imported so this file has no hard dependency on the
 * package: call registerDrishtiTheme(echarts) once at startup, then use theme "drishti".
 */

type EChartsLike = { registerTheme(name: string, theme: Record<string, unknown>): void };

function token(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

/** Build the theme object from the current token values. */
export function drishtiTheme(): Record<string, unknown> {
  const bgRaise = token("--bg-raise", "#ffffff");
  const line = token("--line", "#e1e4d8");
  const ink = token("--ink", "#1b1f18");
  const inkDim = token("--ink-dim", "#616a5a");
  const inkMute = token("--ink-mute", "#9aa28f");
  const signal = token("--signal", "#3b6e43");
  const cool = token("--cool", "#5e7687");
  const ok = token("--ok", "#2f7d6e");
  const mono = token("--font-mono", "IBM Plex Mono, ui-monospace, monospace");

  const axisLabel = { color: inkDim, fontFamily: mono, fontSize: 11 };
  const axisLine = { lineStyle: { color: line } };

  return {
    color: [signal, cool, ok, inkDim],
    backgroundColor: "transparent",
    textStyle: { fontFamily: mono, color: ink },
    animation: false,
    title: { show: false },
    legend: { show: false, textStyle: { color: inkDim, fontFamily: mono, fontSize: 11 } },
    grid: { borderColor: line, containLabel: true, left: 8, right: 8, top: 8, bottom: 8 },
    categoryAxis: {
      axisLine,
      axisTick: { show: false },
      axisLabel,
      splitLine: { show: false },
    },
    valueAxis: {
      axisLine,
      axisTick: { show: false },
      axisLabel,
      splitLine: { show: false },
    },
    tooltip: {
      backgroundColor: bgRaise,
      borderColor: line,
      borderWidth: 1,
      extraCssText: "box-shadow:none;border-radius:2px;",
      textStyle: { color: ink, fontFamily: mono, fontSize: 12 },
      axisPointer: { lineStyle: { color: inkMute }, crossStyle: { color: inkMute } },
    },
    line: { symbol: "none", lineStyle: { width: 1 } },
    bar: { itemStyle: { borderWidth: 0 } },
  };
}

/** Register the theme under the name "drishti". Call once at app startup. */
export function registerDrishtiTheme(echarts: EChartsLike): void {
  echarts.registerTheme("drishti", drishtiTheme());
}
