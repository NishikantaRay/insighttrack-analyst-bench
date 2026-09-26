import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# InsightTrack's backend, for the parity and tool-sync tests. Override with
# INSIGHTTRACK_API; those tests skip when it is not available.
INSIGHTTRACK_API = os.environ.get(
    "INSIGHTTRACK_API",
    os.path.expanduser("~/Desktop/Personal/InsightTrack/apps/analytics-api"),
)


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    """A fresh build of the whole dataset, shared by every test."""
    from insighttrack_bench import build

    out = tmp_path_factory.mktemp("dataset")
    build.build(str(out), "tester")
    return str(out)


@pytest.fixture(scope="session")
def its(dataset):
    from insighttrack_bench import scoring

    scoring.init(dataset)
    return scoring


def insighttrack_available() -> bool:
    return bool(shutil.which("node")) and os.path.exists(
        os.path.join(INSIGHTTRACK_API, "src/services/correlationService.js")
    )
