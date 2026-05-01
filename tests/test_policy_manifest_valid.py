from omega_runtime.core.policy_manifest import (
    DEFAULT_POLICY_PATH,
    verify_policy_manifest,
    write_default_policy_manifest,
)


def test_policy_manifest_valid():
    write_default_policy_manifest(DEFAULT_POLICY_PATH)

    ok, reason, policy_hash = verify_policy_manifest(DEFAULT_POLICY_PATH)

    assert ok is True
    assert reason == "policy manifest valid"
    assert isinstance(policy_hash, str)
    assert len(policy_hash) == 64
