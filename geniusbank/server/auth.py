# auth.py
import os
import hashlib

class Auth:
    """Handles password hashing and verification."""

    def hash_password(self, password: str):
        """
        Generate a random salt and hash the password using PBKDF2-HMAC-SHA256.

        Returns:
            pwd_hash (bytes): Hashed password
            salt (bytes): Randomly generated salt
        """
        salt = os.urandom(32)  # 32-byte salt for better security
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',            # Hash algorithm
            password.encode(),   # Convert password to bytes
            salt,                # Salt
            100_000              # Iterations
        )
        return pwd_hash, salt

    def verify_password(self, stored_hash: bytes, stored_salt: bytes, password: str):
        """
        Verify a password against the stored hash using the given salt.

        Args:
            stored_hash (bytes): Hash stored in DB
            stored_salt (bytes): Salt used when creating stored_hash
            password (str): Password to check

        Returns:
            bool: True if password is correct, False otherwise
        """
        if stored_hash is None or stored_salt is None:
            return False

        check_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            stored_salt,
            100_000
        )
        return check_hash == stored_hash