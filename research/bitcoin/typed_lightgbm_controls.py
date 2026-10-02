"""Matched LightGBM controls: local features, typed summaries and frozen temporal embeddings."""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import temporal_hetero_benchmark as graph
import torch
from common import digest, log

OUT = Path("research/bitcoin/results/typed-lightgbm-controls")
ENCODER = Path("research/bitcoin/results/temporal-hetero-extended/typed_temporal_gru.pt")


def main():
    begin = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    graph.OUT = OUT
    torch.set_num_threads(4)
    graphs, _ = graph.dataset()
    saved = torch.load(ENCODER, weights_only=True)
    net = graph.Model({"subject": 23, "transaction": 6, "ip": 9}, True, True)
    net.load_state_dict(saved["state_dict"])
    net.eval()
    with torch.no_grad():
        _, embeddings = graph.rollout(net, graphs)
    local = np.concatenate([g["subject"].numpy() for g in graphs])
    enriched = []
    for g in graphs:
        tx = torch.cat(
            [g["transaction"], graph.pool(g["ip"], g["edges"]["announces"], len(g["transaction"]))],
            1,
        )
        enriched.append(
            torch.cat(
                [
                    g["subject"],
                    graph.pool(tx, g["edges"]["receives"], len(g["y"])),
                    graph.pool(tx, g["edges"]["funds"].flip(0), len(g["y"])),
                ],
                1,
            ).numpy()
        )
    fit = np.concatenate([np.repeat(g["phase"] == "fit", len(g["y"])) for g in graphs])
    y = np.concatenate([g["y"].numpy() for g in graphs])
    params = {
        "objective": "binary",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 40,
        "lambda_l2": 1.0,
        "num_threads": 4,
        "seed": 42,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
    }
    results = {}
    for name, x in (
        ("lightgbm_local", local),
        ("lightgbm_typed_features", np.concatenate(enriched)),
        ("temporal_embeddings_lightgbm", np.column_stack([local, embeddings])),
    ):
        model = lgb.train(params, lgb.Dataset(x[fit], label=y[fit]), num_boost_round=300)
        model.save_model(str(OUT / f"{name}.txt"))
        results[name] = graph.assess(graphs, model.predict(x), name)
    report = {
        "models": results,
        "params": params,
        "rounds": 300,
        "seconds": time.perf_counter() - begin,
        "selected_by_validation_p20_then_ap": max(
            results,
            key=lambda name: (
                results[name]["validation"]["p_at_20"],
                results[name]["validation"]["ap"],
            ),
        ),
        "hashes": {str(Path(__file__)): digest(__file__), str(ENCODER): digest(ENCODER)},
        "limitations": [
            "Consumed synthetic world; supplementary comparison, not new confirmation.",
            "Encoder is frozen from the validation-selected180epoch temporal run.",
            "Same-fit supervised embeddings, not an out-of-fold stack.",
            "No independent-world LightGBM transfer/policy validation here.",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log("typed_lightgbm_controls_complete", output=str(OUT / "report.json"))


if __name__ == "__main__":
    main()
