"""Shared test fixtures.

The ``compiled_schema`` fixture compiles the GSettings schema into a temporary
directory and points ``GSETTINGS_SCHEMA_DIR`` at it, so configuration tests run
without installing the package. Tests that need it are skipped when
``glib-compile-schemas`` is unavailable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_SOURCE = _PROJECT_ROOT / "data"


@pytest.fixture(scope="session")
def compiled_schema(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    compiler = shutil.which("glib-compile-schemas")
    if compiler is None:
        pytest.skip("glib-compile-schemas not available")

    target = tmp_path_factory.mktemp("schemas")
    shutil.copy(_SCHEMA_SOURCE / "io.github.AndreaBonn.Sysbar.gschema.xml", target)
    subprocess.run([compiler, str(target)], check=True)

    previous = os.environ.get("GSETTINGS_SCHEMA_DIR")
    os.environ["GSETTINGS_SCHEMA_DIR"] = str(target)
    try:
        yield str(target)
    finally:
        if previous is None:
            os.environ.pop("GSETTINGS_SCHEMA_DIR", None)
        else:
            os.environ["GSETTINGS_SCHEMA_DIR"] = previous
