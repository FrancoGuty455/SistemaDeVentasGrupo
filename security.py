import os, hashlib

ITERATIONS = 200_000

def hash_password(password: str, salt: bytes=None):
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return salt, dk

def verify_password(password: str, salt: bytes, expected_hash: bytes) -> bool:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    # compare constant-time
    if len(dk) != len(expected_hash):
        return False
    result = 0
    for a, b in zip(dk, expected_hash):
        result |= a ^ b
    return result == 0
