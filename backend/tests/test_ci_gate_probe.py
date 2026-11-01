"""Deliberately failing test to prove the CI gate; reverted in this PR."""


def test_ci_gate_blocks_on_failure():
    assert False, "deliberate failure: backend-tests must block validate-image"
