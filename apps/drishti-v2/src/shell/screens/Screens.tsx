import type { ReactNode } from "react";
import { STAGES, type StageId } from "../../nav/stages";
import { GlobeScreen } from "./GlobeScreen";
import { MapScreen } from "./MapScreen";
import { IntakeScreen } from "./IntakeScreen";
import { UntangleScreen } from "./UntangleScreen";
import { LeadsScreen } from "./LeadsScreen";
import { OriginScreen } from "./OriginScreen";
import { ProofScreen } from "./ProofScreen";
import { WorldScreen } from "./WorldScreen";
import styles from "./Screens.module.css";

/**
 * The eight stage screens (§11). For M3 these are wired stubs: a real, honest
 * header per stage (name · Sanskrit gloss · what the screen does · its funnel
 * number) — never "coming soon" or empty cards (§3 kill-list). The 3D screens
 * (Globe §9, Map §10, Origin §11.3) name the moment coming; Leads (§11.4) is the
 * one that renders live — the reusable AlertCard + the Properties drawer, so both
 * shared pieces are provably wired.
 */
function StageHeader({ id, children }: { id: StageId; children?: ReactNode }) {
  const s = STAGES.find((x) => x.id === id)!;
  const fmt = new Intl.NumberFormat("en-US");
  return (
    <section className={styles.screen}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{s.name}</h1>
          {s.tag && <span className={styles.tag}>{s.tag}</span>}
        </div>
        <p className={styles.gloss}>{s.gloss}</p>
        {s.count != null && (
          <p className={styles.count}>
            <span className={styles.countNum}>{fmt.format(s.count)}</span>
            <span className={styles.countLabel}>at this stage of the run</span>
          </p>
        )}
      </header>
      <div className={styles.content}>{children}</div>
    </section>
  );
}

const COPY: Record<StageId, string> = {
  globe: "The establishing shot — a paper-matte planet with announcement points where IPs geolocate. Click a point to see who was talking to whom. The 3D globe lands in a later milestone.",
  intake: "Pick a capture file and watch it get sealed: rows in, rows sealed, rows set aside with reasons. The file's full SHA-256 is printed here in full — the one identifier the law never lets us hide.",
  untangle: "The rename that defuses the trap — src_ip becomes the IP that told us. A spatial before/after across a centre seam shows network pulled apart from money.",
  map: "The centrepiece — two floors in 3D: peers on the wire above, addresses and transactions below, and the fluoro-pink announce threads are the only edges crossing between them. Built in a later milestone.",
  origin: "Candidate IPs on concentric rings where radius is inverse likelihood — nearest the centre is most likely. A confidence shell holds the shortlist; a calm grey fog-dome means no answer available.",
  leads: "The ranked queue. Twenty leads, not a thousand maybes. Each is the reusable Alert card — evidence and its own doubts, shown at the same moment.",
  proof: "One lead pressed into a signed, hash-chained document: an IP, a source port and an exact timestamp — the three values an ISP needs to name one subscriber.",
  world: "MAYAJAAL — the synthetic world we built so we can grade ourselves honestly. The observer-fraction curve and the measuring-stick flex live here.",
};

export function StageScreen({ id }: { id: StageId }) {
  if (id === "globe") {
    return <GlobeScreen />;
  }

  if (id === "map") {
    return <MapScreen />;
  }

  if (id === "intake") {
    return <IntakeScreen />;
  }

  if (id === "untangle") {
    return <UntangleScreen />;
  }

  if (id === "leads") {
    return <LeadsScreen />;
  }

  if (id === "origin") {
    return <OriginScreen />;
  }

  if (id === "proof") {
    return <ProofScreen />;
  }

  if (id === "world") {
    return <WorldScreen />;
  }

  return (
    <StageHeader id={id}>
      <p className={styles.note}>{COPY[id]}</p>
    </StageHeader>
  );
}
