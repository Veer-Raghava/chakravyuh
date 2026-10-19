# Chakravyuh

Chakravyuh is a local Bitcoin transaction investigation workspace. It turns peer-observed transaction traffic into a reproducible analysis run, then exposes the results through a read-only API and the Drishti web console.

The project is designed for offline work: generated runs stay on the investigator's machine, while the repository contains the pipeline, tests, UI, and small fixtures needed to reproduce and inspect the workflow.

## What it includes

- A staged Python pipeline for capture, validation, normalisation, graph construction, origin estimation, scoring, explanation, and evidence packets.
- A loopback-only FastAPI service for serving one generated run.
- A React and Three.js console for exploring alerts, transaction graphs, origin estimates, model evidence, and investigation packets.
- Deterministic fixtures and verification targets for contracts, leakage controls, replay, and frontend builds.

## Architecture

The pipeline is intentionally filesystem-based. Each stage reads Parquet from the previous stage and writes a new stage directory, making intermediate results inspectable and runs reproducible.

```text
capture → KAVACH → SETU → JAAL → SHASTRA → BUDDHI → VAANI → PRAMAAN
                                                                    ↓
                                                               DRISHTI
```

- **KAVACH** validates and seals input captures.
- **SETU** normalises types and enriches observations.
- **JAAL** builds the address and peer graph.
- **SHASTRA** estimates origin signals and transaction typology.
- **BUDDHI** ranks investigative subjects and reports uncertainty.
- **VAANI** adds explanations and counter-evidence.
- **PRAMAAN** packages signed evidence for review.
- **DRISHTI** presents the read-only result.

## Requirements

- Python 3.11
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 18 or newer and npm

## Quick start

Install the Python environment and create the local working directories:

```bash
uv sync
make setup
```

Run the frontend with its committed offline fixtures:

```bash
cd apps/drishti-v2
npm ci
npm run dev
```

The console is then available at `http://127.0.0.1:5173`.

To build and serve a complete local pipeline run:

```bash
make demo-full
make demo
```

The demo serves the API on `http://127.0.0.1:8000` and the console on `http://127.0.0.1:5173`. Use `make help` to see the available stage, validation, fixture, and inspection commands.

## Development

Run the backend checks with:

```bash
make verify
```

Check the console independently with:

```bash
cd apps/drishti-v2
npm run typecheck
npm run build
```

The contracts in [`docs/DATA-CONTRACTS.md`](docs/DATA-CONTRACTS.md) and the model vocabulary in [`docs/FEATURES.md`](docs/FEATURES.md) are part of the pipeline boundary. The short architecture and demo notes are [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DEMO-RUN.md`](docs/DEMO-RUN.md).

## Data and limitations

The repository's fixtures are for reproducible development and demonstration. Results depend on the observed traffic, the available peer coverage, the generated ground truth, and the configured run. A score or origin estimate is investigative evidence—not proof of ownership or identity—and the UI is designed to show abstentions and missing evidence rather than hide them.

Generated runs, measurements, research exports, dependency directories, and build output are intentionally ignored. Keep sensitive captures, signing keys, and other local inputs outside version control.

## License

Released under the license in [`LICENSE`](LICENSE).
