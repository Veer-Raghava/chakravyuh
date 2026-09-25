import { describe, expect, it } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { DataTable, type Column } from "./DataTable";

interface Row {
  name: string;
  n: number;
}

const rows: Row[] = [
  { name: "b", n: 3 },
  { name: "a", n: 1 },
  { name: "c", n: 2 },
];

const columns: Column<Row>[] = [
  { key: "name", header: "name", render: (r) => r.name },
  { key: "n", header: "n", numeric: true, render: (r) => String(r.n), sortValue: (r) => r.n },
];

describe("DataTable sorting", () => {
  it("sorts ascending then descending on a sortable numeric header", () => {
    render(<DataTable rows={rows} columns={columns} getKey={(r) => r.name} />);

    const header = screen.getByRole("button", { name: "n" });
    fireEvent.click(header);
    let cells = screen.getAllByText(/^[123]$/).map((el) => el.textContent);
    expect(cells).toEqual(["1", "2", "3"]);

    fireEvent.click(header);
    cells = screen.getAllByText(/^[123]$/).map((el) => el.textContent);
    expect(cells).toEqual(["3", "2", "1"]);
  });

  it("renders every row when they fit the viewport", () => {
    const { container } = render(<DataTable rows={rows} columns={columns} getKey={(r) => r.name} />);
    expect(within(container).getAllByText(/^[abc]$/)).toHaveLength(3);
  });
});
