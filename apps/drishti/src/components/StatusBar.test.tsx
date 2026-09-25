import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBar } from "./StatusBar";
import { MANIFEST } from "../adapter/fixtures";

describe("StatusBar", () => {
  it("shows a real, truncated hash from the manifest with the full value on hover", () => {
    render(<StatusBar manifest={MANIFEST} />);

    // head4 form of the fixture SHA-256, and the full value preserved in the title.
    const sha = screen.getByText("4f2a…c19d");
    expect(sha).toBeInTheDocument();
    expect(sha.closest("[title]")).toHaveAttribute("title", MANIFEST.input_sha256);

    expect(screen.getByText(MANIFEST.run_id)).toBeInTheDocument();
    expect(screen.getByText("999,847")).toBeInTheDocument();
    expect(screen.getByText(/air-gapped/i)).toBeInTheDocument();
  });

  it("colours a completed stage lamp differently from a pending one", () => {
    const withPending = {
      ...MANIFEST,
      stages: MANIFEST.stages.map((s, i) => ({ ...s, complete: i < 3 })),
    };
    render(<StatusBar manifest={withPending} />);
    expect(screen.getByTitle(/kavach complete/)).toBeInTheDocument();
    expect(screen.getByTitle(/shastra pending/)).toBeInTheDocument();
  });
});
