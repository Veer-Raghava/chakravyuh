# Chakravyuh

Chakravyuh is a local Bitcoin transaction investigation workspace. It turns peer-observed transaction traffic into a reproducible analysis run, then presents the result through a read-only API and the Drishti web console.

It is built for offline investigation and development rather than public chain browsing. A run can be generated, inspected stage by stage, scored, explained, and packaged as evidence without sending the capture or its intermediate data to a remote service.

## Why it exists

Bitcoin transactions record the chain, but not the circumstances in which a transaction reached a node. Chakravyuh works with the observable network layer around a transaction and keeps those observations separate from conclusions drawn by later stages.

The result is an investigation workspace that can:

- validate and normalise heterogeneous capture files;
- build address, transaction, and peer relationships;
- estimate origin and network signals with explicit uncertainty;
- rank subjects for review and attach feature-level explanations;
- show abstentions, missing coverage, and counter-evidence; and
- export a reviewable evidence packet from a selected alert.

The system does not turn an observed IP into a guaranteed identity. Results depend on the capture, peer coverage, generated ground truth, and evaluation protocol used for a run.

## How the system fits together

The backend is a filesystem pipeline. Each stage reads the previous stage's Parquet output and writes a new directory. There is no shared database or hidden mutable state; the Makefile is the orchestrator.

```text
capture → KAVACH → SETU → JAAL → SHASTRA → BUDDHI → VAANI → PRAMAAN
                                                                    ↓
                                                               DRISHTI
```

| Stage | Responsibility | Typical output |
| --- | --- | --- |
| MAYAJAAL | Generate deterministic local worlds and captures for development | `capture/`, `ground_truth/` |
| KAVACH | Validate input shape, normalise capture metadata, and seal the input | `sealed/` |
| SETU | Coerce types and enrich observable network fields | `normalised/` |
| JAAL | Build the fused transaction, address, and peer graph | `graph/` |
| SHASTRA | Estimate origin signals and derive transaction typology | `signals/` |
| BUDDHI | Rank investigative subjects and report uncertainty | `scores/` |
| VAANI | Add explanations, counter-evidence, and readable alert text | `alerts/` |
| PRAMAAN | Build signed evidence packets for selected cases | `packets/` |
| DRISHTI | Explore the run through a local web interface | browser UI |

The browser talks to the API rather than reading arbitrary files. The API binds to `127.0.0.1`, serves one selected run, and exposes read-only routes for the manifest, transactions, graph, alerts, origin estimates, and evidence packets.

## What is in this repository

```text
src/chakravyuh/       Python pipeline, API, serializers, and evaluation code
apps/drishti-v2/      React + Three.js investigation console
scripts/              Fixture builders, exporters, validators, and smoke checks
tests/                Backend contracts and stage tests
data/fixtures/        Small committed inputs and UI fixtures
docs/                 Four public reference files used by the project
vendor/               Optional externally sourced data and its loader notes
Makefile              Setup, pipeline, demo, validation, and cleanup commands
```

The repository intentionally does not include generated runs, measurements, dependency trees, build output, private captures, signing keys, or working-session notes. Those remain local and are covered by `.gitignore`.

## Requirements

- Python 3.11
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 18 or newer and npm

The Python dependencies are pinned in `pyproject.toml` and `uv.lock`. The frontend dependencies are pinned in `apps/drishti-v2/package-lock.json`.

## Quick start: inspect the console

This is the shortest path to seeing the interface. It uses committed offline fixtures and does not require a generated backend run.

```bash
cd apps/drishti-v2
npm ci
npm run dev
```

Open <http://127.0.0.1:5173> in a browser. The landing page leads into the console's local fixture login. The fixture credentials are intentionally non-production:

```text
username:  officer.ntro
passphrase: drishti-demo
```

The fixture login only changes local UI state. It is not an authentication system.

## Quick start: build and serve a complete run

Install the Python environment and create the local working directories:

```bash
make setup
```

Build the complete demonstration run. This invokes the stages in order and writes generated data under ignored directories:

```bash
make demo-full
```

Serve the API and the console together:

```bash
make demo
```

The API is available at <http://127.0.0.1:8000> and the console at <http://127.0.0.1:5173>. `make demo` serves the precomputed run and does not regenerate it on every page load.

For a smaller, lower-cost pipeline run, start with the individual stage targets listed by:

```bash
make help
```

## API quick tour

After a run is available, the service can be started directly by naming a run id. The value is a run name under `data/generated/`, not an arbitrary filesystem path.

```bash
CHAKRAVYUH_RUN=s10-demo uv run uvicorn chakravyuh.api.app:app --host 127.0.0.1 --port 8000
```

Useful read-only routes include:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/manifest
curl 'http://127.0.0.1:8000/alerts?limit=20'
curl 'http://127.0.0.1:8000/transactions?limit=20'
curl 'http://127.0.0.1:8000/graph?detail=cluster'
curl http://127.0.0.1:8000/alerts/<alert-id>
curl http://127.0.0.1:8000/packets/<alert-id>
```

The API is intended for the local console and inspection scripts. It has no remote authentication layer because it is deliberately loopback-only; do not expose it on a network interface.

## Data conventions

The pipeline uses a few rules consistently:

- monetary values are integer satoshis, never floating-point BTC;
- times are UTC microseconds since the epoch and use the `_us` suffix;
- `null` means unknown or unavailable and is not silently converted to zero;
- Parquet uses real list columns, while delimited text inputs use pipe-separated lists; and
- every stage writes metadata describing the run and its outputs.

The frozen boundary is documented in [`docs/DATA-CONTRACTS.md`](docs/DATA-CONTRACTS.md). The names and plain-English meanings of model features are in [`docs/FEATURES.md`](docs/FEATURES.md).

## Development and verification

Run the backend checks for the implemented stages with:

```bash
make verify
```

Useful focused checks are:

```bash
make verify-contracts
make verify-quarantine
make verify-determinism
```

Check the console independently with:

```bash
cd apps/drishti-v2
npm run typecheck
npm run build
```

`make clean` removes generated pipeline output and tool caches while leaving source code and committed fixtures in place.

## Limitations and responsible use

This is an offline investigative system, not a hosted service, a general-purpose blockchain explorer, or an identity database. An origin estimate is conditional on what the observing peers saw. A graph cluster is a modelled relationship, not proof of common ownership. A ranked alert is a prioritisation aid, not a final finding.

The UI intentionally surfaces uncertainty and abstention. Do not present a result without its coverage, evidence, model version, and run metadata. Do not place real captures, private keys, credentials, or sensitive case material in the repository.

## Further reading

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) describes the stage boundaries and data flow.
- [`docs/DATA-CONTRACTS.md`](docs/DATA-CONTRACTS.md) defines the schemas shared by the pipeline and UI.
- [`docs/FEATURES.md`](docs/FEATURES.md) defines the model feature vocabulary shown in explanations.
- [`docs/DEMO-RUN.md`](docs/DEMO-RUN.md) explains the precomputed demo artifact and how it is served.

## Contributing and support

If you find a reproducibility issue, a broken command, or a misleading result, open an issue with the command you ran, the run id, and the smallest relevant log or fixture. Avoid attaching real captures or other sensitive data. Changes should keep stage contracts, deterministic fixtures, and the local-only API boundary intact.

## License

Released under the license in [`LICENSE`](LICENSE).
