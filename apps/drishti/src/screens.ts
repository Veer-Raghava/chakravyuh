/** The eight screens, in order. Each is one beat of the demo and one verdict line from
 *  the deck. The key is the digit that jumps to it; `shortcuts` are the per-screen keys
 *  printed at the foot of the rail. Owned here so the Rail and the router never disagree. */
export interface Screen {
  key: string; // "1".."8"
  id: string; // short name shown in the rail
  verdict: string; // the one-line claim from DRISHTI-SPEC
  shortcuts: { keys: string; does: string }[];
}

export const SCREENS: Screen[] = [
  {
    key: "1",
    id: "INTAKE",
    verdict: "it never breaks on their file",
    shortcuts: [
      { keys: "j / k", does: "move row" },
      { keys: "enter", does: "open reject" },
    ],
  },
  {
    key: "2",
    id: "COLLAPSE",
    verdict: "one million rows is not one million events",
    shortcuts: [{ keys: "space", does: "collapse" }],
  },
  {
    key: "3",
    id: "ORIGIN",
    verdict: "we can tell who sent it from who repeated it",
    shortcuts: [
      { keys: "j / k", does: "move tx" },
      { keys: "space", does: "reveal origin" },
    ],
  },
  {
    key: "4",
    id: "GRAPH",
    verdict: "both layers, one picture",
    shortcuts: [
      { keys: "hover", does: "isolate node" },
      { keys: "esc", does: "reset view" },
    ],
  },
  {
    key: "5",
    id: "QUEUE",
    verdict: "twenty leads, ranked, each with its counter-argument",
    shortcuts: [
      { keys: "j / k", does: "move lead" },
      { keys: "enter", does: "open" },
      { keys: "/", does: "filter" },
    ],
  },
  {
    key: "6",
    id: "PACKET",
    verdict: "it holds up in court",
    shortcuts: [{ keys: "c", does: "copy replay" }],
  },
  {
    key: "7",
    id: "LINEAGE",
    verdict: "every field, traced to the stage that made it",
    shortcuts: [
      { keys: "1 – 8", does: "move stage" },
      { keys: "↑ / ↓", does: "move record" },
      { keys: "enter", does: "drill in" },
      { keys: "space", does: "collapse" },
    ],
  },
  {
    key: "8",
    id: "DATA",
    verdict: "the sealed rows, exactly as the pipeline read them",
    shortcuts: [
      { keys: "click", does: "sort column" },
      { keys: "scroll", does: "page rows" },
    ],
  },
];
