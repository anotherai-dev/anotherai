import os
from typing import cast

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESHMAC:
    def __init__(self, hmac_key: bytes, aes_key: bytes) -> None:
        if len(hmac_key) < 32:  # Ensuring HMAC key is at least 256 bits
            raise ValueError("HMAC key must be at least 256 bits.")
        if len(aes_key) not in {16, 24, 32}:  # AES key must be 128, 192, or 256 bits
            raise ValueError("AES key must be 128, 192, or 256 bits.")

        self.hmac_key: bytes = hmac_key
        self.aes_key: bytes = aes_key

    def encrypt(self, value: str) -> str:
        # Generate a random IV
        iv = os.urandom(16)
        # Set up the cipher
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        # Pad plaintext to be multiple of block size
        block_size = cast(int, algorithms.AES.block_size)  # pyright: ignore[reportInvalidCast]
        padder = padding.PKCS7(block_size).padder()
        padded_data = padder.update(value.encode()) + padder.finalize()
        # Encrypt
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Create HMAC
        h = hmac.HMAC(self.hmac_key, hashes.SHA256(), backend=default_backend())
        h.update(ciphertext)
        hmac_value = h.finalize()

        return iv.hex() + ciphertext.hex() + hmac_value.hex()

    def decrypt(self, value: str) -> str:
        iv = bytes.fromhex(value[:32])
        hmac_value = bytes.fromhex(value[-64:])
        ciphertext = bytes.fromhex(value[32:-64])

        # Verify HMAC
        h = hmac.HMAC(self.hmac_key, hashes.SHA256(), backend=default_backend())
        h.update(ciphertext)
        h.verify(hmac_value)

        # Decrypt
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Unpad plaintext
        block_size = cast(int, algorithms.AES.block_size)  # pyright: ignore[reportInvalidCast]
        unpadder = padding.PKCS7(block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        return plaintext.decode()
