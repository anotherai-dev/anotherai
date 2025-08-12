from tiktoken import Encoding, encoding_for_model, get_encoding


def _get_tiktoken_encoding(model: str) -> Encoding:
    try:
        encoding = encoding_for_model(model)
    except KeyError:
        encoding = get_encoding("cl100k_base")

    return encoding


def tokens_from_string(completion: str, model: str) -> int:
    encoding = _get_tiktoken_encoding(model)

    return len(encoding.encode(completion))
