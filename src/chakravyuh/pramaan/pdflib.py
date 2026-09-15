"""A minimal deterministic PDF 1.4 writer. No dependency exists for this and none can be
added (STATE.md open problem 3), so this builds the objects by hand.

Scope, deliberately narrow: A4 pages, the four built-in base fonts (nothing embedded,
nothing fetched), text placed at coordinates, hairline rules, and word wrapping from the
AFM advance widths below. That is exactly what `documents.py` needs and nothing more.

Determinism: the byte stream is a pure function of the calls — no CreationDate, no
Producer, no compression — so the same document always renders to the same bytes, which
the replay gate hashes.

Uncompressed streams are also the point, not a shortcut: the identifier test greps the
PDF bytes for complete-identifier patterns, which only works if the text sits in the
stream as literal characters.

`ponytail:` the width tables are the standard AFM values transcribed for chars 32-126
only, and the bold faces are measured with their regular counterpart's widths — a wrap
point may shift by a character or two against Acrobat's own layout. Documents here wrap
on whole words with a wide margin, so the ceiling is cosmetic, not structural.
"""

from __future__ import annotations

from typing import Final

A4: Final[tuple[float, float]] = (595.28, 841.89)  # points, portrait

FONTS: Final[dict[str, str]] = {
    "serif": "Times-Roman",
    "serif-bold": "Times-Bold",
    "sans": "Helvetica",
    "mono": "Courier",
}

_HELV: Final[dict[int, int]] = {
    32: 278,
    33: 278,
    34: 355,
    35: 556,
    36: 556,
    37: 889,
    38: 667,
    39: 191,
    40: 333,
    41: 333,
    42: 389,
    43: 584,
    44: 278,
    45: 333,
    46: 278,
    47: 278,
    48: 556,
    49: 556,
    50: 556,
    51: 556,
    52: 556,
    53: 556,
    54: 556,
    55: 556,
    56: 556,
    57: 556,
    58: 278,
    59: 278,
    60: 584,
    61: 584,
    62: 584,
    63: 556,
    64: 1015,
    65: 667,
    66: 667,
    67: 722,
    68: 722,
    69: 667,
    70: 611,
    71: 778,
    72: 722,
    73: 278,
    74: 500,
    75: 667,
    76: 556,
    77: 833,
    78: 722,
    79: 778,
    80: 667,
    81: 778,
    82: 722,
    83: 667,
    84: 611,
    85: 722,
    86: 667,
    87: 944,
    88: 667,
    89: 667,
    90: 611,
    91: 278,
    92: 278,
    93: 278,
    94: 469,
    95: 556,
    96: 333,
    97: 556,
    98: 556,
    99: 500,
    100: 556,
    101: 556,
    102: 278,
    103: 556,
    104: 556,
    105: 222,
    106: 222,
    107: 500,
    108: 222,
    109: 833,
    110: 556,
    111: 556,
    112: 556,
    113: 556,
    114: 333,
    115: 500,
    116: 278,
    117: 556,
    118: 500,
    119: 722,
    120: 500,
    121: 500,
    122: 500,
    123: 334,
    124: 260,
    125: 334,
    126: 584,
}

_TIMES: Final[dict[int, int]] = {
    32: 250,
    33: 333,
    34: 408,
    35: 500,
    36: 500,
    37: 833,
    38: 778,
    39: 180,
    40: 333,
    41: 333,
    42: 500,
    43: 564,
    44: 250,
    45: 333,
    46: 250,
    47: 278,
    48: 500,
    49: 500,
    50: 500,
    51: 500,
    52: 500,
    53: 500,
    54: 500,
    55: 500,
    56: 500,
    57: 500,
    58: 278,
    59: 278,
    60: 564,
    61: 564,
    62: 564,
    63: 444,
    64: 921,
    65: 722,
    66: 667,
    67: 667,
    68: 722,
    69: 611,
    70: 556,
    71: 722,
    72: 722,
    73: 333,
    74: 389,
    75: 722,
    76: 611,
    77: 889,
    78: 722,
    79: 722,
    80: 556,
    81: 722,
    82: 667,
    83: 556,
    84: 611,
    85: 722,
    86: 722,
    87: 944,
    88: 722,
    89: 722,
    90: 611,
    91: 333,
    92: 278,
    93: 333,
    94: 469,
    95: 500,
    96: 333,
    97: 444,
    98: 500,
    99: 444,
    100: 500,
    101: 444,
    102: 333,
    103: 500,
    104: 500,
    105: 278,
    106: 278,
    107: 500,
    108: 278,
    109: 778,
    110: 500,
    111: 500,
    112: 500,
    113: 500,
    114: 333,
    115: 389,
    116: 278,
    117: 500,
    118: 500,
    119: 722,
    120: 500,
    121: 500,
    122: 444,
    123: 480,
    124: 200,
    125: 480,
    126: 541,
}

_WIDTHS: Final[dict[str, dict[int, int]]] = {
    "serif": _TIMES,
    "serif-bold": _TIMES,
    "sans": _HELV,
    "sans-bold": _HELV,
    "mono": {c: 600 for c in range(32, 127)},
}


def text_width(text: str, font: str, size: float) -> float:
    """Advance width of `text` in points, using the font's AFM table."""
    table = _WIDTHS[font]
    return size * sum(table.get(ord(ch), table.get(63, 500)) for ch in text) / 1000.0


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    """Word-wrap `text` to `width` points. Explicit newlines are honoured. A single word
    wider than the line is not split: it overflows, and the caller chose the margin."""
    lines: list[str] = []
    for para in text.split("\n"):
        current = ""
        for word in para.split(" "):
            candidate = word if not current else current + " " + word
            if current and text_width(candidate, font, size) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def _pdf_string(text: str) -> str:
    """A PDF literal string, cp1252-encoded per WinAnsiEncoding. `…` lands on 0x85."""
    return (
        "("
        + text.encode("cp1252", "replace")
        .decode("cp1252")
        .replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
        + ")"
    )


class _Page:
    """One page's content operators. Coordinates are from the top-left margin."""

    def __init__(self) -> None:
        self.ops: list[str] = []

    def text(self, x: float, y: float, font: str, size: float, content: str) -> None:
        self.ops.append(
            f"BT /{FONTS[font]} {size:.2f} Tf {x:.2f} {y:.2f} Td {_pdf_string(content)} Tj ET"
        )

    def rule(self, x: float, y: float, width: float) -> None:
        self.ops.append(f"{x:.2f} {y:.2f} m {x + width:.2f} {y:.2f} l 0.5 w S")


class Document:
    """A PDF of A4 pages. `render` returns the bytes; render twice, get the same bytes."""

    def __init__(self, title: str) -> None:
        self._title = title
        self._pages: list[_Page] = []

    def page(self) -> _Page:
        new = _Page()
        self._pages.append(new)
        return new

    def render(self) -> bytes:
        if not self._pages:
            self._pages.append(_Page())
        objects: list[bytes] = []

        def add(body: str | bytes) -> int:
            objects.append(body if isinstance(body, bytes) else body.encode("cp1252", "replace"))
            return len(objects)

        font_ids = {
            key: add(
                f"<< /Type /Font /Subtype /Type1 /BaseFont /{name} "
                f"/Encoding /WinAnsiEncoding >>"
            )
            for key, name in FONTS.items()
        }
        kids: list[int] = []
        for page in self._pages:
            resources = " ".join(f"/{name} {font_ids[key]} 0 R" for key, name in FONTS.items())
            stream = "\n".join(page.ops).encode("cp1252", "replace")
            content_id = add(
                f"<< /Length {len(stream)} >>\nstream\n".encode("cp1252", "replace")
                + stream
                + b"\nendstream"
            )
            page_id = add(
                f"<< /Type /Page /Parent {{pages}} 0 R /MediaBox [0 0 {A4[0]:.2f} {A4[1]:.2f}] "
                f"/Resources << /Font << {resources} >> >> /Contents {content_id} 0 R >>"
            )
            kids.append(page_id)
        info_id = add(f"<< /Title {_pdf_string(self._title)} >>")
        pages_id = add(
            "<< /Type /Pages /Kids ["
            + " ".join(f"{kid} 0 R" for kid in kids)
            + f"] /Count {len(kids)} >>"
        )
        objects = [
            body.replace(b"{pages}", b"%d" % pages_id)
            if body.startswith(b"<< /Type /Page ")
            else body
            for body in objects
        ]
        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0] * (len(objects) + 1)
        for number, body in enumerate(objects, start=1):
            offsets[number] = len(out)
            out += b"%d 0 obj\n" % number
            out += body
            out += b"\nendobj\n"
        xref_at = len(out)
        out += b"xref\n0 %d\n" % (len(objects) + 1)
        out += b"0000000000 65535 f \n"
        for offset in offsets[1:]:
            out += b"%010d 00000 n \n" % offset
        out += b"trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objects) + 1,
            catalog_id,
            info_id,
            xref_at,
        )
        return bytes(out)
