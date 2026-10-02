"""Actual typed mean-message GNN/GRU and embedding-tree experiments on causal AML windows.

This custom window model is NOT a reproduction of HGT, TGAT, TGN or EvolveGCN.
Only research code consumes labels. Every graph/feature is bounded at its window end.
"""

from __future__ import annotations

import argparse
import copy
import json
import resource
import time
from pathlib import Path

import joblib
import numpy as np
import polars as pl
import torch
from buddhi_world_transfer import activity, matrix, windows
from common import digest, log, ranking
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from chakravyuh.buddhi import snapshot
from chakravyuh.jaal import provenance
from chakravyuh.shastra.schema import NET_CLASS_CODES

OUT = Path("research/bitcoin/results/temporal-hetero-benchmark")
WIDTH = 32
EPOCHS = 60
OWNERSHIP_THRESHOLD = 0.3
PARTITION_MODE = "heuristic"


def pool(values, edges, size):
    result = values.new_zeros((size, values.shape[1]))
    count = values.new_zeros((size, 1))
    if edges.shape[1]:
        result.index_add_(0, edges[1], values[edges[0]])
        count.index_add_(0, edges[1], values.new_ones((edges.shape[1], 1)))
    return result / count.clamp(min=1)


def indices(frame, source, target):
    return torch.from_numpy(
        frame.select(source, target)
        .unique()
        .sort(source, target)
        .to_numpy()
        .astype(np.int64)
        .T.copy()
    )


def dataset(threshold=0.3, partition_mode="heuristic"):
    root = Path("data/generated/agency-v2/normalised")
    tx = pl.read_parquet(root / "transactions.parquet")
    addresses = pl.read_parquet(root / "addresses.parquet")
    ann = pl.read_parquet(root / "announcements.parquet")
    peers = pl.read_parquet(root / "peers.parquet")
    truth = pl.read_parquet("ground_truth/agency-v2/entities.parquet")
    labels = truth.select(
        pl.col("entity_id").alias("owner"), pl.col("addresses").alias("address")
    ).explode("address")
    act = activity(
        tx,
        labels,
        pl.read_parquet("ground_truth/agency-v2/campaigns.parquet").select("entity_ids", "txids"),
    )
    return build_graphs(
        tx, addresses, ann, peers, labels, act, threshold=threshold, partition_mode=partition_mode
    )


def build_graphs(
    tx, addresses, ann, peers, labels, act, scalers=None, threshold=0.3, partition_mode="heuristic"
):
    ledger = (
        pl.DataFrame(schema=provenance.LEDGER_SCHEMA)
        if partition_mode == "address"
        else provenance.ownership_evidence(tx)
    )
    graphs, memory_map, offset = [], {}, 0
    for window_id, (phase, start, end) in enumerate(windows(tx)):
        s = snapshot.build(
            tx,
            addresses,
            ledger,
            start_us=start,
            end_us=end,
            threshold=threshold,
            partition_mode=partition_mode,
        )
        owners = act.filter((pl.col("first_seen_us") >= start) & (pl.col("first_seen_us") <= end))[
            "owner"
        ].unique()
        # Attach labels only after label-free snapshot construction.
        target = (
            s.members.join(labels, on="address")
            .group_by("subject_id")
            .agg(pl.col("owner").is_in(owners).any().cast(pl.Int8).alias("y"))
        )
        subjects = s.table.join(target, on="subject_id").sort("subject_id").with_row_index("si")
        members = s.members.join(subjects.select("subject_id", "si"), on="subject_id")
        transactions = (
            tx.filter((pl.col("first_seen_us") >= start) & (pl.col("first_seen_us") <= end))
            .sort("txid")
            .with_row_index("ti")
        )
        observed = ann.filter((pl.col("seen_us") >= start) & (pl.col("seen_us") <= end))
        observed = observed.join(transactions.select("txid", "ti"), on="txid")
        ips = (
            observed.group_by("peer_ip")
            .agg(
                pl.len().alias("observations"),
                pl.col("txid").n_unique().alias("transactions"),
                pl.col("observer_ip").n_unique().alias("observers"),
            )
            .join(peers.select("peer_ip", "net_class"), on="peer_ip", how="left")
        )
        ips = ips.sort("peer_ip").with_row_index("pi")
        in_links = transactions.select("ti", pl.col("input_addresses").alias("address"))
        in_links = in_links.explode("address").drop_nulls("address").join(members, on="address")
        out_links = transactions.select("ti", pl.col("output_addresses").alias("address"))
        out_links = out_links.explode("address").drop_nulls("address").join(members, on="address")
        ip_links = observed.join(ips.select("peer_ip", "pi"), on="peer_ip")
        edges = {
            "funds": indices(in_links, "si", "ti"),
            "receives": indices(out_links, "ti", "si"),
            "announces": indices(ip_links, "pi", "ti"),
        }
        # Context across changing subject IDs follows previously observed addresses only.
        old, current = [], []
        for address, si in members.select("address", "si").rows():
            if address in memory_map:
                old.append(memory_map[address])
                current.append(si)
        memory_edges = torch.tensor([old, current], dtype=torch.long)
        for address, si in members.select("address", "si").rows():
            memory_map[address] = offset + si
        offset += subjects.height
        tx_x = (
            transactions.select(
                "n_in",
                "n_out",
                "total_out_sats",
                "fee_sats",
                "fee_rate_sat_vb",
                "has_equal_outputs",
            )
            .to_numpy()
            .astype(np.float64)
        )
        tx_x = np.log1p(np.maximum(np.nan_to_num(tx_x, nan=0), 0))
        ip_x = ips.select("observations", "transactions", "observers").to_numpy().astype(np.float32)
        codes = ips["net_class"].replace_strict(NET_CLASS_CODES, default=0).to_numpy().astype(int)
        ip_x = np.column_stack([np.log1p(ip_x), np.eye(6)[codes]])
        graph = {
            "phase": phase,
            "window_id": window_id,
            "start_us": start,
            "end_us": end,
            "subjects": subjects.select("subject_id", "y"),
            "members": members.select("subject_id", "address"),
            "subject": matrix(subjects),
            "transaction": tx_x,
            "ip": ip_x,
            "edges": edges,
            "memory_edges": memory_edges,
            "y": torch.tensor(subjects["y"].to_numpy(), dtype=torch.float32),
        }
        graphs.append(graph)
        log(
            "typed_window_graph_built",
            window=window_id,
            subjects=subjects.height,
            transactions=transactions.height,
            ips=ips.height,
            edges={k: v.shape[1] for k, v in edges.items()},
            production_changes=False,
        )
    fit_scalers = scalers is None
    scalers = {} if fit_scalers else scalers
    for kind in ("subject", "transaction", "ip"):
        scaler = (
            StandardScaler().fit(np.concatenate([g[kind] for g in graphs if g["phase"] == "fit"]))
            if fit_scalers
            else scalers[kind]
        )
        scalers[kind] = scaler
        for g in graphs:
            g[kind] = torch.tensor(scaler.transform(g[kind]).astype(np.float32))
    return graphs, scalers


class Model(torch.nn.Module):
    def __init__(self, dimensions, graph=True, temporal=False):
        super().__init__()
        self.use_graph, self.temporal = graph, temporal
        self.encode = torch.nn.ModuleDict(
            {k: torch.nn.Linear(d, WIDTH) for k, d in dimensions.items()}
        )
        self.funds = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.announces = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.receives = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.spends = torch.nn.Linear(WIDTH, WIDTH, bias=False)
        self.self_update = torch.nn.Linear(WIDTH, WIDTH)
        self.gru = torch.nn.GRUCell(WIDTH, WIDTH)
        self.head = torch.nn.Linear(WIDTH, 1)

    def forward(self, g, bank):
        h = {k: torch.relu(self.encode[k](g[k])) for k in self.encode}
        if self.use_graph:
            tx = torch.relu(
                h["transaction"]
                + self.funds(pool(h["subject"], g["edges"]["funds"], len(h["transaction"])))
                + self.announces(pool(h["ip"], g["edges"]["announces"], len(h["transaction"])))
            )
            subject = torch.relu(
                self.self_update(h["subject"])
                + self.receives(pool(tx, g["edges"]["receives"], len(h["subject"])))
                + self.spends(pool(tx, g["edges"]["funds"].flip(0), len(h["subject"])))
            )
        else:
            subject = torch.relu(self.self_update(h["subject"]))
        if self.temporal:
            previous = pool(bank, g["memory_edges"], len(subject))
            subject = self.gru(subject, previous)
        return self.head(
            torch.nn.functional.dropout(subject, 0.2, self.training)
        ).flatten(), subject


def rollout(net, graphs):
    bank = torch.empty((0, WIDTH))
    outputs, embeddings = [], []
    for g in graphs:
        p, h = net(g, bank)
        outputs.append(torch.sigmoid(p).detach().numpy())
        embeddings.append(h.detach().numpy())
        bank = torch.cat([bank, h.detach()])
    return np.concatenate(outputs), np.concatenate(embeddings)


def assess(graphs, scores, name):
    phase = np.concatenate([np.repeat(g["phase"], len(g["y"])) for g in graphs])
    y = np.concatenate([g["y"].numpy() for g in graphs])
    raw = np.clip(scores, 1e-6, 1 - 1e-6)
    logits = np.log(raw / (1 - raw))
    cal = LogisticRegression(max_iter=1000, random_state=42).fit(
        logits[phase == "cal", None], y[phase == "cal"]
    )
    p = cal.predict_proba(logits[:, None])[:, 1]
    frame = pl.concat(
        [
            g["subjects"].with_columns(
                pl.lit(g["window_id"]).alias("window_id"), pl.lit(g["phase"]).alias("phase")
            )
            for g in graphs
        ]
    )
    path = OUT / f"{name}-scores.parquet"
    frame.with_columns(pl.Series("score", p)).write_parquet(path, compression="zstd")
    return {
        "validation": ranking(y[phase == "val"], p[phase == "val"]),
        "test": ranking(y[phase == "test"], p[phase == "test"]),
        "test_by_window": {
            str(i): ranking(
                y[frame["window_id"].to_numpy() == i], p[frame["window_id"].to_numpy() == i]
            )
            for i in (7, 8, 9)
        },
        "score_artifact": str(path),
        "score_sha256": digest(path),
    }


def train(graphs, name, graph=True, temporal=False):
    torch.manual_seed(42)
    net = Model(
        {k: graphs[0][k].shape[1] for k in ("subject", "transaction", "ip")}, graph, temporal
    )
    opt = torch.optim.AdamW(net.parameters(), lr=0.001, weight_decay=0.001)
    fit = [g for g in graphs if g["phase"] == "fit"]
    y = torch.cat([g["y"] for g in fit])
    weight = float(torch.sqrt((len(y) - y.sum()) / y.sum()))
    loss = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(weight))
    best, best_epoch, best_ap = None, 0, -1.0
    for epoch in range(1, EPOCHS + 1):
        net.train()
        bank = torch.empty((0, WIDTH))
        for g in fit:
            opt.zero_grad()
            logits, h = net(g, bank)
            objective = loss(logits, g["y"])
            objective.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5)
            opt.step()
            bank = torch.cat([bank, h.detach()])
        if epoch % 5 == 0:
            net.eval()
            with torch.no_grad():
                p, _ = rollout(net, graphs[:7])
            v = graphs[6]["y"].numpy()
            ap = float(average_precision_score(v, p[-len(v) :]))
            if ap > best_ap:
                best, best_epoch, best_ap = copy.deepcopy(net.state_dict()), epoch, ap
    net.load_state_dict(best)
    net.eval()
    with torch.no_grad():
        scores, embeddings = rollout(net, graphs)
    torch.save(
        {
            "state_dict": net.state_dict(),
            "graph": graph,
            "temporal": temporal,
            "width": WIDTH,
            "selected_epoch": best_epoch,
        },
        OUT / f"{name}.pt",
    )
    return (
        scores,
        embeddings,
        {
            "selected_epoch": best_epoch,
            "validation_checkpoint_ap": best_ap,
            "parameters": sum(p.numel() for p in net.parameters()),
            "positive_weight": weight,
        },
    )


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    graphs, scalers = dataset(OWNERSHIP_THRESHOLD, PARTITION_MODE)
    joblib.dump(scalers, OUT / "scalers.joblib")
    result = {}
    embedding = None
    for name, graph, temporal in (
        ("mlp", False, False),
        ("typed_static", True, False),
        ("typed_temporal_gru", True, True),
    ):
        started = time.perf_counter()
        p, h, meta = train(graphs, name, graph, temporal)
        result[name] = {**assess(graphs, p, name), **meta, "seconds": time.perf_counter() - started}
        if temporal:
            embedding = h
        log(
            "typed_graph_model_complete",
            model=name,
            test=result[name]["test"],
            production_changes=False,
        )
    # Shuffle subject endpoints under one within-window permutation, preserving degrees and
    # graph size but breaking assignment to subject features/labels. Temporal address memory
    # remains correct, isolating relational alignment rather than removing every temporal cue.
    shuffled = copy.deepcopy(graphs)
    rng = np.random.default_rng(42)
    for g in shuffled:
        perm = torch.tensor(rng.permutation(len(g["y"])))
        g["edges"]["funds"][0] = perm[g["edges"]["funds"][0]]
        g["edges"]["receives"][1] = perm[g["edges"]["receives"][1]]
    p, _, meta = train(shuffled, "typed_temporal_shuffled", True, True)
    result["typed_temporal_shuffled"] = {**assess(shuffled, p, "typed_temporal_shuffled"), **meta}
    base = np.concatenate([g["subject"].numpy() for g in graphs])
    # Label-free engineered relation summaries provide a strong tabular graph control.
    enriched = []
    for g in graphs:
        tx_context = torch.cat(
            [g["transaction"], pool(g["ip"], g["edges"]["announces"], len(g["transaction"]))], 1
        )
        enriched.append(
            torch.cat(
                [
                    g["subject"],
                    pool(tx_context, g["edges"]["receives"], len(g["y"])),
                    pool(tx_context, g["edges"]["funds"].flip(0), len(g["y"])),
                ],
                1,
            ).numpy()
        )
    phase = np.concatenate([np.repeat(g["phase"], len(g["y"])) for g in graphs])
    y = np.concatenate([g["y"].numpy() for g in graphs])
    fit = phase == "fit"
    for name, x in (
        ("xgboost_local", base),
        ("xgboost_typed_features", np.concatenate(enriched)),
        ("temporal_embeddings_xgboost", np.column_stack([base, embedding])),
    ):
        model = XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            min_child_weight=10,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=4,
            tree_method="hist",
            random_state=42,
        )
        model.fit(x[fit], y[fit])
        p = model.predict_proba(x)[:, 1]
        model.save_model(OUT / f"{name}.json")
        result[name] = assess(graphs, p, name)
    report = {
        "models": result,
        "epochs": EPOCHS,
        "width": WIDTH,
        "ownership_threshold": OWNERSHIP_THRESHOLD,
        "partition_mode": PARTITION_MODE,
        "seconds": time.perf_counter() - begin,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "selected_by_validation_p20_then_ap": max(
            result,
            key=lambda k: (result[k]["validation"]["p_at_20"], result[k]["validation"]["ap"]),
        ),
        "graph_sizes": [
            {
                "window": g["window_id"],
                "subjects": len(g["y"]),
                "tx": len(g["transaction"]),
                "ip": len(g["ip"]),
                "positives": int(g["y"].sum()),
            }
            for g in graphs
        ],
        "limitations": [
            "Consumed canonical synthetic world; exploratory, not confirmatory.",
            "Custom typed mean GNN plus window GRU; not canonical TGN/TGAT/HGT/EvolveGCN.",
            "Checkpoints use validation AP; family choice uses validation P20 then AP.",
            "Memory pools earlier embeddings by observed addresses, not verified owner.",
            "Previous states detached; no future graph/labels supplied.",
            "IP links identify announcers, not sources; fixed enrichment assumed.",
            "Hybrid tree fits embeddings of neural fitting rows: no cross-fit stack claim.",
            "Subject decisions repeat controllers; target is in-window campaign involvement.",
        ],
        "hashes": {
            str(p): digest(p)
            for p in (Path(__file__), Path(snapshot.__file__), Path(provenance.__file__))
        },
    }
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    log(
        "temporal_hetero_benchmark_complete",
        output=str(OUT / "report.json"),
        production_changes=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--ownership-threshold", type=float, default=0.3)
    parser.add_argument("--partition-mode", choices=("heuristic", "address"), default="heuristic")
    args = parser.parse_args()
    if args.epochs < 5 or args.epochs % 5:
        parser.error("epochs must be a positive multiple of five")
    if not 0 <= args.ownership_threshold <= 1:
        parser.error("ownership threshold must be finite and in [0, 1]")
    EPOCHS, OUT = args.epochs, args.output
    OWNERSHIP_THRESHOLD = args.ownership_threshold
    PARTITION_MODE = args.partition_mode
    main()
