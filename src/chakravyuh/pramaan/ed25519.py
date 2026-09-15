"""Ed25519 signing and verification, pure Python, RFC 8032.

No crypto library exists in the pinned environment and none can be added (uv cannot
re-resolve; see STATE.md open problem 3), so this implements RFC 8032 directly over
`hashlib.sha512` and arithmetic mod 2**255-19. Signing is deterministic per the RFC —
the nonce is derived from the message and the key, never from a random draw — so the
same key over the same bytes produces the same signature, which is what the replay
gate leans on.

This is deliberately the only cryptography in the package and it is slow: roughly a
second per operation. Fine for signing one packet per case, which is the only path the
stage exercises; `--all` exists for the same scale.

A private key never appears in a log line or an exception message: the two functions
that read one take raw bytes and raise with paths only.
"""

from __future__ import annotations

import hashlib
import os
from typing import Final

P: Final[int] = 2**255 - 19
L: Final[int] = 2**252 + 27742317777372353535851937790883648493
D: Final[int] = -121665 * pow(121666, P - 2, P) % P
SQRT_M1: Final[int] = pow(2, (P - 1) // 4, P)  # sqrt(-1) mod P

Point = tuple[int, int]  # affine (x, y); extended coordinates would be faster, this is clearer.


def _recover_x(y: int, sign: int) -> int:
    """The x on curve25519 with the given y and x parity. Raises when y is not on the curve."""
    if y >= P:
        raise ValueError("y out of range")
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        if sign:
            raise ValueError("no point with that parity")
        return 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P != 0:
        raise ValueError("y is not on the curve")
    if x & 1 != sign:
        x = P - x
    return x


def _point_add(p: Point, q: Point) -> Point:
    """Addition on the twisted Edwards curve -x^2 + y^2 = 1 + d x^2 y^2, affine.

    Two inversions per add; a projective implementation would trade clarity for about
    a factor of three and nothing here needs it.
    """
    x1, y1 = p
    x2, y2 = q
    x1x2 = x1 * x2 % P
    y1y2 = y1 * y2 % P
    dxxyy = D * x1x2 % P * y1y2 % P
    x3 = (x1 * y2 + x2 * y1) * pow(1 + dxxyy, P - 2, P) % P
    # a = -1, so the numerator is y1*y2 - a*x1*x2 = y1*y2 + x1*x2.
    y3 = (y1y2 + x1x2) * pow(1 - dxxyy, P - 2, P) % P
    return x3, y3


def _point_mul(scalar: int, point: Point) -> Point:
    """Double-and-add scalar multiplication, affine. The identity is (0, 1)."""
    result: Point = (0, 1)
    addend = point
    while scalar > 0:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1
    return result


def _compress(point: Point) -> bytes:
    """A point to its 32-byte RFC 8032 encoding: little-endian y, x parity in bit 255."""
    x, y = point
    return ((y | ((x & 1) << 255)) % (1 << 256)).to_bytes(32, "little")


def _decompress(data: bytes) -> Point:
    """The inverse of `_compress`. Raises on a point not on the curve, which is how a
    corrupted public key fails verification rather than passing it."""
    if len(data) != 32:
        raise ValueError("a compressed point is 32 bytes")
    raw = int.from_bytes(data, "little")
    y = raw & ((1 << 255) - 1)
    sign = raw >> 255
    return _recover_x(y, sign), y


def _sha512_int(*chunks: bytes) -> int:
    return int.from_bytes(hashlib.sha512(b"".join(chunks)).digest(), "little")


# The standard base point: y = 4/5, x even, per RFC 8032 section 5.1. Defined after the
# helpers because `_recover_x` computes it.
GY: Final[int] = (4 * pow(5, P - 2, P)) % P
GX: Final[int] = _recover_x(GY, 0)


def _scalar(seed: bytes) -> int:
    """The signing scalar: the low half of SHA-512(seed), clamped per RFC 8032 5.1.5."""
    h = hashlib.sha512(seed).digest()
    return int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254)


def generate_seed() -> bytes:
    """32 random bytes from the OS CSPRNG. The only randomness anywhere in this package."""
    return os.urandom(32)


def public_key(seed: bytes) -> bytes:
    """The 32-byte public key for a 32-byte seed, per RFC 8032 section 5.1.5."""
    return _compress(_point_mul(_scalar(seed), (GX, GY)))


def sign(seed: bytes, message: bytes) -> bytes:
    """Sign `message` with the key pair derived from `seed`. Deterministic, 64 bytes out."""
    h = hashlib.sha512(seed).digest()
    scalar = _scalar(seed)
    public = _compress(_point_mul(scalar, (GX, GY)))
    r = _sha512_int(h[32:], message) % L
    r_enc = _compress(_point_mul(r, (GX, GY)))
    k = _sha512_int(r_enc, public, message) % L  # RFC 8032 hashes R first, then A.
    s = (r + k * scalar) % L
    return r_enc + s.to_bytes(32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """RFC 8032 verification. Returns False on any malformed input, never raises on it."""
    try:
        if len(signature) != 64 or len(public) != 32:
            return False
        a_point = _decompress(public)
        r_enc = signature[:32]
        r_point = _decompress(r_enc)
        s = int.from_bytes(signature[32:], "little")
        if s >= L:
            return False
        k = _sha512_int(r_enc, public, message) % L  # RFC 8032 hashes R first, then A.
        # s*B == R + k*A, compared as compressed encodings so parity agrees.
        left = _compress(_point_mul(s, (GX, GY)))
        right = _compress(_point_add(r_point, _point_mul(k, a_point)))
        return left == right
    except (ValueError, IndexError):
        return False
