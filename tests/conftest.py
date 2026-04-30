"""
Shared fixtures: load each data/clean/*.json once per session.

The pipeline (scripts/02_clean_and_merge.py) is the system under test —
these fixtures hand the parsed JSON to test_clean_data.py for assertions.
"""

import json
from pathlib import Path

import pytest

CLEAN = Path(__file__).parent.parent / "data" / "clean"


def _load(name: str):
    with open(CLEAN / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def chimei():
    return _load("chimei.json")


@pytest.fixture(scope="session")
def bunrui():
    return _load("bunrui_bangou.json")


@pytest.fixture(scope="session")
def hiragana():
    return _load("hiragana.json")


@pytest.fixture(scope="session")
def gotochi():
    return _load("gotochi.json")


@pytest.fixture(scope="session")
def summary():
    return _load("summary.json")
