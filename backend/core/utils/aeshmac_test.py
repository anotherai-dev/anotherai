from base64 import b64decode

from .aeshmac import AESHMAC


def test_sanity():
    raw_key1 = "P/eHXwcVqCiGANW9Zjkwy2Mf0Ymk42gg75h6EPkC+tw="
    decoded = b64decode(raw_key1)
    aes_hmac = AESHMAC(decoded, decoded)
    encrypted = aes_hmac.encrypt("Hello, world!")
    decrypted = aes_hmac.decrypt(encrypted)

    assert decrypted == "Hello, world!"
