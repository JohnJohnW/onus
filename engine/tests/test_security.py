from security import hash_password, verify_password


def test_hash_and_verify():
    hashed = hash_password("compliance-2026-secure")
    assert hashed != "compliance-2026-secure"
    assert verify_password("compliance-2026-secure", hashed)
    assert not verify_password("wrong-password", hashed)


def test_long_password_does_not_crash():
    # bcrypt's 72-byte limit must not raise.
    hashed = hash_password("x" * 200)
    assert verify_password("x" * 200, hashed)
