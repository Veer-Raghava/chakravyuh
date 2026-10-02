import { STAGES, type StageId } from "../nav/stages";
import { useRun } from "../data/RunContext";
import { useShell } from "./ShellContext";
import styles from "./CaseRibbon.module.css";
const intent: Record<StageId, [string, string]> = {
  globe: [
    "Start with the observation",
    "Choose a trail, then follow the same transaction into JAAL.",
  ],
  intake: [
    "Trust starts with the capture",
    "Inspect source hashes, row balance and rejected records before interpreting the data.",
  ],
  untangle: [
    "One transaction. Many echoes.",
    "Separate value transfer from the peers that relayed it.",
  ],
  map: [
    "Follow the money",
    "Read the flow atlas, compare ownership hypotheses, then open the full 3D trace.",
  ],
  origin: [
    "Compare the candidate trail",
    "Timing and peer behavior support a shortlist. A relay is an observation, not an identity.",
  ],
  leads: [
    "Spend attention where it matters",
    "Review ranked evidence, inspect mitigating factors and carry a case into its packet.",
  ],
  proof: [
    "An evidence trail you can carry",
    "Inspect the selected case, its provenance and the exact artifact before exporting.",
  ],
  world: [
    "Understand the world behind the evidence",
    "Explore this capture’s coverage and the independently measured research engine.",
  ],
};
export function CaseRibbon() {
  const { stage, goTo, closeDrawer } = useShell();
  const {
    run,
    fixtures,
    has,
    selectedTx,
    selectedAlert,
    selectTx,
    selectAlert,
  } = useRun();
  const tx = selectedTx?.replace(/^tx:/, "");
  const jump = (id: StageId) => {
    closeDrawer();
    goTo(id);
  };
  return (
    <aside className={styles.ribbon} aria-label="Investigation context">
      <div className={styles.intent}>
        <span className={styles.layer}>
          {STAGES.find((s) => s.id === stage)?.tag || "DRISHTI"}
        </span>
        <strong>{intent[stage][0]}</strong>
        <p>{intent[stage][1]}</p>
      </div>
      <div className={styles.context}>
        <span>
          {run.label} · {run.coverageLabel}
        </span>
        <strong>
          {selectedAlert
            ? `Case ${selectedAlert.slice(0, 16)}`
            : tx
              ? `TX ${tx.slice(0, 10)}…${tx.slice(-6)}`
              : has("transactions")
                ? `${fixtures.transactions.transactions.length} transactions in the exported view`
                : "Select an observation to begin"}
        </strong>
        {(selectedTx || selectedAlert) && (
          <button
            type="button"
            onClick={() => {
              selectTx(null);
              selectAlert(null);
              closeDrawer();
            }}
          >
            Clear selection
          </button>
        )}
      </div>
      <div className={styles.actions}>
        <button
          type="button"
          onClick={() =>
            jump(
              stage === "world"
                ? "globe"
                : stage === "proof"
                  ? "leads"
                  : STAGES[
                      Math.min(STAGES.findIndex((s) => s.id === stage) + 1, 6)
                    ].id,
            )
          }
        >
          {stage === "world"
            ? "Start investigating"
            : stage === "proof"
              ? "Back to leads"
              : `Continue to ${STAGES[Math.min(STAGES.findIndex((s) => s.id === stage) + 1, 6)].name}`}{" "}
          →
        </button>
      </div>
    </aside>
  );
}
