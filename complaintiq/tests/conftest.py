import dataclasses

import pytest

from complaintiq.config import Settings


@pytest.fixture(scope="session")
def synth_df():
    from complaintiq.synth import generate

    return generate(3000, seed=1)


@pytest.fixture()
def settings(tmp_path):
    return dataclasses.replace(Settings.from_env(), artifacts_dir=tmp_path / "art", results_dir=tmp_path / "res",
                               docs_dir=tmp_path / "docs", data_dir=tmp_path / "data", llm_provider="mock",
                               reranker="lexical", embedder="hashing")
