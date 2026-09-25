import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PacketView } from "./Packet";
import type { Packet } from "../adapter";

// A packet is court-ready only when all three lamps are green. The two states the screen
// must never blur: a fully verified packet, and one whose replay did not reproduce — which
// has to shout DO NOT SERVE rather than render as if it were signed and clean.
const base: Packet = {
  case_id: "CASE-T",
  generated_at_us: 1_700_000_000_000_000,
  tool_version: "t1",
  code_version: "c1",
  subject: { subject_id: "sub-1", addresses: ["bc1qexampleaddressone"], cluster_id: "clu-1" },
  attribution: {
    peer_ip: "103.21.244.17", peer_port: 8333, observed_at_utc: "2026-09-17T00:00:00Z",
    p_origin: 0.87, margin: 0.78, asn: 9829, as_org: "BSNL", geo_country: "IN", net_class: "residential",
  },
  findings: [{ statement: "f1", kind: "typology", source_ref: "ref#1" }],
  counter_findings: [{ statement: "c1", kind: "shared_ip", would_clear: false }],
  confidence: { low: 0.79, high: 0.92, coverage_target: 0.9, method: "conformal" },
  merkle_head: "a".repeat(64),
  ed25519_signature: "b".repeat(128),
  replay: { seed: 7, command: "chakravyuh replay --seed 7", expected_packet_sha256: "c".repeat(64) },
  legal: { basis: "BNSS s.94", hash_disclosure: "merkle root disclosed" },
  verification: { hash_verified: true, signature_valid: true, replay_matched: true },
  notice: { statute: "BNSS 2023 s.94", exchange: "Exchange Ltd", requested_records: ["KYC", "logs"] },
};

describe("PACKET view", () => {
  it("renders a fully verified packet without the DO NOT SERVE banner", () => {
    render(<PacketView packet={base} onCopyReplay={() => {}} />);
    expect(screen.queryByText("DO NOT SERVE")).toBeNull();
    expect(screen.getByText("hash verified")).toBeInTheDocument();
  });

  it("shows DO NOT SERVE when the replay did not reproduce the packet", () => {
    const mismatch = { ...base, verification: { ...base.verification, replay_matched: false } };
    render(<PacketView packet={mismatch} onCopyReplay={() => {}} />);
    expect(screen.getByText("DO NOT SERVE")).toBeInTheDocument();
    expect(screen.getByText(/did not reproduce from its seed/)).toBeInTheDocument();
  });
});
