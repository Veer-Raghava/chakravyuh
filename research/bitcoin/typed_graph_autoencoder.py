"""Label-free typed link reconstruction; edge surprise is not an illicit probability."""

from __future__ import annotations

import json
import math
import resource
import time
from pathlib import Path

import numpy as np
import polars as pl
import torch
from common import digest, log, ranking
from temporal_hetero_benchmark import WIDTH, Model, dataset, pool

OUT = Path("research/bitcoin/results/typed-graph-autoencoder")
RELATIONS = {
    "funds": ("subject", "transaction"),
    "receives": ("transaction", "subject"),
    "announces": ("ip", "transaction"),
}


class Autoencoder(Model):
    def __init__(self, dimensions):
        super().__init__(dimensions, graph=True, temporal=False)
        self.decoder = torch.nn.ParameterDict(
            {name: torch.nn.Parameter(torch.eye(WIDTH)) for name in RELATIONS}
        )

    def representations(self, graph):
        h = {name: torch.relu(self.encode[name](graph[name])) for name in self.encode}
        tx = torch.relu(
            h["transaction"]
            + self.funds(pool(h["subject"], graph["edges"]["funds"], len(h["transaction"])))
            + self.announces(pool(h["ip"], graph["edges"]["announces"], len(h["transaction"])))
        )
        subject = torch.relu(
            self.self_update(h["subject"])
            + self.receives(pool(tx, graph["edges"]["receives"], len(h["subject"])))
            + self.spends(pool(tx, graph["edges"]["funds"].flip(0), len(h["subject"])))
        )
        return {"subject": subject, "transaction": tx, "ip": h["ip"]}

    def edge_logits(self, h, relation, edges):
        source, target = RELATIONS[relation]
        left = h[source][edges[0]] @ self.decoder[relation]
        return (left * h[target][edges[1]]).sum(1) / math.sqrt(WIDTH)


def negatives(edges, target_size, rng):
    """Sample type-correct targets, excluding every actual relation edge."""
    source = edges[0].numpy()
    targets = rng.integers(target_size, size=len(source))
    keys = source.astype(np.int64) * target_size + edges[1].numpy()
    keep = ~np.isin(source.astype(np.int64) * target_size + targets, keys)
    return torch.tensor(np.vstack([source[keep], targets[keep]]), dtype=torch.long)


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    graphs, _ = dataset()
    net = Autoencoder({kind: graphs[0][kind].shape[1] for kind in ("subject", "transaction", "ip")})
    optimizer = torch.optim.AdamW(net.parameters(), lr=0.001, weight_decay=0.001)
    rng = np.random.default_rng(42)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    history = []
    # Budget fixed before evaluation; no class labels or validation labels in fitting.
    for epoch in range(1, 31):
        total = 0.0
        for graph in graphs[:4]:
            optimizer.zero_grad()
            h = net.representations(graph)
            losses = []
            for relation, (_, target) in RELATIONS.items():
                edges = graph["edges"][relation]
                negative = negatives(edges, len(h[target]), rng)
                positive_logits = net.edge_logits(h, relation, edges)
                negative_logits = net.edge_logits(h, relation, negative)
                losses.extend(
                    [
                        loss_fn(positive_logits, torch.ones_like(positive_logits)),
                        loss_fn(negative_logits, torch.zeros_like(negative_logits)),
                    ]
                )
            loss = torch.stack(losses).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5)
            optimizer.step()
            total += float(loss.detach())
        history.append({"epoch": epoch, "mean_fit_loss": total / 4})
    scores = []
    with torch.no_grad():
        for graph in graphs:
            h = net.representations(graph)
            surprise = torch.zeros(len(h["subject"]))
            counts = torch.zeros_like(surprise)
            for relation, endpoint in (("funds", 0), ("receives", 1)):
                edges = graph["edges"][relation]
                edge_loss = torch.nn.functional.softplus(-net.edge_logits(h, relation, edges))
                surprise.index_add_(0, edges[endpoint], edge_loss)
                counts.index_add_(0, edges[endpoint], torch.ones_like(edge_loss))
            scores.append((surprise / counts.clamp(min=1)).numpy())
    p = np.concatenate(scores)
    frame = pl.concat(
        [
            graph["subjects"].with_columns(
                pl.lit(graph["phase"]).alias("phase"),
                pl.lit(graph["window_id"]).alias("window_id"),
            )
            for graph in graphs
        ]
    ).with_columns(pl.Series("edge_surprise", p))
    path = OUT / "scores.parquet"
    frame.write_parquet(path, compression="zstd")
    result = {}
    for phase in ("val", "test"):
        block = frame.filter(pl.col("phase") == phase)
        result[phase] = ranking(block["y"].to_numpy(), block["edge_surprise"].to_numpy())
        result[phase].pop("brier", None)
    torch.save(net.state_dict(), OUT / "model.pt")
    report = {
        "metrics": result,
        "history": history,
        "epochs": 30,
        "width": WIDTH,
        "seconds": time.perf_counter() - begin,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "hashes": {str(Path(__file__)): digest(__file__), str(path): digest(path)},
        "limitations": [
            "Custom typed link autoencoder, not a canonical published implementation.",
            "Current-window edges both condition encoding and define reconstruction targets.",
            "Random target corruption is not a matched hard-negative sampler.",
            "Unusual observed links are not illicit labels or source-absence evidence.",
            "Single consumed synthetic world; no independent novelty-label evaluation.",
            "No probability interpretation or production promotion.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("typed_graph_autoencoder_complete", output=str(OUT / "report.json"))


if __name__ == "__main__":
    main()
