"""Actual trained CPU GNNs versus trees/local/engineered-graph controls on vendored Elliptic.

This is snapshot-transductive inside each public two-week time step, not event-time inference.
No validation/calibration/test adjacency or labels enter graph-model fitting. All 93 named local
columns only; vendor anonymous/aggregate feature provenance remains a limitation.
"""

from __future__ import annotations

import copy
import json
import resource
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
import sklearn
import torch
import xgboost
from common import digest, log, ranking
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

SEED = 42
MAX_EPOCHS = 240
VENDOR = Path("vendor/elliptic")
OUT = Path("research/bitcoin/results/elliptic-graph-benchmark.json")


def adjacency(edges, indices, size):
    # Symmetric normalization plus self loops; global-to-phase node IDs isolate future graph.
    lookup = np.full(size, -1, dtype=np.int64)
    lookup[indices] = np.arange(len(indices))
    mapped = lookup[edges]
    mapped = mapped[:, (mapped >= 0).all(axis=0)]
    directed = torch.from_numpy(mapped)
    undirected = torch.cat([directed, directed.flip(0)], dim=1)
    loops = torch.arange(len(indices)).repeat(2, 1)
    a = torch.sparse_coo_tensor(
        torch.cat([undirected, loops], 1),
        torch.ones(undirected.shape[1] + len(indices)),
        (len(indices), len(indices)),
    ).coalesce()
    # Parallel pairs count once; transaction-flow CSV should not contain duplicate pairs.
    degree = torch.sparse.sum(a, dim=1).to_dense().clamp(min=1)
    inv = degree.rsqrt()
    values = a.values() * inv[a.indices()[0]] * inv[a.indices()[1]]
    return torch.sparse_coo_tensor(a.indices(), values, a.shape).coalesce()


class Network(torch.nn.Module):
    def __init__(self, dim, kind):
        super().__init__()
        self.kind = kind
        self.first = torch.nn.Linear(dim * (2 if kind == "sage" else 1), 32)
        self.second = torch.nn.Linear(64 if kind == "sage" else 32, 1)

    def forward(self, x, a):
        if self.kind == "gcn":
            h = torch.relu(self.first(torch.sparse.mm(a, x)))
            p = self.second(torch.sparse.mm(a, torch.nn.functional.dropout(h, 0.2, self.training)))
        elif self.kind == "sage":
            # Normalized neighborhood with self term explicitly retained; not canonical mean-SAGE.
            h = torch.relu(self.first(torch.cat([x, torch.sparse.mm(a, x)], 1)))
            d = torch.nn.functional.dropout(h, 0.2, self.training)
            p = self.second(torch.cat([d, torch.sparse.mm(a, d)], 1))
        else:
            h = torch.relu(self.first(x))
            p = self.second(torch.nn.functional.dropout(h, 0.2, self.training))
        return p.flatten(), h


def train_network(kind, phases, y):
    torch.manual_seed(SEED)
    net = Network(phases["fit"][0].shape[1], kind)
    opt = torch.optim.AdamW(net.parameters(), lr=0.005, weight_decay=5e-4)
    ids = phases["fit"][2]
    labelled = y[ids] >= 0
    target = torch.tensor(y[ids][labelled], dtype=torch.float32)
    positive_weight = float(np.sqrt((len(target) - target.sum().item()) / target.sum().item()))
    objective = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(positive_weight))
    best_ap, best_state, best_epoch = -1.0, None, 0
    curve = []
    from sklearn.metrics import average_precision_score

    for epoch in range(1, MAX_EPOCHS + 1):
        net.train()
        opt.zero_grad()
        logits, _ = net(phases["fit"][0], phases["fit"][1])
        loss = objective(logits[labelled], target)
        loss.backward()
        opt.step()
        if epoch % 5 == 0:
            net.eval()
            with torch.no_grad():
                ids = phases["select"][2]
                known = y[ids] >= 0
                v, _ = net(phases["select"][0], phases["select"][1])
                ap = float(average_precision_score(y[ids][known], torch.sigmoid(v).numpy()[known]))
            curve.append(
                {"epoch": epoch, "validation_ap": ap, "training_loss": float(loss.detach())}
            )
            if ap > best_ap:
                best_ap, best_state, best_epoch = ap, copy.deepcopy(net.state_dict()), epoch
    net.load_state_dict(best_state)
    net.eval()
    scores, embeddings = np.zeros(len(y)), np.zeros((len(y), 32), dtype=np.float32)
    with torch.no_grad():
        for x, a, ids in phases.values():
            v, h = net(x, a)
            scores[ids] = torch.sigmoid(v).numpy()
            embeddings[ids] = h.numpy()
    return (
        scores,
        embeddings,
        {
            "kind": kind,
            "hidden": 32,
            "max_epochs": MAX_EPOCHS,
            "selected_epoch": best_epoch,
            "lr": 0.005,
            "weight_decay": 0.0005,
            "dropout": 0.2,
            "positive_weight": positive_weight,
            "parameters": sum(p.numel() for p in net.parameters()),
            "learning_curve": curve,
        },
    )


def evaluate(raw, y, step):
    labelled = y >= 0
    calibration = labelled & (step >= 35) & (step <= 37)
    validation = labelled & (step >= 38) & (step <= 39)
    test = labelled & (step >= 40)
    logits = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / np.clip(1 - raw, 1e-6, 1 - 1e-6))
    calibrator = LogisticRegression(max_iter=1000, random_state=SEED)
    calibrator.fit(logits[calibration, None], y[calibration])
    p = calibrator.predict_proba(logits[:, None])[:, 1]
    choices = []
    for threshold in np.linspace(0.01, 0.99, 99):
        precision, recall, f1, _ = precision_recall_fscore_support(
            y[validation], p[validation] >= threshold, average="binary", zero_division=0
        )
        choices.append((f1, -threshold, precision, recall))
    f1, minus_threshold, _, _ = max(choices)
    threshold = -minus_threshold
    precision, recall, test_f1, _ = precision_recall_fscore_support(
        y[test], p[test] >= threshold, average="binary", zero_division=0
    )
    return {
        "test": ranking(y[test], p[test]),
        "threshold": threshold,
        "policy_validation_f1": f1,
        "test_precision": precision,
        "test_recall": recall,
        "test_f1": test_f1,
        "test_by_step": {
            str(s): ranking(y[labelled & (step == s)], p[labelled & (step == s)])
            for s in range(40, 50)
        },
    }


def main():
    started = time.perf_counter()
    torch.set_num_threads(4)
    torch.sparse.check_sparse_tensor_invariants.enable()
    torch.use_deterministic_algorithms(True)
    np.random.seed(SEED)
    feature_path = VENDOR / "elliptic_txs_features.csv"
    data = pl.read_csv(feature_path)
    local = [c for c in data.columns if c.startswith("Local_feature_")]
    if len(local) != 93:
        raise ValueError("requires audited named export with exactly 93 local numeric features")
    ids = data["txId"].to_numpy()
    step = data["Time step"].to_numpy()
    classes = pl.read_csv(VENDOR / "elliptic_txs_classes.csv").with_columns(
        pl.col("class").cast(pl.String)
    )
    joined = data.select("txId").join(classes, on="txId", how="left")
    labels = joined["class"].to_numpy()
    y = np.where(labels == "1", 1, np.where(labels == "2", 0, -1))
    edges_frame = pl.read_csv(VENDOR / "elliptic_txs_edgelist.csv")
    index = {int(txid): i for i, txid in enumerate(ids)}
    edges = np.array(
        [[index[int(a)], index[int(b)]] for a, b in edges_frame.iter_rows()], dtype=np.int64
    ).T
    cross_step = int((step[edges[0]] != step[edges[1]]).sum())
    if cross_step:
        raise ValueError(
            "cross-step edges require per-step point-in-time inference, not phase batches"
        )
    train = (step <= 30) & (y >= 0)
    x = (
        StandardScaler()
        .fit(data.select(local).to_numpy()[step <= 30])
        .transform(data.select(local).to_numpy())
        .astype(np.float32)
    )
    phases = {}
    for name, lo, hi in [
        ("fit", 1, 30),
        ("select", 31, 34),
        ("cal", 35, 37),
        ("policy", 38, 39),
        ("test", 40, 49),
    ]:
        positions = np.flatnonzero((step >= lo) & (step <= hi))
        phases[name] = (
            torch.from_numpy(x[positions]),
            adjacency(edges, positions, len(ids)),
            positions,
        )
    result = {}
    embeddings = None
    for name, kind in [
        ("mlp", "mlp"),
        ("gcn", "gcn"),
        ("sage_variant", "sage"),
        ("gcn_permuted", "gcn"),
    ]:
        phase_input = phases
        if name == "gcn_permuted":
            # Relocate both endpoints under random node permutation within each time step.
            rng = np.random.default_rng(SEED)
            permutation = np.arange(len(ids))
            for s in range(1, 50):
                same = np.flatnonzero(step == s)
                permutation[same] = rng.permutation(same)
            randomized_edges = permutation[edges]
            phase_input = {
                n: (a, adjacency(randomized_edges, pos, len(ids)), pos)
                for n, (a, _, pos) in phases.items()
            }
        begin = time.perf_counter()
        raw, hidden, params = train_network(kind, phase_input, y)
        result[name] = {
            "parameters": params,
            "fit_and_predict_seconds": time.perf_counter() - begin,
            **evaluate(raw, y, step),
        }
        if name == "gcn":
            embeddings = hidden
        log("elliptic_graph_model_complete", model=name, test_ap=result[name]["test"]["ap"])
    # Same observed adjacency available to an engineered graph-feature tree control.
    neighbors = np.empty_like(x)
    for a, graph, pos in phases.values():
        neighbors[pos] = torch.sparse.mm(graph, a).numpy()
    degree_in = np.bincount(edges[1], minlength=len(ids))
    degree_out = np.bincount(edges[0], minlength=len(ids))
    graph_features = np.column_stack([x, neighbors, np.log1p(degree_in), np.log1p(degree_out)])
    gbm_params = {
        "objective": "binary",
        "num_leaves": 31,
        "min_data_in_leaf": 40,
        "learning_rate": 0.05,
        "lambda_l2": 1,
        "num_threads": 4,
        "seed": SEED,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
    }
    for name, matrix in [
        ("lightgbm_local", x),
        ("lightgbm_graph_features", graph_features),
        ("gcn_embedding_lightgbm", np.column_stack([x, embeddings])),
    ]:
        begin = time.perf_counter()
        model = lgb.train(
            gbm_params, lgb.Dataset(matrix[train], label=y[train]), num_boost_round=300
        )
        raw = model.predict(matrix)
        result[name] = {
            "parameters": {**gbm_params, "rounds": 300, "input_dim": matrix.shape[1]},
            "fit_and_predict_seconds": time.perf_counter() - begin,
            **evaluate(raw, y, step),
        }
        log("elliptic_graph_model_complete", model=name, test_ap=result[name]["test"]["ap"])
    begin = time.perf_counter()
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_child_weight=10,
        subsample=0.9,
        colsample_bytree=0.9,
        n_jobs=4,
        tree_method="hist",
        random_state=SEED,
    )
    model.fit(x[train], y[train])
    raw = model.predict_proba(x)[:, 1]
    result["xgboost_local"] = {
        "parameters": {
            "rounds": 300,
            "max_depth": 5,
            "lr": 0.05,
            "min_child_weight": 10,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "seed": SEED,
            "threads": 4,
        },
        "fit_and_predict_seconds": time.perf_counter() - begin,
        **evaluate(raw, y, step),
    }
    report = {
        "dataset": "vendored named Elliptic export",
        "nodes": len(ids),
        "edges": edges.shape[1],
        "cross_time_step_edges": cross_step,
        "features": local,
        "seed": SEED,
        "models": result,
        "runtime_versions": {
            "torch": torch.__version__,
            "numpy": np.__version__,
            "polars": pl.__version__,
            "scikit-learn": sklearn.__version__,
            "lightgbm": lgb.__version__,
            "xgboost": xgboost.__version__,
        },
        "protocol": {
            "fit": "steps 1-30",
            "checkpoint_selection": "31-34",
            "platt_calibration": "35-37",
            "F1_threshold_selection": "38-39",
            "test": "40-49",
        },
        "limitations": [
            "local export feature provenance not independently event-time verified",
            "within-step unlabeled adjacency transductive; no finer timestamps available",
            "single seed and small hyperparameter search; no SOTA claim",
            "sage_variant uses symmetric normalization/self loops, not canonical mean GraphSAGE",
            "transaction classification; no IP data, wallet ownership, or source attribution",
            "same public dataset previously used by project; "
            "confirmatory external test requires another dataset",
        ],
        "seconds": time.perf_counter() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "hashes": {
            str(p): digest(p)
            for p in [
                feature_path,
                VENDOR / "elliptic_txs_classes.csv",
                VENDOR / "elliptic_txs_edgelist.csv",
                Path(__file__),
            ]
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    log("elliptic_graph_benchmark_complete", output=str(OUT), production_changes=False)


if __name__ == "__main__":
    main()
