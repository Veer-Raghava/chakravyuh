import { readFileSync, writeFileSync, existsSync } from "node:fs";

const CONTENT = "/home/void/chakravyuh/.superpowers/brainstorm/4-1790265986/content";
const FDIR = CONTENT + "/fonts";
const b64 = (f) => readFileSync(`${FDIR}/${f}`).toString("base64");
const has = (f) => existsSync(`${FDIR}/${f}`);
const face = (fam, w, f) =>
  has(f)
    ? `@font-face{font-family:"${fam}";font-weight:${w};font-style:normal;font-display:swap;src:url(data:font/woff2;base64,${b64(f)}) format("woff2");}`
    : "";

// Every UI candidate + Plex Mono for figures. Missing files skip silently.
const FONTS = [
  face("Hanken Grotesk", 400, "Hanken-400.woff2"),
  face("Hanken Grotesk", 500, "Hanken-500.woff2"),
  face("Hanken Grotesk", 600, "Hanken-600.woff2"),
  face("Instrument Sans", 400, "Instrument-400.woff2"),
  face("Instrument Sans", 500, "Instrument-500.woff2"),
  face("Instrument Sans", 600, "Instrument-600.woff2"),
  face("Work Sans", 400, "Work-400.woff2"),
  face("Work Sans", 500, "Work-500.woff2"),
  face("Work Sans", 600, "Work-600.woff2"),
  face("Fira Sans", 400, "FiraSans-Regular.woff2"),
  face("Fira Sans", 500, "FiraSans-Medium.woff2"),
  face("Fira Sans", 600, "FiraSans-Medium.woff2"),
  face("IBM Plex Sans", 400, "IBMPlexSans-Regular.woff2"),
  face("IBM Plex Sans", 500, "IBMPlexSans-Medium.woff2"),
  face("IBM Plex Sans", 600, "IBMPlexSans-SemiBold.woff2"),
  // optional high-character faces if the user downloads them
  face("Space Grotesk", 400, "SpaceGrotesk-400.woff2"),
  face("Space Grotesk", 500, "SpaceGrotesk-500.woff2"),
  face("Space Grotesk", 600, "SpaceGrotesk-600.woff2"),
  face("Geist", 400, "Geist-400.woff2"),
  face("Geist", 500, "Geist-500.woff2"),
  face("Geist", 600, "Geist-600.woff2"),
  face("Archivo", 400, "Archivo-400.woff2"),
  face("Archivo", 500, "Archivo-500.woff2"),
  face("Archivo", 600, "Archivo-600.woff2"),
  face("Mono", 400, "IBMPlexMono-Regular.woff2"),
  face("Mono", 500, "IBMPlexMono-Medium.woff2"),
  face("Mono", 600, "IBMPlexMono-SemiBold.woff2"),
].filter(Boolean).join("\n");

// UI faces to compare. `have` gates the optional downloads.
const FACES = [
  { id: "IBM Plex Sans", note: "engineered, technical — sibling of the Plex Mono figures, one coherent instrument voice", rec: true },
  { id: "Hanken Grotesk", note: "warm neutral grotesque — friendly, the current pick" },
  { id: "Instrument Sans", note: "compact modern grotesque — a little editorial" },
  { id: "Fira Sans", note: "humanist and sturdy — more character in the letterforms" },
  { id: "Work Sans", note: "clean geometric — quiet, understated" },
  { id: "Space Grotesk", note: "distinctive technical display — quirky, strong identity", opt: true },
  { id: "Geist", note: "modern technical (Vercel) — crisp, neutral", opt: true },
  { id: "Archivo", note: "grotesque with presence — confident headings", opt: true },
].filter((f) => !f.opt || has(`${f.id.replace(/ /g, "")}-400.woff2`) || has(`${f.id.split(" ")[0]}-400.woff2`));

// Five restrained light directions. Accent = the transformation / selection, under ~5% of pixels.
const PALS = [
  { id: "A", name: "Warm Paper · Terracotta", sem: "archival warmth; the accent marks the moment a field is transformed",
    v: "--bg:#F3EFE7;--panel:#FCFBF8;--line:#EBE5DA;--linehi:#D8D1C2;--ink:#1F1C17;--dim:#726B60;--mute:#ADA595;--faint:#C9C2B4;--signal:#B4550E;--sig-soft:#E4C9AE;--ok:#3C8B61;" },
  { id: "B", name: "Soft Ivory · Muted Blue", sem: "official, forensic; cool accent reads as a system decision on a warm page",
    v: "--bg:#F4F2EC;--panel:#FCFBF7;--line:#E8E4DA;--linehi:#D5D0C4;--ink:#1E1D1A;--dim:#6C6960;--mute:#A8A498;--faint:#C6C2B4;--signal:#3E6E8E;--sig-soft:#CBDCE6;--ok:#3C8B61;" },
  { id: "C", name: "Cool Paper · Teal", sem: "clean and technical; teal signals an active, verified transform",
    v: "--bg:#EEF1EE;--panel:#FBFCFB;--line:#E0E5E1;--linehi:#CDD4CE;--ink:#182020;--dim:#5F6B67;--mute:#9AA6A0;--faint:#BCC6C0;--signal:#1F7A6D;--sig-soft:#C4DED8;--ok:#B4550E;" },
  { id: "D", name: "Pale Sage · Forest", sem: "quiet and natural; forest accent for provenance and origin",
    v: "--bg:#EDEFE7;--panel:#FAFBF6;--line:#E1E4D8;--linehi:#CDD2C2;--ink:#1B1F18;--dim:#616A5A;--mute:#9AA28F;--faint:#BEC5B2;--signal:#3B6E43;--sig-soft:#CBDDC4;--ok:#B4550E;" },
  { id: "E", name: "Neutral White · Restrained Violet", sem: "restrained, modern; violet as a neutral 'attention' accent (note: breaks the earlier no-violet rule)",
    v: "--bg:#F2F1F3;--panel:#FCFBFD;--line:#E6E4E9;--linehi:#D3D0DA;--ink:#1C1B1F;--dim:#67646E;--mute:#A3A0AB;--faint:#C4C1CC;--signal:#6A5A9E;--sig-soft:#D8D2E8;--ok:#3C8B61;" },
  { id: "F", name: "Pure White · Monochrome", sem: "stark and minimal; the accent is ink itself — the transform reads by weight, not colour",
    v: "--bg:#FFFFFF;--panel:#FFFFFF;--line:#ECECEC;--linehi:#DBDBDB;--ink:#101010;--dim:#5E5E5E;--mute:#969696;--faint:#C4C4C4;--signal:#101010;--sig-soft:#E4E4E4;--ok:#3C8B61;" },
  { id: "G", name: "Pure Dark · Instrument", sem: "the dark room; warm accent glows against near-black for the one thing that moved",
    v: "--bg:#0E0E10;--panel:#161619;--line:#242429;--linehi:#33333A;--ink:#ECEAE6;--dim:#9A9AA2;--mute:#6C6C74;--faint:#45454D;--signal:#D07B33;--sig-soft:#3A2A1B;--ok:#4FA875;" },
];

const STAGES = [
  { k: "MAYAJAAL", in: "—", out: "41,594" },
  { k: "KAVACH", in: "41,594", out: "41,594" },
  { k: "SETU", in: "41,594", out: "41,594", sel: true },
  { k: "JAAL", in: "1", out: "3" },
  { k: "SHASTRA", in: "1", out: "0.87" },
  { k: "BUDDHI", in: "1", out: "0.78" },
  { k: "VAANI", in: "1", out: "1" },
  { k: "PRAMAAN", in: "1", out: "1" },
];

const MAP = [
  { t: "rename", hero: true, from: "src_ip", to: "peer_ip", v: "103.x.x.x" },
  { t: "rename", from: "dst_ip", to: "observer_ip", v: "45.x.x.x" },
  { t: "enrich", f: "geo_country", before: "null", v: "IN" },
  { t: "enrich", f: "asn", before: "null", v: "AS9829" },
  { t: "born", f: "rank_in_tx", v: "1" },
  { t: "born", f: "net_class", v: "residential" },
  { t: "kept", f: "row_id", v: "418826" },
  { t: "kept", f: "txid", v: "a91f4c2d…9f4d" },
  { t: "kept", f: "ts_raw", v: "2026-02-14T09:41:02Z" },
];

const CSS = `
*{margin:0;padding:0;box-sizing:border-box}
:root{
  ${PALS[3].v}
  --ui:"Hanken Grotesk",system-ui,sans-serif; --mono:"Mono",ui-monospace,monospace;
  /* ONE scale, six steps, each with a job. No values off this ladder. */
  --fs-label:11px;  /* uppercase tracked labels, nav, status, captions */
  --fs-data:12px;   /* mono figures, small values */
  --fs-body:13px;   /* prose */
  --fs-h2:16px;     /* section + seam heading */
  --fs-hero:22px;   /* the SETU rename, the one focal figure */
  --fs-h1:34px;     /* page / screen title */
}
html,body{background:var(--desk,#E4DED2);color:var(--ink);font-family:var(--ui);
  font-size:var(--fs-body);line-height:1.5;-webkit-font-smoothing:antialiased;}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1;}
.page{max-width:1160px;margin:0 auto;padding:36px 30px 90px;}

/* section scaffolding for the exploration doc */
.lead{font-size:var(--fs-body);color:var(--dim);margin-bottom:8px;}
.lead b{color:var(--ink);font-weight:600;}
.sec{margin-top:56px;}
.sec-h{display:flex;align-items:baseline;gap:12px;padding-bottom:12px;border-bottom:1px solid var(--linehi);margin-bottom:24px;}
.sec-n{font-family:var(--mono);font-size:var(--fs-data);color:var(--signal);}
.sec-t{font-size:var(--fs-h2);font-weight:600;color:var(--ink);}
.sec-d{font-size:var(--fs-label);color:var(--mute);letter-spacing:.02em;margin-left:auto;text-align:right;}

/* ---- typeface specimens ---- */
.specs{display:flex;flex-direction:column;gap:2px;}
.spec{padding:20px 18px;border:1px solid transparent;border-radius:3px;cursor:pointer;font-family:var(--ui);}
.spec:hover{background:var(--panel);}
.spec.on{background:var(--panel);border-color:var(--linehi);}
.spec-top{display:flex;align-items:baseline;gap:12px;margin-bottom:12px;}
.spec-name{font-size:var(--fs-body);font-weight:600;color:var(--ink);}
.spec-rec{font-family:var(--mono);font-size:var(--fs-label);color:var(--signal);letter-spacing:.04em;}
.spec-note{font-size:var(--fs-label);color:var(--dim);letter-spacing:.01em;}
.spec-body .sl{font-size:var(--fs-h1);font-weight:600;letter-spacing:-.015em;line-height:1;color:var(--ink);}
.spec-body .sg{margin-top:8px;font-size:var(--fs-h2);color:var(--dim);letter-spacing:.01em;}
.spec-body .snav{margin-top:10px;font-size:var(--fs-label);letter-spacing:.13em;text-transform:uppercase;color:var(--mute);font-weight:600;}
.spec-body .srow{margin-top:12px;display:flex;align-items:baseline;gap:10px;}
.spec-body .srow .k{font-family:var(--mono);font-size:var(--fs-data);color:var(--dim);}
.spec-body .srow .ar{font-family:var(--mono);color:var(--signal);}
.spec-body .srow .kk{font-size:var(--fs-body);font-weight:600;color:var(--signal);}
.spec-body .srow .vv{font-family:var(--mono);font-size:var(--fs-data);color:var(--ink);}

/* ---- palette directions ---- */
.pals{display:flex;flex-direction:column;gap:14px;}
.pal{border:1px solid var(--linehi);border-radius:3px;overflow:hidden;cursor:pointer;background:var(--panel);}
.pal.on{outline:2px solid var(--signal);outline-offset:-2px;}
.pal-grid{display:grid;grid-template-columns:280px 1fr;}
.pal-meta{padding:18px 18px;border-right:1px solid var(--line);}
.pal-name{font-size:var(--fs-body);font-weight:600;color:var(--ink);}
.pal-sem{font-size:var(--fs-label);color:var(--dim);margin-top:6px;line-height:1.45;}
.sw{display:flex;gap:0;margin-top:14px;border:1px solid var(--line);border-radius:2px;overflow:hidden;width:fit-content;}
.sw i{width:26px;height:20px;display:block;}
.pal-prev{padding:20px 22px;}

/* ---- spine (shared by palette preview + full screen) ---- */
.spine{display:grid;position:relative;}
.spine.full{grid-template-columns:repeat(8,1fr);}
.spine.mini{grid-template-columns:repeat(4,1fr);max-width:520px;}
.spine::before{content:"";position:absolute;left:calc(100%/16);right:calc(100%/16);top:22px;height:1px;background:var(--linehi);z-index:0;}
.spine.mini::before{top:20px;}
.node{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;gap:9px;padding:6px 4px;}
.n-in{font-family:var(--mono);font-size:var(--fs-label);color:var(--mute);height:13px;}
.lamp{width:9px;height:9px;border-radius:50%;background:var(--panel);border:1.5px solid var(--faint);}
.n-name{font-size:var(--fs-label);letter-spacing:.13em;text-transform:uppercase;color:var(--mute);font-weight:600;}
.n-out{font-family:var(--mono);font-size:var(--fs-data);color:var(--dim);height:15px;}
.node.sel .lamp{width:15px;height:15px;background:var(--signal);border:none;box-shadow:0 0 0 4px var(--sig-soft);}
.node.sel .n-name{color:var(--ink);} .node.sel .n-out{color:var(--ink);font-weight:500;}
.node.sel::after{content:"";position:absolute;bottom:-3px;width:20px;height:2px;background:var(--signal);}

/* ---- before/after map (shared) ---- */
.map{display:flex;flex-direction:column;gap:2px;}
.mrow{display:grid;grid-template-columns:1fr 150px 1fr;align-items:center;padding:7px 0;}
.mb{text-align:right;} .ma{text-align:left;}
.fn{font-family:var(--mono);font-size:var(--fs-data);color:var(--dim);}
.fv{font-family:var(--mono);font-size:var(--fs-data);color:var(--ink);margin:0 .5ch;}
.fv.dim{color:var(--mute);} .fv.strike{color:var(--faint);text-decoration:line-through;}
.mc{position:relative;display:flex;align-items:center;justify-content:center;height:100%;}
.cline{position:absolute;left:0;right:0;top:50%;height:1px;background:var(--line);}
.cmk{position:relative;z-index:1;background:var(--panel);padding:0 8px;font-family:var(--mono);font-size:var(--fs-data);color:var(--signal);}
.mrow.kept .fn{color:var(--mute);} .mrow.kept .cmk{display:none;}
.mrow.rename .cline,.mrow.enrich .cline{background:var(--sig-soft);}
.mrow.born .cline{left:50%;background:var(--sig-soft);}
.sig{color:var(--signal)!important;}
.mrow.hero{padding:15px 0;}
.mrow.hero .fn,.mrow.hero .fv,.mrow.hero .cmk{font-size:var(--fs-hero);}
.mrow.hero .mb .fn{color:var(--dim);} .mrow.hero .ma .fn{color:var(--signal);font-weight:600;}
.mrow.hero .ma .fv{color:var(--ink);font-weight:500;}
.pulse{animation:pulse 2.6s ease-out 1;}
@keyframes pulse{0%{background:transparent}20%{background:var(--sig-soft)}100%{background:transparent}}

/* ---- full LINEAGE frame ---- */
.frame{background:var(--bg);border:1px solid var(--linehi);border-radius:3px;overflow:hidden;font-family:var(--ui);}
.bar{display:flex;align-items:center;gap:20px;padding:9px 18px;border-bottom:1px solid var(--line);background:var(--panel);
  font-size:var(--fs-label);color:var(--mute);letter-spacing:.06em;text-transform:uppercase;}
.bar .airgap{color:var(--dim);font-weight:600;} .bar .sp{flex:1;}
.bar .dot{width:5px;height:5px;border-radius:50%;background:var(--ok);display:inline-block;margin-right:6px;vertical-align:middle;}
.bar .run{font-family:var(--mono);letter-spacing:.02em;text-transform:none;color:var(--dim);}
.body{display:grid;grid-template-columns:172px 1fr;}
.rail{border-right:1px solid var(--line);background:var(--panel);padding:22px 0;display:flex;flex-direction:column;min-height:640px;}
.brand{padding:0 20px 22px;font-size:var(--fs-data);font-weight:600;letter-spacing:.28em;color:var(--ink);text-transform:uppercase;}
.navsec{padding:16px 20px 6px;font-size:var(--fs-label);letter-spacing:.16em;text-transform:uppercase;color:var(--mute);font-weight:600;}
.nav{display:flex;flex-direction:column;}
.nav a{padding:6px 20px;font-size:var(--fs-label);letter-spacing:.1em;text-transform:uppercase;color:var(--dim);font-weight:500;border-left:2px solid transparent;}
.nav a.on{color:var(--ink);font-weight:600;border-left-color:var(--signal);}
.rail .foot{margin-top:auto;padding:16px 20px 0;border-top:1px solid var(--line);font-size:var(--fs-label);letter-spacing:.06em;text-transform:uppercase;color:var(--mute);}
.themes{display:flex;gap:8px;margin-top:12px;}
.themes b{width:16px;height:16px;border-radius:50%;cursor:pointer;border:1px solid var(--linehi);position:relative;}
.themes b.on{box-shadow:0 0 0 2px var(--panel),0 0 0 3px var(--ink);}
.main{padding:32px 40px 44px;}
.head{display:flex;align-items:flex-end;justify-content:space-between;}
.h1{font-size:var(--fs-h1);font-weight:600;letter-spacing:-.015em;line-height:1;color:var(--ink);}
.sub{font-size:var(--fs-body);color:var(--dim);margin-top:10px;max-width:52ch;}
.rec{text-align:right;font-size:var(--fs-label);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);}
.rec .rid{display:block;font-family:var(--mono);font-size:var(--fs-data);letter-spacing:0;text-transform:none;color:var(--ink);margin-top:5px;}
.spine-wrap{margin:44px 0 4px;}
.fork{grid-column:3;justify-self:center;margin-top:14px;font-family:var(--mono);font-size:var(--fs-label);color:var(--signal);letter-spacing:.02em;}
.trans{margin:56px 0 24px;}
.trans .seam{font-size:var(--fs-h2);font-weight:600;color:var(--ink);}
.trans .seam .ar{color:var(--signal);margin:0 9px;font-family:var(--mono);}
.trans .say{font-size:var(--fs-body);color:var(--dim);margin-top:6px;max-width:62ch;}
.mhead{display:grid;grid-template-columns:1fr 150px 1fr;margin-bottom:14px;font-size:var(--fs-label);letter-spacing:.16em;text-transform:uppercase;color:var(--mute);font-weight:600;}
.mhead .l{text-align:right;} .mhead .r{text-align:left;}
.bal{margin-top:42px;padding-top:16px;border-top:1px solid var(--line);display:flex;align-items:center;gap:12px;font-family:var(--mono);font-size:var(--fs-data);color:var(--dim);}
.bal .eq{color:var(--ink);} .bal .ok{color:var(--ok);}
.bal .cap{font-family:var(--ui);font-size:var(--fs-label);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin-left:auto;}
`;

const node = (s) => `
  <div class="node${s.sel ? " sel" : ""}">
    <span class="n-in">${s.in}</span><span class="lamp"></span>
    <span class="n-name">${s.k}</span><span class="n-out">${s.out}</span>
  </div>`;

const mrow = (r) => {
  if (r.t === "kept")
    return `<div class="mrow kept"><div class="mb"><span class="fn">${r.f}</span><span class="fv dim">${r.v}</span></div>
      <div class="mc"><span class="cline"></span></div><div class="ma"><span class="fv dim">${r.v}</span></div></div>`;
  if (r.t === "rename")
    return `<div class="mrow rename${r.hero ? " hero pulse" : ""}"><div class="mb"><span class="fn">${r.from}</span></div>
      <div class="mc"><span class="cline"></span><span class="cmk">&rarr;</span></div>
      <div class="ma"><span class="fn sig">${r.to}</span><span class="fv">${r.v}</span></div></div>`;
  if (r.t === "enrich")
    return `<div class="mrow enrich"><div class="mb"><span class="fn">${r.f}</span><span class="fv strike">${r.before}</span></div>
      <div class="mc"><span class="cline"></span><span class="cmk">&rarr;</span></div>
      <div class="ma"><span class="fv sig">${r.v}</span></div></div>`;
  return `<div class="mrow born"><div class="mb"></div>
    <div class="mc"><span class="cline"></span><span class="cmk">+</span></div>
    <div class="ma"><span class="fn sig">${r.f}</span><span class="fv">${r.v}</span></div></div>`;
};

const specimen = (f) => `
  <div class="spec" style="--ui:'${f.id}',system-ui,sans-serif" onclick="pickFace(this,'${f.id}')">
    <div class="spec-top"><span class="spec-name">${f.id}</span>${f.rec ? '<span class="spec-rec">recommended</span>' : ""}
      <span class="spec-note">${f.note}</span></div>
    <div class="spec-body">
      <div class="sl">Lineage</div>
      <div class="sg">Rag 0123456789 &middot; a g Q R j &amp; kty</div>
      <div class="snav">Intake &middot; Lineage &middot; Graph &middot; Origin &middot; Risk &middot; Evidence</div>
      <div class="srow"><span class="k">src_ip</span><span class="ar">&rarr;</span>
        <span class="kk">peer_ip</span><span class="vv">103.x.x.x</span></div>
    </div>
  </div>`;

const MINI = [STAGES[1], { ...STAGES[2] }, STAGES[3], STAGES[4]];
const palette = (p) => `
  <div class="pal" style="${p.v}" onclick="pickPal(this,'${p.v}')">
    <div class="pal-grid">
      <div class="pal-meta">
        <div class="pal-name">${p.id} &middot; ${p.name}</div>
        <div class="pal-sem">${p.sem}</div>
        <div class="sw">
          <i style="background:var(--bg)"></i><i style="background:var(--panel)"></i>
          <i style="background:var(--linehi)"></i><i style="background:var(--mute)"></i>
          <i style="background:var(--dim)"></i><i style="background:var(--ink)"></i>
          <i style="background:var(--signal)"></i><i style="background:var(--sig-soft)"></i>
        </div>
      </div>
      <div class="pal-prev">
        <div class="spine mini">${MINI.map(node).join("")}</div>
        <div class="map" style="margin-top:14px">${mrow(MAP[0])}</div>
      </div>
    </div>
  </div>`;

const HTML = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>DRISHTI — visual identity</title>
<style>${FONTS}\n${CSS}</style></head>
<body><div class="page">
  <div class="lead"><b>DRISHTI visual identity</b> — final exploration before lock. Type scale is fixed to six steps (11 / 12 / 13 / 16 / 22 / 34). Mockup only, not committed code.</div>

  <div class="sec">
    <div class="sec-h"><span class="sec-n">01</span><span class="sec-t">Typeface</span>
      <span class="sec-d">figures always IBM Plex Mono · click to compare</span></div>
    <div class="specs">${FACES.map(specimen).join("")}</div>
  </div>

  <div class="sec">
    <div class="sec-h"><span class="sec-n">02</span><span class="sec-t">Palette direction</span>
      <span class="sec-d">accent under ~5% of pixels · click to compare</span></div>
    <div class="pals">${PALS.map(palette).join("")}</div>
  </div>

  <div class="sec">
    <div class="sec-h"><span class="sec-n">03</span><span class="sec-t">Lineage — refined</span>
      <span class="sec-d">LOCKED default: Hanken Grotesk + Pale Sage · click any face or swatch to preview others</span></div>
    <div class="frame" id="screen">
      <div class="bar"><span class="airgap"><span class="dot"></span>AIR-GAPPED</span>
        <span>OFFLINE</span><span>SEED 42</span><span class="sp"></span>
        <span class="run">run _sweep-0.10 &middot; sha f3977f4c</span></div>
      <div class="body">
        <div class="rail">
          <div class="brand">Drishti</div>
          <div class="navsec">Pipeline</div>
          <div class="nav"><a>Intake</a><a class="on">Lineage</a><a>Graph</a><a>Origin</a><a>Risk</a><a>Explain</a><a>Evidence</a></div>
          <div class="navsec">Case</div>
          <div class="nav"><a>Queue</a><a>Notebook</a></div>
          <div class="foot">Theme
            <div class="themes">${PALS.map((p, i) => `<b title="${p.name}"${i === 3 ? ' class="on"' : ""} style="background:${p.v.match(/--signal:([^;]+)/)[1]}" onclick="setTheme(this,'${p.v}')"></b>`).join("")}</div>
          </div>
        </div>
        <div class="main">
          <div class="head">
            <div><div class="h1">Lineage</div>
              <div class="sub">One captured row, followed across all eight stages &mdash; every rename, enrichment and field it gains on the way.</div></div>
            <div class="rec">Tracing record<span class="rid">418826</span></div>
          </div>
          <div class="spine-wrap"><div class="spine full">${STAGES.map(node).join("")}
            <div class="fork">splits &rarr; 8,495 transactions</div></div></div>
          <div class="trans"><div class="seam">KAVACH<span class="ar">&rarr;</span>SETU</div>
            <div class="say">Where the sealed row becomes a normalised announcement: two fields are renamed, nulls are enriched, and three fields are born.</div></div>
          <div class="mhead"><span class="l">Sealed row</span><span></span><span class="r">Announcement</span></div>
          <div class="map">${MAP.map(mrow).join("")}</div>
          <div class="bal"><span>in</span><span class="eq">41,594</span><span>==</span>
            <span class="eq">41,594</span><span>out</span><span>+</span><span class="eq">0</span><span>dropped</span>
            <span class="ok">&check;</span><span class="cap">Counts balance</span></div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
var screen=function(){return document.getElementById('screen')};
function hi(el){var p=el.parentNode;p.querySelectorAll(':scope > .spec, :scope > .pal, :scope > b').forEach(function(x){x.classList.remove('on')});el.classList.add('on');}
function applyTheme(v){var s=screen();v.split(';').forEach(function(d){var kv=d.split(':');if(kv[0].trim())s.style.setProperty(kv[0].trim(),kv[1].trim());});}
function pickFace(el,id){hi(el);screen().style.setProperty('--ui',"'"+id+"',system-ui,sans-serif");}
function pickPal(el,v){hi(el);applyTheme(v);}
function setTheme(el,v){hi(el);applyTheme(v);}
</script>
</body></html>`;

writeFileSync(`${CONTENT}/identity.html`, HTML);
writeFileSync("/home/void/chakravyuh/apps/drishti/public/theme-preview.html", HTML);
console.log(`wrote identity mockup (${HTML.length} bytes) · faces=${FACES.length} pals=${PALS.length}`);


