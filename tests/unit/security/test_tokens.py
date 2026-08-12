from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

import lifelenz.security
from lifelenz.identity import UserId
from lifelenz.security import AccessTokenClaims, JwtAccessTokenService, TokenValidationError

SECRET = "token-test-secret-material-that-is-never-production"


def service(**changes: object) -> JwtAccessTokenService:
    values = {
        "secret": SECRET,
        "issuer": "issuer",
        "audience": "audience",
        "access_token_lifetime": timedelta(minutes=5),
    }
    values.update(changes)
    return JwtAccessTokenService(**values)  # type: ignore[arg-type]


def test_claims_are_minimal_typed_and_round_trip() -> None:
    user_id = UserId.new()
    token = service().issue_token(user_id)
    claims = service().decode_token(token)
    assert claims.subject == user_id
    assert claims.expires_at > claims.issued_at
    assert claims.issuer == "issuer"
    payload = jwt.decode(token, SECRET, algorithms=["HS256"], audience="audience", issuer="issuer")
    assert set(payload) == {"sub", "iat", "exp", "jti", "iss", "aud"}


def test_claim_model_requires_aware_ordered_values() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        AccessTokenClaims(UserId.new(), now, now, uuid4(), "issuer", "audience")


@pytest.mark.parametrize("token", ["", "not.jwt", "a.b.c"])
def test_malformed_tokens_are_generic(token: str) -> None:
    with pytest.raises(TokenValidationError):
        service().decode_token(token)


def test_wrong_signature_issuer_audience_expiry_and_algorithm_are_rejected() -> None:
    user = UserId.new()
    valid = service().issue_token(user)
    for decoder in (
        service(secret="different-secret-material-at-least-32-bytes"),
        service(issuer="other"),
        service(audience="other"),
    ):
        with pytest.raises(TokenValidationError):
            decoder.decode_token(valid)
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(user.value),
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "jti": str(uuid4()),
            "iss": "issuer",
            "aud": "audience",
        },
        SECRET,
        algorithm="HS256",
    )
    unsupported = jwt.encode(
        {
            "sub": str(user.value),
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "jti": str(uuid4()),
            "iss": "issuer",
            "aud": "audience",
        },
        SECRET,
        algorithm="HS384",
    )
    for token in (expired, unsupported):
        with pytest.raises(TokenValidationError):
            service().decode_token(token)


def test_missing_required_claim_and_malformed_jti_are_rejected() -> None:
    now = datetime.now(UTC)
    base = {
        "sub": str(UserId.new().value),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "jti": str(uuid4()),
        "iss": "issuer",
        "aud": "audience",
    }
    missing = dict(base)
    del missing["sub"]
    malformed = {**base, "jti": "not-a-uuid"}
    for payload in (missing, malformed):
        with pytest.raises(TokenValidationError):
            service().decode_token(jwt.encode(payload, SECRET, algorithm="HS256"))


def test_security_public_api_is_exact() -> None:
    assert lifelenz.security.__all__ == [
        "AccessTokenClaims",
        "Argon2PasswordHasher",
        "JwtAccessTokenService",
        "PasswordHashError",
        "SecurityError",
        "TokenValidationError",
    ]
