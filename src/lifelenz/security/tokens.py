"""Fixed-algorithm short-lived JWT access tokens."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from lifelenz.identity import UserId
from lifelenz.security.exceptions import TokenValidationError

_ALGORITHM = "HS256"
_MAX_LIFETIME = timedelta(days=1)


def _aware_utc(value: object, name: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise TypeError(f"{name} must be an aware datetime")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Validated minimal claims carried by a LifeLenz access token."""

    subject: UserId
    issued_at: datetime
    expires_at: datetime
    token_id: UUID
    issuer: str
    audience: str

    def __post_init__(self) -> None:
        if type(self.subject) is not UserId:
            raise TypeError("subject must be a UserId")
        issued = _aware_utc(self.issued_at, "issued_at")
        expires = _aware_utc(self.expires_at, "expires_at")
        object.__setattr__(self, "issued_at", issued)
        object.__setattr__(self, "expires_at", expires)
        if expires <= issued:
            raise ValueError("expires_at must be after issued_at")
        if type(self.token_id) is not UUID:
            raise TypeError("token_id must be a UUID")
        for value, name in ((self.issuer, "issuer"), (self.audience, "audience")):
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} must be a nonblank string")


class JwtAccessTokenService:
    """Issue and validate only HS256 access tokens with required claims."""

    __slots__ = ("__secret", "_audience", "_issuer", "_lifetime")

    def __init__(
        self, *, secret: str, issuer: str, audience: str, access_token_lifetime: timedelta
    ) -> None:
        if type(secret) is not str or not secret or len(secret.encode("utf-8")) < 32:
            raise ValueError("secret must contain at least 32 UTF-8 bytes")
        if len(secret.encode("utf-8")) > 4096:
            raise ValueError("secret is too long")
        if type(issuer) is not str or not issuer.strip():
            raise ValueError("issuer must be a nonblank string")
        if type(audience) is not str or not audience.strip():
            raise ValueError("audience must be a nonblank string")
        if (
            type(access_token_lifetime) is not timedelta
            or not timedelta(0) < access_token_lifetime <= _MAX_LIFETIME
        ):
            raise ValueError("access token lifetime must be positive and at most one day")
        self.__secret = secret
        self._issuer = issuer
        self._audience = audience
        self._lifetime = access_token_lifetime

    def issue_token(self, user_id: UserId) -> str:
        """Issue one minimal signed token for an exact account identity."""
        if type(user_id) is not UserId:
            raise TypeError("user_id must be a UserId")
        issued_at = datetime.now(UTC).replace(microsecond=0)
        payload = {
            "sub": str(user_id.value),
            "iat": issued_at,
            "exp": issued_at + self._lifetime,
            "jti": str(uuid4()),
            "iss": self._issuer,
            "aud": self._audience,
        }
        return jwt.encode(payload, self.__secret, algorithm=_ALGORITHM)

    def decode_token(self, token: str) -> AccessTokenClaims:
        """Verify and reconstruct trusted claims without exposing PyJWT errors."""
        if type(token) is not str or not token:
            raise TokenValidationError("access token is invalid")
        try:
            payload = jwt.decode(
                token,
                self.__secret,
                algorithms=[_ALGORITHM],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "iat", "exp", "jti", "iss", "aud"]},
            )
            issued_raw = payload["iat"]
            expires_raw = payload["exp"]
            if type(issued_raw) not in (int, float) or type(expires_raw) not in (int, float):
                raise ValueError("timestamps must be numeric")
            return AccessTokenClaims(
                subject=UserId(UUID(payload["sub"])),
                issued_at=datetime.fromtimestamp(issued_raw, UTC),
                expires_at=datetime.fromtimestamp(expires_raw, UTC),
                token_id=UUID(payload["jti"]),
                issuer=payload["iss"],
                audience=payload["aud"],
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise TokenValidationError("access token is invalid") from error
