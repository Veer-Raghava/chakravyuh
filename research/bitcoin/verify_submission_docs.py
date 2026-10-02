import datetime
import hashlib
import json
import re
from pathlib import Path

r = Path("research/bitcoin/results/submission-audit")
checks = []
fields = Path("docs/submission/portal-copy")
limits = {"title": 100, "abstract": 10000, "description": 50000}
for v in range(1, 5):
    for name, limit in limits.items():
        text = (fields / f"version-{v}-{name}.txt").read_text()
        u = len(text.encode("utf-16-le")) // 2
        assert 0 < len(text) <= limit and u <= limit
        checks.append(
            {
                "check": f"version-{v}-{name}",
                "characters": len(text),
                "utf16_units": u,
                "limit": limit,
            }
        )
# Source-defined dimensions and saved neural report values.
import sys

sys.path.insert(0, str(Path("src").resolve()))
from chakravyuh.buddhi import features, relational_inference, snapshot

assert len(features.MODEL_FEATURES) == 33
assert len(snapshot.SNAPSHOT_FEATURES) == 23
assert len(relational_inference.CONTEXT) == 38
assert len(relational_inference.FEATURES) == 329
checks.append(
    {
        "check": "source-defined features",
        "default": 33,
        "causal": 23,
        "context": 38,
        "rich": 329,
        "R47_mean_context_tree": 23 + 2 * (6 + 9),
    }
)
report = json.loads(
    Path("research/bitcoin/results/drishti-r47-graph-training/report.json").read_text()
)
assert report["models"]["typed_temporal_gru"]["test"]["hits_at_20"] == 19
checks.append(
    {
        "check": "R47 neural report",
        "temporal_ap": report["models"]["typed_temporal_gru"]["test"]["ap"],
        "hits_at_20": 19,
    }
)
# Check only local markdown links, outside code blocks.
for file in [*Path("docs/submission").glob("*.md"), Path("docs/CHAKRAVYUH-TECHNICAL-MASTER.md")]:
    text = file.read_text()
    plain = re.sub(r"```[\s\S]*?```", "", text)
    assert "lorem ipsum" not in plain.lower()
    assert len(text.split("```")) % 2 == 1, f"unbalanced fences in {file}"
    for url in re.findall(r"\]\(([^)]+)\)", plain):
        if re.match(r"https?://", url) or url.startswith("#"):
            continue
        target = file.parent / url.split("#")[0]
        assert target.exists(), f"missing link {file} -> {url}"
    checks.append(
        {
            "check": str(file),
            "bytes": file.stat().st_size,
            "words": len(text.split()),
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }
    )
(r / "document-validation.json").write_text(
    json.dumps(
        {"utc": datetime.datetime.now(datetime.UTC).isoformat(), "checks": checks},
        indent=2,
    )
)
print("Document checks passed:", len(checks))
