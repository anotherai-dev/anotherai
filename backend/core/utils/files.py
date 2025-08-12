from typing import Literal

file_signatures = signatures = {
    # Images
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    # Documents
    b"%PDF": "application/pdf",
    # Audio
    b"ID3": "audio/mpeg",
    b"\xff\xfb": "audio/mpeg",
    b"\xff\xf3": "audio/mpeg",
    b"\xff\xf2": "audio/mpeg",
}


def guess_content_type(file_data: bytes, mode: Literal["image", "audio", "video"] | None = None) -> str | None:
    for signature, mime_type in file_signatures.items():
        if file_data.startswith(signature):
            return mime_type

    if file_data.startswith(b"RIFF"):
        if file_data[8:12] == b"WEBP":
            return "image/webp"
        if b"WAVE" in file_data[:12]:
            return "audio/wav"

    return None
