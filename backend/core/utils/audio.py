import asyncio
import io


def _ffmpeg_format_from_content_type(content_type: str) -> str:
    match content_type:
        case "audio/mpeg":
            return "mp3"
        case _:
            return content_type.split("/")[1]


def _audio_duration_seconds_sync(data: bytes, content_type: str) -> float:
    from pydub import AudioSegment

    _format = _ffmpeg_format_from_content_type(content_type)
    segment = AudioSegment.from_file(io.BytesIO(data), _format)
    return len(segment) / 1000


async def audio_duration_seconds(data: bytes, content_type: str) -> float:
    return await asyncio.to_thread(_audio_duration_seconds_sync, data, content_type)
