from __future__ import annotations

from pathlib import Path

import pytest

from booktoskill.pipeline import Conversion, convert
from booktoskill.samplepdf import tiny_book, write_pdf


@pytest.fixture(scope="session")
def tiny_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_pdf(tmp_path_factory.mktemp("pdf") / "tiny.pdf", tiny_book())


@pytest.fixture(scope="session")
def tiny(tiny_pdf: Path) -> Conversion:
    return convert(tiny_pdf)
