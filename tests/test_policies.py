from sandbox_service import EXPECTED_LIMITS, POLICY_LIMITS


def test_policy_keys_match_contract():
    assert POLICY_LIMITS.keys() == EXPECTED_LIMITS.keys()


def test_policy_values_match_contract():
    assert POLICY_LIMITS == EXPECTED_LIMITS


def test_limits_remain_positive_integers():
    assert all(isinstance(value, int) and value > 0 for value in POLICY_LIMITS.values())
