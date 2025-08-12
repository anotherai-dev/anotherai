from .utils import cut_string, fixture_text, fixtures_stream_hex


def test_fixtures_text() -> None:
    text = fixture_text("openai", "completion.json")
    assert text


def test_fixtures_stream() -> None:
    stream = fixtures_stream_hex("bedrock", "stream_content_moderation.txt")
    assert stream


def test_cut_string():
    s = "1234567890"
    cut_idxs = [3, 5, 9]
    chunks = list(cut_string(s, cut_idxs))
    assert chunks == ["123", "45", "6789", "0"]
