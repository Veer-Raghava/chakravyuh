"""Actual isolated inference with only observations/model artifacts and no Torch import."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from common import digest, log


def main():
    start = time.perf_counter()
    root = Path.cwd()
    expected = json.loads(
        (root / "research/bitcoin/results/investigation-demo-v2/window8/leads.json").read_text()
    )
    with tempfile.TemporaryDirectory(prefix="chakravyuh-investigation-") as directory:
        work = Path(directory)
        normalised = work / "normalised"
        normalised.mkdir()
        for name in ("transactions", "addresses", "announcements", "peers"):
            shutil.copyfile(
                root / f"data/generated/agency-v2/normalised/{name}.parquet",
                normalised / f"{name}.parquet",
            )
        shutil.copytree(
            root / "research/bitcoin/results/relational-inference-artifacts/address", work / "model"
        )
        code = """import sys,importlib.abc
class NoTorch(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='torch' or fullname.startswith('torch.'):
            raise ModuleNotFoundError('Torch deliberately unavailable')
sys.meta_path.insert(0,NoTorch())
from pathlib import Path
from chakravyuh.vaani.investigation import run
run(Path('normalised'),Path('model'),Path('output'),start_us=START,end_us=END)
assert 'torch' not in sys.modules
assert not any(k.startswith('research.') for k in sys.modules)
import json,resource
Path('resources.json').write_text(json.dumps({'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
""".replace("START", str(expected["window"]["start_us"])).replace(
            "END", str(expected["window"]["end_us"])
        )
        environment = dict(os.environ, PYTHONPATH=str(root / "src"))
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=work,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        actual = json.loads((work / "output/leads.json").read_text())
        assert actual == expected
        report = dict(
            leads=actual["lead_count"],
            exact_packet_replay=True,
            torch_disabled=True,
            resources=json.loads((work / "resources.json").read_text()),
            copied_input_files=4,
            ground_truth_copied=False,
            stdout_empty=not result.stdout,
            seconds=time.perf_counter() - start,
            source_sha256=digest(__file__),
            statement="Portable inference on copied observations; not full packaged deployment.",
        )
    (root / "research/bitcoin/results/investigation-stripped-smoke.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    log("investigation_stripped_smoke_complete", **report)


if __name__ == "__main__":
    main()
