"""Tests for password hashing and JWT utilities."""
import time
import pytest
from jose import ExpiredSignatureError, JWTError

from api.auth_utils import hash_password, verify_password, create_access_token, decode_access_token


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("abc")
        h2 = hash_password("abc")
        # bcrypt uses a random salt — same input must not produce same hash
        assert h1 != h2


class TestJWT:
    SECRET = "test-secret"
    ALGORITHM = "HS256"

    def test_create_and_decode_token(self):
        token = create_access_token(user_id=42, secret=self.SECRET, expire_hours=1)
        payload = decode_access_token(token, secret=self.SECRET)
        assert payload["sub"] == "42"

    def test_expired_token_raises(self):
        token = create_access_token(user_id=1, secret=self.SECRET, expire_hours=-1)
        with pytest.raises(ExpiredSignatureError):
            decode_access_token(token, secret=self.SECRET)

    def test_tampered_token_raises(self):
        token = create_access_token(user_id=1, secret=self.SECRET, expire_hours=1)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_access_token(tampered, secret=self.SECRET)
